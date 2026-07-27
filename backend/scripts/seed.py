#!/usr/bin/env python3
"""Load the food catalog fixtures into the database.

Run via:  just seed
          cd backend && uv run python scripts/seed.py
"""

import json
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Allow importing from the app package (script lives in backend/scripts/)
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import (
    Category,
    InventoryTransaction,
    Product,
    ProductRevision,
    Profile,
    ProfileAchievement,
    ProfileReward,
    RewardTier,
    level_for_xp,
)
from app.services.achievements import check_progress
from app.services.progression import award_transaction

FIXTURES = Path(__file__).parent.parent / "fixtures" / "food_catalog.json"
SEED_DAYS_SPAN = 30
SEED_STOCK_MULTIPLIER = 3

# Sample household profiles. Movements are attributed (see main) so the two end
# up with *different* badges, showcasing achievements out of the box. `base` is a
# stable part id (never a glyph) and the colors match the frontend presets in
# `lib/profiles.ts` / `lib/theme.ts`.
SEED_PROFILES = [
    {"name": "Mia", "avatar_config": {"base": "fox", "color": "#e8a33d"}},
    {"name": "Leo", "avatar_config": {"base": "bear", "color": "#3498db"}},
]

# Household-wide reward tiers (WL-5.4). Chosen against the XP the seed awards so
# both states are on screen: Mia ends at level 2 (L2 unlocked 🎁 + redeemable),
# Leo at level 1 (both locked 🔒). Redemption itself is left unseeded — checking
# one off is the real-life action the feature exists for.
SEED_REWARDS = [
    {"level": 2, "description": "Pick tonight's dessert"},
    {"level": 5, "description": "Pick movie night"},
]


def main() -> None:
    settings = Settings()
    engine = create_engine(settings.database_url, echo=False)

    with Session(engine) as session:
        n_cats = session.execute(select(func.count(Category.id))).scalar_one()
        n_prods = session.execute(select(func.count(Product.id))).scalar_one()

        if n_cats > 0 or n_prods > 0:
            print(f"Database already contains {n_cats} categories and {n_prods} products.")
            try:
                answer = input("Delete existing data and re-seed? [y/N] ").strip().lower()
            except EOFError:
                answer = ""
            if answer != "y":
                print("Aborted.")
                sys.exit(0)

            # Children first (they reference products/profiles/reward tiers).
            # Achievements and redemptions must go too: SQLite reuses profile ids
            # after a delete-all, so orphaned rows would collide with the re-seeded
            # profiles — suppressing badge re-granting (check_progress would see
            # them as already earned) and showing rewards as pre-redeemed.
            session.execute(InventoryTransaction.__table__.delete())
            session.execute(ProductRevision.__table__.delete())
            session.execute(ProfileAchievement.__table__.delete())
            session.execute(ProfileReward.__table__.delete())
            session.execute(RewardTier.__table__.delete())
            session.execute(Product.__table__.delete())
            session.execute(Category.__table__.delete())
            session.execute(Profile.__table__.delete())
            session.commit()
            print("Cleared existing data.")

        catalog = json.loads(FIXTURES.read_text())

        profiles = [Profile(**prof_def) for prof_def in SEED_PROFILES]
        session.add_all(profiles)
        session.flush()

        rewards = [RewardTier(**reward_def) for reward_def in SEED_REWARDS]
        session.add_all(rewards)

        # Insert categories in declaration order so parents resolve before children.
        cat_map: dict[str, int] = {}
        for cat_def in catalog["categories"]:
            parent_id = cat_map.get(cat_def["parent"]) if "parent" in cat_def else None
            cat = Category(
                name=cat_def["name"],
                icon=cat_def.get("icon"),
                parent_id=parent_id,
            )
            session.add(cat)
            session.flush()
            cat_map[cat_def["name"]] = cat.id

        # Attribution is designed so the two profiles end up with *different*
        # badges: Mia shops on a long consecutive run (earns the 7-day streak),
        # Leo only on scattered days (first-scan alone). XP, streaks and badges
        # are then *derived* from these movements by replaying them through the
        # real award services below — the seed can't drift from how the app
        # actually grants them.
        mia, leo = profiles
        leo_days = {0, 2, 4, 6, 8, 10}  # alternating days: Leo's streak never builds
        movements: dict[int, list[datetime]] = {mia.id: [], leo.id: []}

        # Insert products and initial "in" transactions spread across recent days.
        now = datetime.now(UTC)
        stock_seq = 0
        for prod_def in catalog["products"]:
            cat_id = cat_map.get(prod_def["category"]) if "category" in prod_def else None
            product = Product(
                ean=prod_def.get("ean"),
                name=prod_def["name"],
                brand=prod_def.get("brand"),
                category_id=cat_id,
                image_url=prod_def.get("image_url"),
            )
            session.add(product)
            session.flush()

            stock = int(prod_def.get("stock", 0)) * SEED_STOCK_MULTIPLIER
            if stock > 0:
                # One consecutive day per stocked product, so streaks are well-defined.
                day_offset = stock_seq % SEED_DAYS_SPAN
                stock_seq += 1
                txn_day = now - timedelta(days=day_offset)

                # Stable pseudo-randomized time within the day from EAN/name seed.
                seed_basis = prod_def.get("ean") or prod_def["name"]
                rng = random.Random(seed_basis)
                txn_time = txn_day.replace(
                    hour=rng.randint(8, 20),
                    minute=rng.randint(0, 59),
                    second=rng.randint(0, 59),
                    microsecond=0,
                )

                owner = leo if day_offset in leo_days else mia
                session.add(
                    InventoryTransaction(
                        product_id=product.id,
                        profile_id=owner.id,
                        type="in",
                        quantity=stock,
                        transacted_at=txn_time,
                        notes=f"Initial stock (seed, -{day_offset}d)",
                    ),
                )
                movements[owner.id].append(txn_time)

        # Derive XP, streaks and badges exactly as the API would, replaying each
        # profile's movements oldest-first.
        granted: dict[str, list[str]] = {}
        for profile in profiles:
            for txn_time in sorted(movements[profile.id]):
                award_transaction(profile, "in", today=txn_time.date())
            granted[profile.name] = check_progress(session, profile)

        # The seed exists to showcase the feature — the profiles must differ.
        assert granted[mia.name] != granted[leo.name], granted

        # Likewise for rewards: one tier reachable, one still out of reach, so both
        # 🎁 and 🔒 render. Catches SEED_REWARDS drifting out of the seeded XP range.
        mia_level = level_for_xp(mia.xp)
        reward_levels = [reward.level for reward in rewards]
        assert any(level <= mia_level for level in reward_levels), (mia_level, reward_levels)
        assert any(level > mia_level for level in reward_levels), (mia_level, reward_levels)

        session.commit()

    n_seeded = len(catalog["products"])
    n_cats_seeded = len(catalog["categories"])
    print(
        f"Seeded {n_cats_seeded} categories, {n_seeded} products, "
        f"{len(SEED_PROFILES)} profiles, and {len(SEED_REWARDS)} reward tiers."
    )
    for name, badges in granted.items():
        print(f"  {name}: {', '.join(badges) or 'no badges'}")
    for reward_def in SEED_REWARDS:
        print(f"  reward L{reward_def['level']}: {reward_def['description']}")


if __name__ == "__main__":
    main()
