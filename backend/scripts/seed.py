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
from app.models import Category, InventoryTransaction, Product, ProductRevision

FIXTURES = Path(__file__).parent.parent / "fixtures" / "food_catalog.json"
SEED_DAYS_SPAN = 30
SEED_STOCK_MULTIPLIER = 3


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

            session.execute(InventoryTransaction.__table__.delete())
            session.execute(ProductRevision.__table__.delete())
            session.execute(Product.__table__.delete())
            session.execute(Category.__table__.delete())
            session.commit()
            print("Cleared existing data.")

        catalog = json.loads(FIXTURES.read_text())

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

        # Insert products and initial "in" transactions spread across recent days.
        now = datetime.now(UTC)
        for idx, prod_def in enumerate(catalog["products"]):
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
                # Deterministic but varied dates for analytics charts.
                day_offset = idx % SEED_DAYS_SPAN
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

                session.add(
                    InventoryTransaction(
                        product_id=product.id,
                        type="in",
                        quantity=stock,
                        transacted_at=txn_time,
                        notes=f"Initial stock (seed, -{day_offset}d)",
                    )
                )

        session.commit()

    n_seeded = len(catalog["products"])
    n_cats_seeded = len(catalog["categories"])
    print(f"Seeded {n_cats_seeded} categories and {n_seeded} products.")


if __name__ == "__main__":
    main()
