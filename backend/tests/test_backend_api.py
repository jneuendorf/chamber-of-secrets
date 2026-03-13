import os
import sys
import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure app settings pick up a test DB before importing app modules.
_TEMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TEMP_DB.close()
os.environ["APP_DATABASE_URL"] = f"sqlite:///{_TEMP_DB.name}"

# Ensure backend/app is importable when tests run from repository root.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


class BackendAPITestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._db_path = _TEMP_DB.name
        cls._engine = create_engine(
            f"sqlite:///{cls._db_path}",
            connect_args={"check_same_thread": False},
        )
        cls._SessionLocal = sessionmaker(bind=cls._engine)

        Base.metadata.drop_all(bind=cls._engine)
        Base.metadata.create_all(bind=cls._engine)

        def override_get_db() -> Generator[Session]:
            db = cls._SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls._engine.dispose()
        try:
            Path(cls._db_path).unlink(missing_ok=True)
        except OSError:
            pass

    def setUp(self) -> None:
        # Keep tests isolated but fast by resetting tables each test.
        Base.metadata.drop_all(bind=self._engine)
        Base.metadata.create_all(bind=self._engine)

    # ---------- Helpers ----------

    def _create_category(self, name: str, **extra: object) -> dict:
        payload = {"name": name, **extra}
        res = self.client.post("/api/categories/", json=payload)
        self.assertEqual(res.status_code, 201, res.text)
        return res.json()

    def _create_product(self, name: str, **extra: object) -> dict:
        payload = {"name": name, **extra}
        res = self.client.post("/api/products/", json=payload)
        self.assertEqual(res.status_code, 201, res.text)
        return res.json()

    # ---------- Route availability + basic JSON shape ----------

    def test_health_route_available_and_shape(self) -> None:
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIsInstance(body, dict)
        self.assertEqual(set(body.keys()), {"status"})
        self.assertEqual(body["status"], "ok")

    def test_products_list_route_available_and_shape(self) -> None:
        res = self.client.get("/api/products/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIsInstance(body, list)

    def test_categories_list_route_available_and_shape(self) -> None:
        res = self.client.get("/api/categories/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIsInstance(body, list)

    def test_transactions_list_route_available_and_shape(self) -> None:
        res = self.client.get("/api/transactions/")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIsInstance(body, list)

    def test_analytics_routes_available_and_shape(self) -> None:
        spending = self.client.get("/api/analytics/spending")
        self.assertEqual(spending.status_code, 200)
        self.assertIsInstance(spending.json(), list)

        timeseries = self.client.get("/api/analytics/timeseries")
        self.assertEqual(timeseries.status_code, 200)
        self.assertIsInstance(timeseries.json(), list)

        restock = self.client.get("/api/analytics/restock-overview")
        self.assertEqual(restock.status_code, 200)
        payload = restock.json()
        self.assertIsInstance(payload, dict)
        self.assertTrue(
            {
                "rows",
                "total_missing_quantity",
                "total_products_needing_restock",
                "by_child_category",
                "by_parent_category",
            }.issubset(payload.keys())
        )

    # ---------- JSON contract checks ----------

    def test_create_and_get_product_json_shape(self) -> None:
        category = self._create_category("Dairy")
        created = self._create_product(
            "Milk",
            ean="1234567890123",
            brand="Farm",
            category_id=category["id"],
            image_url="https://example.com/milk.jpg",
        )

        self.assertTrue(
            {
                "id",
                "ean",
                "name",
                "brand",
                "category_id",
                "image_url",
                "created_at",
                "updated_at",
            }.issubset(created.keys())
        )

        fetched = self.client.get(f"/api/products/{created['id']}")
        self.assertEqual(fetched.status_code, 200)
        body = fetched.json()

        self.assertTrue(
            {
                "id",
                "ean",
                "name",
                "brand",
                "category_id",
                "image_url",
                "created_at",
                "updated_at",
                "stock",
                "category",
            }.issubset(body.keys())
        )
        self.assertEqual(body["name"], "Milk")
        self.assertEqual(body["stock"], 0.0)
        self.assertIsInstance(body["category"], dict)
        self.assertEqual(body["category"]["name"], "Dairy")

    def test_create_transaction_json_shape(self) -> None:
        product = self._create_product("Rice")
        res = self.client.post(
            "/api/transactions/",
            json={
                "product_id": product["id"],
                "type": "in",
                "quantity": 2.5,
                "unit_price": 3.2,
                "notes": "weekly buy",
            },
        )
        self.assertEqual(res.status_code, 201, res.text)
        body = res.json()
        self.assertTrue(
            {
                "id",
                "product_id",
                "type",
                "quantity",
                "unit_price",
                "transacted_at",
                "notes",
            }.issubset(body.keys())
        )
        self.assertEqual(body["type"], "in")
        self.assertEqual(body["quantity"], 2.5)

    # ---------- Business logic checks ----------

    def test_product_stock_is_derived_from_transactions(self) -> None:
        product = self._create_product("Flour")

        # +5 in
        res_in = self.client.post(
            "/api/transactions/",
            json={"product_id": product["id"], "type": "in", "quantity": 5},
        )
        self.assertEqual(res_in.status_code, 201, res_in.text)

        # -2 out
        res_out = self.client.post(
            "/api/transactions/",
            json={"product_id": product["id"], "type": "out", "quantity": 2},
        )
        self.assertEqual(res_out.status_code, 201, res_out.text)

        fetched = self.client.get(f"/api/products/{product['id']}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["stock"], 3.0)

    def test_transaction_for_missing_product_returns_404(self) -> None:
        res = self.client.post(
            "/api/transactions/",
            json={"product_id": 999999, "type": "in", "quantity": 1},
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json().get("detail"), "Product not found")

    def test_category_cycle_prevention(self) -> None:
        parent = self._create_category("Parent")
        child = self._create_category("Child", parent_id=parent["id"])

        # Try to set Parent -> Child while Child already points to Parent.
        res = self.client.patch(
            f"/api/categories/{parent['id']}",
            json={"parent_id": child["id"]},
        )
        self.assertEqual(res.status_code, 422)
        self.assertIn("cycle", res.json().get("detail", "").lower())

    def test_restock_overview_business_logic_needs_restock_and_totals(self) -> None:
        cat = self._create_category("Pantry", restock_target=10.0, restock_min=4.0)
        product = self._create_product("Pasta", category_id=cat["id"])

        # Current stock = 3, so below min and missing to target should be 7.
        tx = self.client.post(
            "/api/transactions/",
            json={"product_id": product["id"], "type": "in", "quantity": 3.0},
        )
        self.assertEqual(tx.status_code, 201, tx.text)

        res = self.client.get("/api/analytics/restock-overview")
        self.assertEqual(res.status_code, 200)
        payload = res.json()

        rows = payload["rows"]
        self.assertEqual(len(rows), 1)
        row = rows[0]

        self.assertEqual(row["name"], "Pasta")
        self.assertEqual(row["current_stock"], 3.0)
        self.assertEqual(row["effective_target"], 10.0)
        self.assertEqual(row["effective_min"], 4.0)
        self.assertEqual(row["missing_to_target"], 7.0)
        self.assertTrue(row["below_min"])
        self.assertTrue(row["needs_restock"])

        self.assertEqual(payload["total_missing_quantity"], 7.0)
        self.assertEqual(payload["total_products_needing_restock"], 1)


if __name__ == "__main__":
    unittest.main()
