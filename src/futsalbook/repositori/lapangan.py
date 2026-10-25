"""Operasi persistensi untuk entitas lapangan."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from futsalbook.inti.enums import JenisLapangan
from futsalbook.model.lapangan import Lapangan


class RepositoriLapangan:
    """Menyediakan query dan penyimpanan data lapangan."""

    def __init__(self, db: Session):
        self.db = db

    def berdasarkan_id(self, lapangan_id: int) -> Lapangan | None:
        return self.db.get(Lapangan, lapangan_id)

    def daftar(
        self,
        batas: int,
        offset: int,
        jenis: JenisLapangan | None = None,
        aktif: bool | None = None,
        hanya_aktif: bool = False,
    ) -> list[Lapangan]:
        pernyataan = select(Lapangan)
        if hanya_aktif:
            pernyataan = pernyataan.where(Lapangan.aktif.is_(True))
        elif aktif is not None:
            pernyataan = pernyataan.where(Lapangan.aktif.is_(aktif))
        if jenis is not None:
            pernyataan = pernyataan.where(Lapangan.jenis == jenis)
        return list(self.db.scalars(pernyataan.order_by(Lapangan.id).offset(offset).limit(batas)).all())

    def simpan(self, lapangan: Lapangan) -> Lapangan:
        self.db.add(lapangan)
        self.db.commit()
        self.db.refresh(lapangan)
        return lapangan
