"""Runtime configuration; secret files are never logged or embedded in setup."""

from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / ".local/runtime.env", override=False)


class Settings:
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://allexport@127.0.0.1:15432/allexport"
    )
    if os.environ.get("DATABASE_PASSWORD_FILE"):
        from sqlalchemy.engine import make_url

        database_url = (
            make_url(database_url)
            .set(
                password=Path(os.environ["DATABASE_PASSWORD_FILE"]).read_text().strip()
            )
            .render_as_string(hide_password=False)
        )
    mode = os.environ.get("APP_MODE", "normal")
    storage = Path(os.environ.get("STORAGE_PATH", str(ROOT / ".local/files")))
    max_upload_bytes = 10 * 1024 * 1024
    session_hours = 8

    @property
    def demo(self):
        return self.mode == "demo"


settings = Settings()
