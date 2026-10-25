"""Pembuatan engine dan sesi SQLAlchemy secara malas (lazy)."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from futsalbook.inti.konfigurasi import dapatkan_pengaturan


class BasisModel(DeclarativeBase):
    """Kelas dasar untuk seluruh model basis data."""


@lru_cache
def dapatkan_engine() -> Engine:
    """Membuat engine ketika koneksi pertama memang diperlukan."""
    url = dapatkan_pengaturan().database_url
    opsi: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        opsi["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **opsi)


def buat_sesi() -> Session:
    """Membuat satu sesi terikat ke engine aplikasi."""
    pembuat_sesi = sessionmaker(
        bind=dapatkan_engine(), autoflush=False, autocommit=False, expire_on_commit=False
    )
    return pembuat_sesi()


def dapatkan_db() -> Generator[Session, None, None]:
    """Menyediakan sesi basis data untuk satu permintaan."""
    db = buat_sesi()
    try:
        yield db
    finally:
        db.close()
