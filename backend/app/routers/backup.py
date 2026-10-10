"""Backup & restore (WL-6.1): the whole household in one ZIP.

`backup.json` holds every table row-for-row (ids kept, so references survive);
`uploads/products/` holds the uploaded product photos the rows point at.
Restore replaces everything in one transaction, and only accepts a backup taken
at the same schema revision — an older backup is restored by an older build.
ponytail: built in memory, fine at household scale; stream it if backups reach
hundreds of MB.
"""

import io
import json
import zipfile
from datetime import date, datetime
from pathlib import PurePosixPath

from alembic.runtime.migration import MigrationContext
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import Connection, Date, DateTime, delete, insert, select, text
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from app.config import PRODUCT_IMAGE_DIR
from app.database import get_db
from app.models import Base

router = APIRouter(prefix="/backup", tags=["backup"])

FORMAT = 1
DATA_FILE = "backup.json"
IMAGE_PREFIX = "uploads/products/"
MAX_BACKUP_BYTES = 200 * 1024 * 1024


def _revision(conn: Connection) -> str | None:
    return MigrationContext.configure(conn).get_current_revision()


def _to_json(value: object) -> object:
    return value.isoformat() if isinstance(value, date | datetime) else value


@router.get("", response_class=Response)
def download_backup(db: Session = Depends(get_db)) -> Response:
    conn = db.connection()
    tables = {
        table.name: [
            {key: _to_json(value) for key, value in row.items()}
            for row in conn.execute(select(table)).mappings()
        ]
        for table in Base.metadata.sorted_tables
    }
    payload = {"format": FORMAT, "revision": _revision(conn), "tables": tables}

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(DATA_FILE, json.dumps(payload, ensure_ascii=False))
        for image in sorted(PRODUCT_IMAGE_DIR.iterdir()):
            if image.is_file():
                archive.write(image, IMAGE_PREFIX + image.name)

    filename = f"chamber-backup-{date.today().isoformat()}.zip"
    return Response(
        buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _from_json(table_name: str, row: dict) -> dict:
    table = Base.metadata.tables[table_name]
    parsed = {}
    for column in table.columns:
        value = row.get(column.name)
        if isinstance(value, str) and isinstance(column.type, DateTime):
            value = datetime.fromisoformat(value)
        elif isinstance(value, str) and isinstance(column.type, Date):
            value = date.fromisoformat(value)
        parsed[column.name] = value
    return parsed


def _bad(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


@router.post("/restore", status_code=204)
async def restore_backup(file: UploadFile, db: Session = Depends(get_db)) -> None:
    contents = await file.read()
    if len(contents) > MAX_BACKUP_BYTES:
        raise HTTPException(status_code=413, detail="Backup is too large")
    try:
        archive = zipfile.ZipFile(io.BytesIO(contents))
        payload = json.loads(archive.read(DATA_FILE))
    except (zipfile.BadZipFile, KeyError, ValueError) as err:
        raise _bad("Not a Chamber of Secrets backup") from err

    if not isinstance(payload, dict) or payload.get("format") != FORMAT:
        raise _bad("Not a Chamber of Secrets backup")
    conn = db.connection()
    if payload.get("revision") != _revision(conn):
        raise _bad("Backup is from a different app version")
    tables = payload.get("tables")
    if not isinstance(tables, dict) or not all(
        isinstance(rows, list) and all(isinstance(row, dict) for row in rows)
        for rows in tables.values()
    ):
        raise _bad("Backup data is malformed")

    # Only plain file names under uploads/products/ — never a path out of it.
    images = {}
    for name in archive.namelist():
        if name.startswith(IMAGE_PREFIX) and not name.endswith("/"):
            image_name = PurePosixPath(name).name
            if name != IMAGE_PREFIX + image_name or image_name.startswith("."):
                raise _bad("Backup contains an unexpected file")
            images[image_name] = archive.read(name)

    # Self-referencing categories may list a child before its parent.
    conn.execute(text("PRAGMA defer_foreign_keys = ON"))
    try:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(delete(table))
        for table in Base.metadata.sorted_tables:
            rows = [_from_json(table.name, row) for row in tables.get(table.name, [])]
            if rows:
                conn.execute(insert(table), rows)
        db.commit()
    except (StatementError, ValueError) as err:
        db.rollback()
        raise _bad("Backup data is inconsistent") from err

    # Files after the commit: a failed restore leaves the photos untouched.
    for old in PRODUCT_IMAGE_DIR.iterdir():
        if old.is_file():
            old.unlink()
    for image_name, data in images.items():
        (PRODUCT_IMAGE_DIR / image_name).write_bytes(data)
