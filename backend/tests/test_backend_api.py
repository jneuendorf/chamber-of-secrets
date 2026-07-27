import contextlib
import os
import sys
import tempfile
import unittest
import unittest.mock
from collections.abc import Generator
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
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
from app.models import Base, InventoryTransaction, Profile  # noqa: E402
from app.routers import products as products_router  # noqa: E402
from app.services.achievements import (  # noqa: E402
    EXPLORER,
    FIRST_SCAN,
    LEVEL_5,
    STOCKED_50,
    STREAK_7,
)
from app.services.progression import XP_PER_EVENT, bump_streak  # noqa: E402


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
            }.issubset(payload.keys()),
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
            }.issubset(created.keys()),
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
            }.issubset(body.keys()),
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
            }.issubset(body.keys()),
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
            "/api/categories/",
            json={"name": "Orphan", "parent_id": 999999},
        )
        self.assertEqual(res.status_code, 404)
        self.assertIn("parent", res.json()["detail"].lower())

    def test_category_create_cannot_self_reference(self) -> None:
        # parent_id must point to an existing category, so a new category
        # can never reference itself — the ID doesn't exist yet.
        res = self.client.post(
            "/api/categories/",
            json={"name": "Loop", "parent_id": 1},
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
            f"/api/categories/{a['id']}",
            json={"parent_id": c["id"]},
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

    # ---------- Transaction edit / delete (WL-4.2) ----------

    def _add_transaction(self, product_id: int, **extra: object) -> dict:
        payload = {"product_id": product_id, "type": "in", "quantity": 1, **extra}
        res = self.client.post("/api/transactions/", json=payload)
        self.assertEqual(res.status_code, 201, res.text)
        return res.json()

    def test_delete_transaction_recomputes_stock(self) -> None:
        product = self._create_product("Beans")
        first = self._add_transaction(product["id"], quantity=5)
        self._add_transaction(product["id"], quantity=3)

        res = self.client.delete(f"/api/transactions/{first['id']}")
        self.assertEqual(res.status_code, 204)

        fetched = self.client.get(f"/api/products/{product['id']}")
        self.assertEqual(fetched.json()["stock"], 3.0)

    def test_delete_transaction_not_found(self) -> None:
        res = self.client.delete("/api/transactions/999999")
        self.assertEqual(res.status_code, 404)

    def test_patch_transaction_updates_fields_and_stock(self) -> None:
        product = self._create_product("Corn")
        txn = self._add_transaction(product["id"], quantity=2)

        res = self.client.patch(
            f"/api/transactions/{txn['id']}",
            json={"quantity": 8, "type": "in", "unit_price": 1.5},
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["quantity"], 8.0)

        fetched = self.client.get(f"/api/products/{product['id']}")
        self.assertEqual(fetched.json()["stock"], 8.0)

    def test_patch_transaction_rejects_non_positive_quantity(self) -> None:
        product = self._create_product("Oats")
        txn = self._add_transaction(product["id"])
        res = self.client.patch(f"/api/transactions/{txn['id']}", json={"quantity": 0})
        self.assertEqual(res.status_code, 422)

    # ---------- Product delete + merge (WL-4.2) ----------

    def test_delete_product_cascades_transactions(self) -> None:
        product = self._create_product("Sugar")
        self._add_transaction(product["id"], quantity=4)

        res = self.client.delete(f"/api/products/{product['id']}")
        self.assertEqual(res.status_code, 204)

        self.assertEqual(self.client.get(f"/api/products/{product['id']}").status_code, 404)
        listing = self.client.get(f"/api/transactions/?product_id={product['id']}").json()
        self.assertEqual(listing, [])

    def test_delete_product_not_found(self) -> None:
        res = self.client.delete("/api/products/999999")
        self.assertEqual(res.status_code, 404)

    def test_delete_product_frees_category(self) -> None:
        # The category-delete dead end (WL-4.2): once its only product is gone,
        # the category can be deleted.
        cat = self._create_category("Snacks")
        product = self._create_product("Chips", category_id=cat["id"])
        self.assertEqual(self.client.delete(f"/api/categories/{cat['id']}").status_code, 409)

        self.client.delete(f"/api/products/{product['id']}")
        self.assertEqual(self.client.delete(f"/api/categories/{cat['id']}").status_code, 204)

    def test_merge_products_repoints_transactions(self) -> None:
        keep = self._create_product("Milk 1L")
        dupe = self._create_product("Milk one litre")
        self._add_transaction(keep["id"], quantity=2)
        self._add_transaction(dupe["id"], quantity=5)

        res = self.client.post(
            "/api/products/merge",
            json={"source_id": dupe["id"], "target_id": keep["id"]},
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["id"], keep["id"])
        self.assertEqual(res.json()["stock"], 7.0)

        self.assertEqual(self.client.get(f"/api/products/{dupe['id']}").status_code, 404)

    def test_merge_products_rejects_same_id(self) -> None:
        product = self._create_product("Water")
        res = self.client.post(
            "/api/products/merge",
            json={"source_id": product["id"], "target_id": product["id"]},
        )
        self.assertEqual(res.status_code, 422)

    def test_merge_products_missing_returns_404(self) -> None:
        product = self._create_product("Juice")
        res = self.client.post(
            "/api/products/merge",
            json={"source_id": 999999, "target_id": product["id"]},
        )
        self.assertEqual(res.status_code, 404)

    # ---------- WL-4.6: contribute back to Open Food Facts ----------

    def test_contribute_without_ean_returns_400(self) -> None:
        product = self._create_product("Loose apples")  # no EAN
        res = self.client.post(f"/api/products/{product['id']}/contribute")
        self.assertEqual(res.status_code, 400)

    def test_contribute_missing_product_returns_404(self) -> None:
        res = self.client.post("/api/products/999999/contribute")
        self.assertEqual(res.status_code, 404)

    def test_contribute_success(self) -> None:
        product = self._create_product("Store bread", ean="4001234567890")
        with unittest.mock.patch(
            "app.routers.products.contribute_product",
            new=unittest.mock.AsyncMock(return_value=True),
        ) as mocked:
            res = self.client.post(f"/api/products/{product['id']}/contribute")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"ok": True})
        mocked.assert_awaited_once()

    def test_contribute_rejected_returns_502(self) -> None:
        product = self._create_product("Store bread", ean="4001234567890")
        with unittest.mock.patch(
            "app.routers.products.contribute_product",
            new=unittest.mock.AsyncMock(return_value=False),
        ):
            res = self.client.post(f"/api/products/{product['id']}/contribute")
        self.assertEqual(res.status_code, 502)

    def test_contribute_uploads_local_image_when_enabled(self) -> None:
        product = self._create_product("Store bread", ean="4001234567890")
        self.client.post(
            f"/api/products/{product['id']}/image",
            files={"file": ("bread.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")},
        )
        image_mock = unittest.mock.AsyncMock(return_value=True)
        with (
            unittest.mock.patch(
                "app.routers.products.contribute_product",
                new=unittest.mock.AsyncMock(return_value=True),
            ),
            unittest.mock.patch("app.routers.products.contribute_image", new=image_mock),
            unittest.mock.patch.object(
                products_router.settings,
                "off_contribute_images",
                True,
            ),
        ):
            res = self.client.post(f"/api/products/{product['id']}/contribute")
        self.assertEqual(res.status_code, 200)
        image_mock.assert_awaited_once()

    def test_contribute_skips_image_when_disabled(self) -> None:
        product = self._create_product("Store bread", ean="4001234567890")
        self.client.post(
            f"/api/products/{product['id']}/image",
            files={"file": ("bread.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")},
        )
        image_mock = unittest.mock.AsyncMock(return_value=True)
        with (
            unittest.mock.patch(
                "app.routers.products.contribute_product",
                new=unittest.mock.AsyncMock(return_value=True),
            ),
            unittest.mock.patch("app.routers.products.contribute_image", new=image_mock),
        ):
            res = self.client.post(f"/api/products/{product['id']}/contribute")
        self.assertEqual(res.status_code, 200)
        image_mock.assert_not_awaited()

    def test_delete_root_category_reparents_children_to_null(self) -> None:
        root = self._create_category("Root")
        child = self._create_category("Child", parent_id=root["id"])

        res = self.client.delete(f"/api/categories/{root['id']}")
        self.assertEqual(res.status_code, 204)

        updated_child = next(
            c for c in self.client.get("/api/categories/").json() if c["id"] == child["id"]
        )
        self.assertIsNone(updated_child["parent_id"])

    # ---------- WL-5.1: profiles & attribution ----------

    def test_create_profile_defaults_and_derived_level(self) -> None:
        res = self.client.post(
            "/api/profiles/",
            json={"name": "  Mia  ", "avatar_config": {"base": "fox", "color": "#e8a33d"}},
        )
        self.assertEqual(res.status_code, 201, res.text)
        body = res.json()
        self.assertEqual(body["name"], "Mia")  # trimmed
        self.assertEqual(body["xp"], 0)
        self.assertEqual(body["level"], 1)  # derived from xp, never stored
        self.assertFalse(body["is_archived"])
        self.assertEqual(body["avatar_config"], {"base": "fox", "color": "#e8a33d"})

    def test_create_profile_rejects_blank_name(self) -> None:
        res = self.client.post("/api/profiles/", json={"name": "   "})
        self.assertEqual(res.status_code, 422)

    def test_list_profiles_excludes_archived_by_default(self) -> None:
        keep = self.client.post("/api/profiles/", json={"name": "Keep"}).json()
        gone = self.client.post("/api/profiles/", json={"name": "Gone"}).json()
        self.client.patch(f"/api/profiles/{gone['id']}", json={"is_archived": True})

        ids = {p["id"] for p in self.client.get("/api/profiles/").json()}
        self.assertIn(keep["id"], ids)
        self.assertNotIn(gone["id"], ids)

        all_ids = {p["id"] for p in self.client.get("/api/profiles/?include_archived=true").json()}
        self.assertIn(gone["id"], all_ids)

    def test_patch_profile_not_found(self) -> None:
        res = self.client.patch("/api/profiles/999999", json={"name": "Nope"})
        self.assertEqual(res.status_code, 404)

    def test_transaction_records_profile_attribution(self) -> None:
        profile = self.client.post("/api/profiles/", json={"name": "Leo"}).json()
        product = self._create_product("Milk")
        res = self.client.post(
            "/api/transactions/",
            json={"product_id": product["id"], "profile_id": profile["id"], "type": "in"},
        )
        self.assertEqual(res.status_code, 201, res.text)
        self.assertEqual(res.json()["profile_id"], profile["id"])

    def test_transaction_with_unknown_profile_returns_404(self) -> None:
        product = self._create_product("Butter")
        res = self.client.post(
            "/api/transactions/",
            json={"product_id": product["id"], "profile_id": 999999, "type": "in"},
        )
        self.assertEqual(res.status_code, 404)

    def test_db_rejects_orphan_transaction(self) -> None:
        # Backstop behind the router guards: a direct write with a dangling
        # product_id must be refused by SQLite itself (PRAGMA foreign_keys=ON),
        # proving the constraint is enforced, not just documented.
        db = self._SessionLocal()
        try:
            db.add(InventoryTransaction(product_id=999999, type="in", quantity=1))
            with self.assertRaises(IntegrityError):
                db.flush()
        finally:
            db.rollback()
            db.close()

    def test_transaction_allows_archived_profile(self) -> None:
        # A device may hold a stale selection until its next reload; the row still
        # exists, so attribution stays valid rather than failing mid-scan.
        profile = self.client.post("/api/profiles/", json={"name": "Ada"}).json()
        self.client.patch(f"/api/profiles/{profile['id']}", json={"is_archived": True})
        product = self._create_product("Yoghurt")
        res = self.client.post(
            "/api/transactions/",
            json={"product_id": product["id"], "profile_id": profile["id"], "type": "in"},
        )
        self.assertEqual(res.status_code, 201, res.text)
        self.assertEqual(res.json()["profile_id"], profile["id"])

    def test_transaction_without_profile_is_null(self) -> None:
        product = self._create_product("Eggs")
        res = self.client.post(
            "/api/transactions/",
            json={"product_id": product["id"], "type": "in"},
        )
        self.assertEqual(res.status_code, 201, res.text)
        self.assertIsNone(res.json()["profile_id"])

    # ---------- WL-5.3: progression (XP, levels, streaks) ----------

    def test_attributed_transactions_award_xp_and_level_up(self) -> None:
        profile = self.client.post("/api/profiles/", json={"name": "Nia"}).json()
        product = self._create_product("Oats")
        for _ in range(10):
            self.client.post(
                "/api/transactions/",
                json={"product_id": product["id"], "profile_id": profile["id"], "type": "in"},
            )

        updated = self._get_profile(profile["id"])
        self.assertEqual(updated["xp"], 10 * XP_PER_EVENT["in"])
        self.assertEqual(updated["level"], 2)  # 100 XP crosses the first threshold
        self.assertEqual(updated["current_streak"], 1)
        self.assertEqual(updated["longest_streak"], 1)

    def test_unattributed_transaction_awards_nothing(self) -> None:
        profile = self.client.post("/api/profiles/", json={"name": "Ravi"}).json()
        product = self._create_product("Rice")
        self.client.post("/api/transactions/", json={"product_id": product["id"], "type": "in"})

        self.assertEqual(self._get_profile(profile["id"])["xp"], 0)

    def test_streak_extends_on_consecutive_days_and_resets_after_a_gap(self) -> None:
        # Column defaults only apply on insert, so a transient row needs them set.
        profile = Profile(name="Streaky", current_streak=0, longest_streak=0)
        today = date(2026, 7, 19)

        bump_streak(profile, today - timedelta(days=1))
        bump_streak(profile, today)
        self.assertEqual(profile.current_streak, 2)

        bump_streak(profile, today)  # same day again: no double count
        self.assertEqual(profile.current_streak, 2)

        bump_streak(profile, today + timedelta(days=3))  # gap
        self.assertEqual(profile.current_streak, 1)
        self.assertEqual(profile.longest_streak, 2)

    # ---------- WL-5.4: achievements ----------

    def test_first_stocking_earns_first_scan_only_once(self) -> None:
        profile = self.client.post("/api/profiles/", json={"name": "Ana"}).json()
        product = self._create_product("Beans")
        self.assertEqual(profile["achievements"], [])

        for _ in range(3):
            self.client.post(
                "/api/transactions/",
                json={"product_id": product["id"], "profile_id": profile["id"], "type": "in"},
            )

        self.assertEqual(self._get_profile(profile["id"])["achievements"], [FIRST_SCAN])

    def test_stocking_milestone_and_level_badges_stack(self) -> None:
        profile = self.client.post("/api/profiles/", json={"name": "Bo"}).json()
        product = self._create_product("Pasta")
        for _ in range(50):
            self.client.post(
                "/api/transactions/",
                json={"product_id": product["id"], "profile_id": profile["id"], "type": "in"},
            )

        earned = self._get_profile(profile["id"])["achievements"]
        # 500 XP → level 3, so LEVEL_5 must not be handed out yet.
        self.assertEqual(set(earned), {FIRST_SCAN, STOCKED_50})
        self.assertNotIn(LEVEL_5, earned)

    def test_consuming_alone_earns_no_stocking_badge(self) -> None:
        profile = self.client.post("/api/profiles/", json={"name": "Cy"}).json()
        product = self._create_product("Tea")
        self.client.post("/api/transactions/", json={"product_id": product["id"], "type": "in"})
        self.client.post(
            "/api/transactions/",
            json={"product_id": product["id"], "profile_id": profile["id"], "type": "out"},
        )

        self.assertEqual(self._get_profile(profile["id"])["achievements"], [])

    def test_streak_badge_lands_once_the_longest_streak_reaches_target(self) -> None:
        profile = self.client.post("/api/profiles/", json={"name": "Di"}).json()
        with self._SessionLocal() as session:
            row = session.get(Profile, profile["id"])
            assert row is not None
            row.longest_streak = 7  # the streak_7 threshold
            session.commit()

        product = self._create_product("Milk")
        self.client.post(
            "/api/transactions/",
            json={"product_id": product["id"], "profile_id": profile["id"], "type": "in"},
        )

        self.assertIn(STREAK_7, self._get_profile(profile["id"])["achievements"])

    def test_contributing_to_off_earns_explorer_for_the_active_profile(self) -> None:
        profile = self.client.post("/api/profiles/", json={"name": "Eli"}).json()
        product = self._create_product("Local jam", ean="4009876543210")
        with unittest.mock.patch(
            "app.routers.products.contribute_product",
            new=unittest.mock.AsyncMock(return_value=True),
        ):
            res = self.client.post(
                f"/api/products/{product['id']}/contribute?profile_id={profile['id']}",
            )

        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._get_profile(profile["id"])["achievements"], [EXPLORER])

    def test_reward_tiers_created_and_listed_sorted_by_level(self) -> None:
        self.client.post("/api/rewards/", json={"level": 5, "description": "Movie night"})
        self.client.post("/api/rewards/", json={"level": 2, "description": "Ice cream"})
        rewards = self.client.get("/api/rewards/").json()
        self.assertEqual([r["level"] for r in rewards], [2, 5])
        self.assertEqual(rewards[0]["description"], "Ice cream")

    def test_reward_tier_rejects_level_below_two(self) -> None:
        res = self.client.post("/api/rewards/", json={"level": 1, "description": "Nope"})
        self.assertEqual(res.status_code, 422)

    def test_reward_tier_rejects_blank_description(self) -> None:
        res = self.client.post("/api/rewards/", json={"level": 3, "description": "   "})
        self.assertEqual(res.status_code, 422)

    def test_delete_reward_tier(self) -> None:
        created = self.client.post(
            "/api/rewards/",
            json={"level": 4, "description": "Pizza"},
        ).json()
        self.assertEqual(self.client.delete(f"/api/rewards/{created['id']}").status_code, 204)
        self.assertEqual(self.client.get("/api/rewards/").json(), [])

    def test_delete_reward_tier_not_found(self) -> None:
        self.assertEqual(self.client.delete("/api/rewards/999999").status_code, 404)

    def _level_2_profile(self, name: str) -> dict:
        """A profile with 100 XP (level 2) via 10 attributed `in` movements."""
        profile = self.client.post("/api/profiles/", json={"name": name}).json()
        product = self._create_product(f"{name}-oats")
        for _ in range(10):
            self.client.post(
                "/api/transactions/",
                json={"product_id": product["id"], "profile_id": profile["id"], "type": "in"},
            )
        return self._get_profile(profile["id"])

    def test_redeeming_unlocked_reward_marks_it_for_that_profile(self) -> None:
        profile = self._level_2_profile("Reda")
        reward = self.client.post(
            "/api/rewards/",
            json={"level": 2, "description": "Ice cream"},
        ).json()

        res = self.client.post(
            f"/api/rewards/{reward['id']}/redemption?profile_id={profile['id']}",
        )
        self.assertEqual(res.status_code, 204)
        self.assertEqual(self._get_profile(profile["id"])["redeemed_rewards"], [reward["id"]])

    def test_redeeming_is_idempotent(self) -> None:
        profile = self._level_2_profile("Ida")
        reward = self.client.post(
            "/api/rewards/",
            json={"level": 2, "description": "Sticker"},
        ).json()

        url = f"/api/rewards/{reward['id']}/redemption?profile_id={profile['id']}"
        self.assertEqual(self.client.post(url).status_code, 204)
        self.assertEqual(self.client.post(url).status_code, 204)
        self.assertEqual(self._get_profile(profile["id"])["redeemed_rewards"], [reward["id"]])

    def test_redeeming_a_locked_reward_is_rejected(self) -> None:
        profile = self.client.post("/api/profiles/", json={"name": "Lo"}).json()  # level 1
        reward = self.client.post(
            "/api/rewards/",
            json={"level": 5, "description": "Movie night"},
        ).json()

        res = self.client.post(
            f"/api/rewards/{reward['id']}/redemption?profile_id={profile['id']}",
        )
        self.assertEqual(res.status_code, 409)
        self.assertEqual(self._get_profile(profile["id"])["redeemed_rewards"], [])

    def test_redeeming_unknown_reward_or_profile_is_404(self) -> None:
        profile = self._level_2_profile("Uma")
        reward = self.client.post(
            "/api/rewards/",
            json={"level": 2, "description": "Cookie"},
        ).json()

        self.assertEqual(
            self.client.post(f"/api/rewards/999999/redemption?profile_id={profile['id']}").status_code,
            404,
        )
        self.assertEqual(
            self.client.post(f"/api/rewards/{reward['id']}/redemption?profile_id=999999").status_code,
            404,
        )

    def test_unredeeming_removes_the_mark(self) -> None:
        profile = self._level_2_profile("Ned")
        reward = self.client.post(
            "/api/rewards/",
            json={"level": 2, "description": "Extra screen time"},
        ).json()
        url = f"/api/rewards/{reward['id']}/redemption?profile_id={profile['id']}"
        self.client.post(url)

        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self._get_profile(profile["id"])["redeemed_rewards"], [])
        # Idempotent: un-redeeming again is a no-op, still 204.
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_deleting_a_reward_tier_cascades_its_redemptions(self) -> None:
        profile = self._level_2_profile("Cas")
        reward = self.client.post(
            "/api/rewards/",
            json={"level": 2, "description": "Late bedtime"},
        ).json()
        self.client.post(f"/api/rewards/{reward['id']}/redemption?profile_id={profile['id']}")

        # FK ON DELETE CASCADE must clear the redemption, not raise on the FK.
        self.assertEqual(self.client.delete(f"/api/rewards/{reward['id']}").status_code, 204)
        self.assertEqual(self._get_profile(profile["id"])["redeemed_rewards"], [])

    def _get_profile(self, profile_id: int) -> dict:
        return next(
            p
            for p in self.client.get("/api/profiles/?include_archived=true").json()
            if p["id"] == profile_id
        )


if __name__ == "__main__":
    unittest.main()
