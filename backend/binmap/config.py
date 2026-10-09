from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_prefix="BINMAP_", extra="ignore"
    )
    database_url: str = f"sqlite:///{ROOT / 'data' / 'binmap.db'}"
    survey_key: str = ""
    review_key: str = ""
    data_dir: Path = ROOT / "data"
    frontend_dir: Path = ROOT / "frontend" / "dist"
    stale_days: int = 30
