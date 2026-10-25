"""Pengaturan aplikasi dari environment dan berkas .env."""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Pengaturan(BaseSettings):
    nama_aplikasi: str = Field(default="FutsalBook API", validation_alias=AliasChoices("APP_NAME", "NAMA_APLIKASI"))
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://futsalbook:futsalbook@localhost:5432/futsalbook"
    api_versi: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def dapatkan_pengaturan() -> Pengaturan:
    """Membaca pengaturan satu kali per proses."""
    return Pengaturan()
