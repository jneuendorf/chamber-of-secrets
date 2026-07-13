import httpx

from app.config import settings


def _off_client() -> httpx.AsyncClient:
    """Configured client for OFF writes: descriptive User-Agent + staging gate.

    Staging gates writes behind HTTP basic auth (off/off); prod sets
    off_site_auth="" to drop it.
    """
    auth: httpx.BasicAuth | None = None
    if settings.off_site_auth:
        user, _, password = settings.off_site_auth.partition(":")
        auth = httpx.BasicAuth(user, password)
    return httpx.AsyncClient(
        timeout=15,
        headers={"User-Agent": settings.off_user_agent},
        auth=auth,
    )


async def contribute_product(
    code: str,
    name: str,
    brand: str | None = None,
    category: str | None = None,
    lc: str = "en",
) -> bool:
    """Submit a barcode-keyed product to Open Food Facts (WL-4.6).

    Writes name/brands/categories via the jqm2 endpoint using a server-side OFF
    account. Returns True on OFF status==1.

    ponytail: jqm2 (flat form fields + inline user_id/password) over
    PATCH /api/v3/product/{barcode} — v3 needs session/Bearer auth and a nested
    JSON document. Switch to v3 if we ever need field-level partial updates or
    its richer taxonomy handling.
    """
    data = {
        "code": code,
        "user_id": settings.off_user_id,
        "password": settings.off_password,
        "product_name": name,
        "lc": lc,
    }
    if brand:
        data["brands"] = brand
    if category:
        data["categories"] = category

    async with _off_client() as client:
        response = await client.post(
            f"{settings.off_write_base_url}/cgi/product_jqm2.pl",
            data=data,
        )
    return response.status_code == 200 and response.json().get("status") == 1


async def contribute_image(
    code: str,
    image_bytes: bytes,
    filename: str,
    content_type: str,
    lc: str = "en",
) -> bool:
    """Upload a front image for a product to Open Food Facts (WL-4.6).

    Fully wired but dormant: the caller only reaches it when
    ``settings.off_contribute_images`` is on, which stays off until the manual
    scan flow captures a real photo. ponytail: verify the "status ok" contract
    against staging when the flag is first flipped.
    """
    field = f"front_{lc}"
    data = {
        "code": code,
        "imagefield": field,
        "user_id": settings.off_user_id,
        "password": settings.off_password,
    }
    files = {f"imgupload_{field}": (filename, image_bytes, content_type)}

    async with _off_client() as client:
        response = await client.post(
            f"{settings.off_write_base_url}/cgi/product_image_upload.pl",
            data=data,
            files=files,
        )
    return response.status_code == 200 and response.json().get("status") == "status ok"
