"""Operasi persistensi untuk entitas pemesanan."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from futsalbook.inti.enums import StatusPemesanan
from futsalbook.model.pemesanan import Pemesanan


class RepositoriPemesanan:
    """Menangani query pemesanan dan pencarian benturan waktu."""

    def __init__(self, db: Session):
        self.db = db

    def berdasarkan_id(self, pemesanan_id: int) -> Pemesanan | None:
        return self.db.get(Pemesanan, pemesanan_id)

    def daftar(
        self,
        batas: int,
        offset: int,
        pengguna_id: int | None = None,
        status: StatusPemesanan | None = None,
    ) -> list[Pemesanan]:
        pernyataan = select(Pemesanan)
        if pengguna_id is not None:
            pernyataan = pernyataan.where(Pemesanan.pengguna_id == pengguna_id)
        if status is not None:
            pernyataan = pernyataan.where(Pemesanan.status == status)
        return list(self.db.scalars(pernyataan.order_by(Pemesanan.mulai.desc()).offset(offset).limit(batas)).all())

    def ada_benturan(self, lapangan_id: int, mulai: datetime, selesai: datetime) -> bool:
        benturan = self.db.scalar(
            select(Pemesanan.id).where(
                Pemesanan.lapangan_id == lapangan_id,
                Pemesanan.status != StatusPemesanan.DIBATALKAN,
                Pemesanan.mulai < selesai,
                Pemesanan.selesai > mulai,
            ).limit(1)
        )
        return benturan is not None

    def simpan(self, pemesanan: Pemesanan) -> Pemesanan:
        self.db.add(pemesanan)
        self.db.commit()
        self.db.refresh(pemesanan)
        return pemesanan
