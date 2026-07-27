import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine.interfaces import ReflectedColumn

# Ensure backend/app is importable when tests run from repository root.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from alembic.config import Config  # noqa: E402

from alembic import command  # noqa: E402
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

    def _category_columns(self) -> dict[str, ReflectedColumn]:
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

    def test_profiles_are_part_of_the_initial_schema(self) -> None:
        command.upgrade(self._config(), "head")

        engine = create_engine(self._url)
        try:
            inspector = inspect(engine)
            self.assertIn("profiles", inspector.get_table_names())

            tx_columns = {c["name"] for c in inspector.get_columns("inventory_transactions")}
            self.assertIn("profile_id", tx_columns)

            # The FK must reach the migrated DDL, not just the one create_all
            # builds — otherwise tests and a real deployment would disagree the
            # moment SQLite FK enforcement is switched on.
            profile_fks = [
                fk
                for fk in inspector.get_foreign_keys("inventory_transactions")
                if fk["referred_table"] == "profiles"
            ]
            self.assertEqual(len(profile_fks), 1)
            self.assertEqual(profile_fks[0]["constrained_columns"], ["profile_id"])
        finally:
            engine.dispose()

    def test_profile_achievements_table_is_created(self) -> None:
        command.upgrade(self._config(), "head")

        engine = create_engine(self._url)
        try:
            inspector = inspect(engine)
            self.assertIn("profile_achievements", inspector.get_table_names())

            # One badge per profile — the uniqueness is what makes re-checking
            # achievements idempotent, so it must reach the migrated DDL.
            unique = inspector.get_unique_constraints("profile_achievements")
            self.assertIn(
                ["profile_id", "achievement_key"],
                [constraint["column_names"] for constraint in unique],
            )
        finally:
            engine.dispose()

    def test_reward_tiers_table_is_created(self) -> None:
        command.upgrade(self._config(), "head")

        engine = create_engine(self._url)
        try:
            self.assertIn("reward_tiers", inspect(engine).get_table_names())
        finally:
            engine.dispose()

    def test_profile_rewards_table_is_created(self) -> None:
        command.upgrade(self._config(), "head")

        engine = create_engine(self._url)
        try:
            inspector = inspect(engine)
            self.assertIn("profile_rewards", inspector.get_table_names())

            # One redemption per (profile, tier) — the unique constraint is what
            # makes re-redeeming idempotent, so it must reach the migrated DDL.
            unique = inspector.get_unique_constraints("profile_rewards")
            self.assertIn(
                ["profile_id", "reward_tier_id"],
                [constraint["column_names"] for constraint in unique],
            )
        finally:
            engine.dispose()

    def test_full_downgrade_and_re_upgrade(self) -> None:
        config = self._config()
        command.upgrade(config, "head")
        command.downgrade(config, "base")
        command.upgrade(config, "head")

        self.assertIn("restock_inherit", self._category_columns())


if __name__ == "__main__":
    unittest.main()
