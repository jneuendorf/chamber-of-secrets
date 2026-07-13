from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/inventory.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    ean_api_base_url: str = "https://world.openfoodfacts.org/api/v2"

    # Contribute-back (WL-4.6). Defaults target the OFF *staging* server so dev
    # and tests never pollute production. Staging gates writes behind HTTP basic
    # auth off/off; product writes use an OFF account (off/off on staging).
    # Prod deploy overrides all four via APP_OFF_* env, and sets
    # APP_OFF_SITE_AUTH= (empty) to drop the staging gate.
    off_write_base_url: str = "https://world.openfoodfacts.net"
    off_site_auth: str = "off:off"
    off_user_id: str = "off"
    off_password: str = "off"
    off_user_agent: str = "ChamberOfSecrets/1.0 (household grocery companion)"
    # Front-image upload is fully wired but dormant. Flip to True (or
    # APP_OFF_CONTRIBUTE_IMAGES=true) once the manual scan flow captures a real
    # photo; no code change needed then.
    off_contribute_images: bool = False

    model_config = {"env_file": ".env", "env_prefix": "APP_"}


settings = Settings()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

PRODUCT_IMAGE_DIR = UPLOAD_DIR / "products"
PRODUCT_IMAGE_DIR.mkdir(exist_ok=True)
