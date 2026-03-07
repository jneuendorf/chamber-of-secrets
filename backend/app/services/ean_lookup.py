import httpx

from app.config import settings
from app.schemas import EANLookupResult


async def lookup_ean(ean: str) -> EANLookupResult | None:
    """Look up product info by EAN using Open Food Facts API."""
    url = f"{settings.ean_api_base_url}/product/{ean}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            url, params={"fields": "product_name,brands,image_url,categories"}
        )

    if response.status_code != 200:
        return None

    data = response.json()
    if data.get("status") != 1:
        return None

    product = data.get("product", {})
    return EANLookupResult(
        ean=ean,
        name=product.get("product_name"),
        brand=product.get("brands"),
        image_url=product.get("image_url"),
        category=product.get("categories"),
    )
