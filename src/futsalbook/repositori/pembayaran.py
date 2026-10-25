"""Operasi persistensi untuk entitas pembayaran."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from futsalbook.inti.enums import StatusPembayaran
from futsalbook.model.pembayaran import Pembayaran
from futsalbook.model.pemesanan import Pemesanan


class RepositoriPembayaran:
    """Menangani query pembayaran dan mencari pembayaran aktif."""

    def __init__(self, db: Session):
        self.db = db

    def berdasarkan_id(self, pembayaran_id: int) -> Pembayaran | None:
        return self.db.get(Pembayaran, pembayaran_id)

    def daftar(
        self,
        batas: int,
        offset: int,
        pengguna_id: int | None = None,
        status: StatusPembayaran | None = None,
    ) -> list[Pembayaran]:
        pernyataan = select(Pembayaran).join(Pemesanan, Pembayaran.pemesanan_id == Pemesanan.id)
        if pengguna_id is not None:
            pernyataan = pernyataan.where(Pemesanan.pengguna_id == pengguna_id)
        if status is not None:
            pernyataan = pernyataan.where(Pembayaran.status == status)
        return list(self.db.scalars(pernyataan.order_by(Pembayaran.id.desc()).offset(offset).limit(batas)).all())

    def memiliki_pembayaran_aktif(self, pemesanan_id: int) -> bool:
        pembayaran_id = self.db.scalar(
            select(Pembayaran.id).where(
                Pembayaran.pemesanan_id == pemesanan_id,
                Pembayaran.status.in_([StatusPembayaran.MENUNGGU, StatusPembayaran.BERHASIL]),
            ).limit(1)
        )
        return pembayaran_id is not None

    def simpan(self, pembayaran: Pembayaran) -> Pembayaran:
        self.db.add(pembayaran)
        self.db.commit()
        self.db.refresh(pembayaran)
        return pembayaran
