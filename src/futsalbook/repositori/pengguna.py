"""Operasi persistensi untuk entitas pengguna."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from futsalbook.model.pengguna import Pengguna


class RepositoriPengguna:
    """Membungkus query pengguna supaya router tidak mengelola SQL langsung."""

    def __init__(self, db: Session):
        self.db = db

    def berdasarkan_id(self, pengguna_id: int) -> Pengguna | None:
        return self.db.get(Pengguna, pengguna_id)

    def berdasarkan_email(self, email: str) -> Pengguna | None:
        return self.db.scalar(select(Pengguna).where(Pengguna.email == email))

    def berdasarkan_hash_kunci(self, api_key_hash: str) -> Pengguna | None:
        return self.db.scalar(select(Pengguna).where(Pengguna.api_key_hash == api_key_hash))

    def daftar(self, batas: int, offset: int) -> list[Pengguna]:
        return list(self.db.scalars(select(Pengguna).order_by(Pengguna.id).offset(offset).limit(batas)).all())

    def simpan(self, pengguna: Pengguna) -> Pengguna:
        self.db.add(pengguna)
        self.db.commit()
        self.db.refresh(pengguna)
        return pengguna
