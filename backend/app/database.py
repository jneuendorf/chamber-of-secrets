from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


@event.listens_for(Engine, "connect")
def _sqlite_fk_on(dbapi_conn: DBAPIConnection, _record: object) -> None:
    # SQLite defaults foreign_keys OFF and resets it per connection. Enable it on
    # every connect so the DB rejects orphans — a backstop behind the routers'
    # existence guards, not a replacement for them. Bound to Engine (not our
    # engine instance) so the test suite's own engine gets it too.
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
