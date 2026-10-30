from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SDRT_", env_file=ROOT / ".env", extra="ignore"
    )
    database_url: str
    csrf_secret: str
    environment: str = "development"
    secure_cookies: bool = True
    allowed_origins: list[str] = ["http://localhost:8000"]
    private_dir: Path = ROOT / ".private/uploads"
    seed_password: str = ""
    test_database_url: str = ""

    @field_validator("database_url")
    @classmethod
    def mysql_only(cls, value):
        if not value.startswith("mysql+pymysql://"):
            raise ValueError("MySQL with PyMySQL is required")
        return value

    @field_validator("csrf_secret")
    @classmethod
    def strong_secret(cls, value):
        if len(value) < 32 or value.startswith("REPLACE_"):
            raise ValueError("Set a random CSRF secret of at least 32 characters")
        return value


settings = Settings()
