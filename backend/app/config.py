from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/inventory.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    ean_api_base_url: str = "https://world.openfoodfacts.org/api/v2"

    model_config = {"env_file": ".env", "env_prefix": "APP_"}


settings = Settings()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

PRODUCT_IMAGE_DIR = UPLOAD_DIR / "products"
PRODUCT_IMAGE_DIR.mkdir(exist_ok=True)
