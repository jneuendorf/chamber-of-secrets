import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect

# Ensure backend/app is importable when tests run from repository root.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.config import settings  # noqa: E402


class MigrationsTestCase(unittest.TestCase):
    """Exercise the real Alembic migrations on a fresh SQLite database.

    The API tests bootstrap their schema with ``Base.metadata.create_all``,
    which bypasses migrations entirely — so a migration that emits SQL SQLite
    cannot run (e.g. a standalone ``ALTER COLUMN``) would go unnoticed until a
    fresh deployment. These tests run ``alembic upgrade head`` end to end,
    mirroring container startup.
    """

    def setUp(self) -> None:
        self._original_url = settings.database_url
        self._tmp = tempfile.TemporaryDirectory()
        self._url = f"sqlite:///{self._tmp.name}/migrations.db"
        # env.py reads the URL from app settings.
        settings.database_url = self._url

    def tearDown(self) -> None:
        settings.database_url = self._original_url
        self._tmp.cleanup()

    def _config(self) -> Config:
        return Config(str(_BACKEND_ROOT / "alembic.ini"))

    def _category_columns(self) -> dict[str, dict]:
        engine = create_engine(self._url)
        try:
            return {c["name"]: c for c in inspect(engine).get_columns("categories")}
        finally:
            engine.dispose()

    def test_upgrade_head_on_fresh_db(self) -> None:
        command.upgrade(self._config(), "head")

        columns = self._category_columns()
        for expected in ("restock_target", "restock_min", "restock_inherit"):
            self.assertIn(expected, columns)

        # restock_inherit must be NOT NULL with no leftover server default
        # (the model uses a Python-side default only).
        self.assertFalse(columns["restock_inherit"]["nullable"])
        self.assertIsNone(columns["restock_inherit"]["default"])

    def test_full_downgrade_and_re_upgrade(self) -> None:
        config = self._config()
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        command.upgrade(config, "head")

        self.assertIn("restock_inherit", self._category_columns())


if __name__ == "__main__":
    unittest.main()
