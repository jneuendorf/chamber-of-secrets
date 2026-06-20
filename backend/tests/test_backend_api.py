import contextlib
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
_TEMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)  # noqa: SIM115
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
        with contextlib.suppress(OSError):
            Path(cls._db_path).unlink(missing_ok=True)

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

    def test_category_create_with_nonexistent_parent_returns_404(self) -> None:
        res = self.client.post(
            "/api/categories/", json={"name": "Orphan", "parent_id": 999999}
        )
        self.assertEqual(res.status_code, 404)
        self.assertIn("parent", res.json()["detail"].lower())

    def test_category_create_cannot_self_reference(self) -> None:
        # parent_id must point to an existing category, so a new category
        # can never reference itself — the ID doesn't exist yet.
        res = self.client.post(
            "/api/categories/", json={"name": "Loop", "parent_id": 1}
        )
        # Either 404 (no category with id=1) or 201 if id=1 happens to
        # exist from a prior insert — either way, no cycle is possible.
        if res.status_code == 201:
            body = res.json()
            self.assertNotEqual(body["id"], body["parent_id"])

    def test_category_deep_cycle_prevention(self) -> None:
        a = self._create_category("A")
        b = self._create_category("B", parent_id=a["id"])
        c = self._create_category("C", parent_id=b["id"])

        # Try to close the loop: A → B → C → A
        res = self.client.patch(
            f"/api/categories/{a['id']}", json={"parent_id": c["id"]}
        )
        self.assertEqual(res.status_code, 422)
        self.assertIn("cycle", res.json()["detail"].lower())

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

    # ---------- Product image upload ----------

    def test_upload_product_image_success(self) -> None:
        product = self._create_product("Milk")
        res = self.client.post(
            f"/api/products/{product['id']}/image",
            files={"file": ("milk.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
        )
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertTrue(body["image_url"].startswith("/api/uploads/products/"))
        self.assertTrue(body["image_url"].endswith(".jpg"))

    def test_upload_product_image_replaces_old(self) -> None:
        product = self._create_product("Butter")
        content_a = b"\x89PNG\r\n\x1a\n" + b"\xaa" * 100
        content_b = b"\x89PNG\r\n\x1a\n" + b"\xbb" * 100

        first = self.client.post(
            f"/api/products/{product['id']}/image",
            files={"file": ("a.png", content_a, "image/png")},
        )
        self.assertEqual(first.status_code, 200)
        first_url = first.json()["image_url"]

        second = self.client.post(
            f"/api/products/{product['id']}/image",
            files={"file": ("b.png", content_b, "image/png")},
        )
        self.assertEqual(second.status_code, 200)
        second_url = second.json()["image_url"]
        self.assertNotEqual(second_url, first_url)

        served = self.client.get(second_url)
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served.content, content_b)

    def test_upload_product_image_rejects_non_image(self) -> None:
        product = self._create_product("Cheese")
        res = self.client.post(
            f"/api/products/{product['id']}/image",
            files={"file": ("data.txt", b"hello", "text/plain")},
        )
        self.assertEqual(res.status_code, 422)

    def test_upload_product_image_rejects_spoofed_content_type(self) -> None:
        product = self._create_product("Ham")
        res = self.client.post(
            f"/api/products/{product['id']}/image",
            files={"file": ("evil.jpg", b"<html>not an image</html>", "image/jpeg")},
        )
        self.assertEqual(res.status_code, 422)

    def test_upload_product_image_not_found(self) -> None:
        res = self.client.post(
            "/api/products/999999/image",
            files={"file": ("img.jpg", b"\xff\xd8\xff\xe0", "image/jpeg")},
        )
        self.assertEqual(res.status_code, 404)

    def test_delete_product_image(self) -> None:
        product = self._create_product("Eggs")
        self.client.post(
            f"/api/products/{product['id']}/image",
            files={"file": ("egg.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 100, "image/jpeg")},
        )
        res = self.client.delete(f"/api/products/{product['id']}/image")
        self.assertEqual(res.status_code, 204)

        fetched = self.client.get(f"/api/products/{product['id']}")
        self.assertIsNone(fetched.json()["image_url"])

    # ---------- Product update with image_url ----------

    def test_update_product_image_url_via_patch(self) -> None:
        product = self._create_product("Rice")
        res = self.client.patch(
            f"/api/products/{product['id']}",
            json={"image_url": "https://example.com/rice.jpg"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["image_url"], "https://example.com/rice.jpg")

    def test_update_product_partial_does_not_clear_other_fields(self) -> None:
        product = self._create_product("Pasta")
        self.client.patch(
            f"/api/products/{product['id']}",
            json={"image_url": "https://example.com/pasta.jpg"},
        )
        res = self.client.patch(
            f"/api/products/{product['id']}",
            json={"category_id": None},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["image_url"], "https://example.com/pasta.jpg")

    # ---------- Category delete ----------

    def test_delete_category_success(self) -> None:
        cat = self._create_category("ToDelete")
        res = self.client.delete(f"/api/categories/{cat['id']}")
        self.assertEqual(res.status_code, 204)

        listing = self.client.get("/api/categories/")
        names = [c["name"] for c in listing.json()]
        self.assertNotIn("ToDelete", names)

    def test_delete_category_not_found(self) -> None:
        res = self.client.delete("/api/categories/999999")
        self.assertEqual(res.status_code, 404)

    def test_delete_category_with_products_rejected(self) -> None:
        cat = self._create_category("HasProducts")
        self._create_product("Bread", category_id=cat["id"])

        res = self.client.delete(f"/api/categories/{cat['id']}")
        self.assertEqual(res.status_code, 409)
        self.assertIn("products", res.json()["detail"].lower())

    def test_delete_category_reparents_children(self) -> None:
        grandparent = self._create_category("Grandparent")
        parent = self._create_category("Parent", parent_id=grandparent["id"])
        child = self._create_category("Child", parent_id=parent["id"])

        res = self.client.delete(f"/api/categories/{parent['id']}")
        self.assertEqual(res.status_code, 204)

        updated_child = next(
            c for c in self.client.get("/api/categories/").json() if c["id"] == child["id"]
        )
        self.assertEqual(updated_child["parent_id"], grandparent["id"])

    def test_delete_root_category_reparents_children_to_null(self) -> None:
        root = self._create_category("Root")
        child = self._create_category("Child", parent_id=root["id"])

        res = self.client.delete(f"/api/categories/{root['id']}")
        self.assertEqual(res.status_code, 204)

        updated_child = next(
            c for c in self.client.get("/api/categories/").json() if c["id"] == child["id"]
        )
        self.assertIsNone(updated_child["parent_id"])


if __name__ == "__main__":
    unittest.main()
