"""Fixture bersama untuk menguji API dengan basis data terisolasi."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from futsalbook.inti.database import BasisModel, dapatkan_db
from futsalbook.inti.enums import PeranPengguna
from futsalbook.inti.keamanan import hash_kunci_api
from futsalbook.main import app
from futsalbook.model import Lapangan, Pembayaran, Pemesanan, Pengguna  # noqa: F401


@pytest.fixture
def sesi_factory() -> Generator[sessionmaker[Session], None, None]:
    """Menyediakan SQLite sementara yang dibagi antar-sesi selama satu tes."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    BasisModel.metadata.create_all(bind=engine)
    pembuat_sesi = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    yield pembuat_sesi
    BasisModel.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def client(sesi_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    """Menghubungkan TestClient ke basis data tes melalui dependency override."""

    def db_tes():
        db = sesi_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[dapatkan_db] = db_tes
    with TestClient(app) as klien:
        yield klien
    app.dependency_overrides.clear()


@pytest.fixture
def data_pengguna(sesi_factory: sessionmaker[Session]) -> dict:
    """Membuat admin, staf, dan dua pelanggan untuk skenario otorisasi."""
    data = {
        "admin": {"nama": "Admin Uji", "email": "admin@example.com", "peran": PeranPengguna.ADMIN, "key": "kunci-admin-tes-32-byte-aman"},
        "staff": {"nama": "Staf Uji", "email": "staff@example.com", "peran": PeranPengguna.STAFF, "key": "kunci-staf-tes-32-byte-aman"},
        "customer": {"nama": "Pelanggan Satu", "email": "satu@example.com", "peran": PeranPengguna.CUSTOMER, "key": "kunci-customer-satu-tes-aman"},
        "customer2": {"nama": "Pelanggan Dua", "email": "dua@example.com", "peran": PeranPengguna.CUSTOMER, "key": "kunci-customer-dua-tes-aman"},
    }
    with sesi_factory() as db:
        for identitas in data.values():
            pengguna = Pengguna(
                nama=identitas["nama"],
                email=identitas["email"],
                peran=identitas["peran"],
                api_key_hash=hash_kunci_api(identitas["key"]),
                aktif=True,
            )
            db.add(pengguna)
        db.commit()
        for nama in data:
            pengguna = db.query(Pengguna).filter_by(email=data[nama]["email"]).one()
            data[nama]["id"] = pengguna.id
    data["headers"] = {nama: {"X-API-Key": rincian["key"]} for nama, rincian in data.items() if nama != "headers"}
    return data
