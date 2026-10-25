"""Model lapangan futsal."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from futsalbook.inti.database import BasisModel
from futsalbook.inti.enums import JenisLapangan

if TYPE_CHECKING:
    from futsalbook.model.pemesanan import Pemesanan


class Lapangan(BasisModel):
    __tablename__ = "lapangan"
    __table_args__ = (CheckConstraint("tarif_per_jam > 0", name="ck_lapangan_tarif_positif"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nama: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    lokasi: Mapped[str] = mapped_column(String(200), nullable=False)
    jenis: Mapped[JenisLapangan] = mapped_column(
        Enum(JenisLapangan, native_enum=False, create_constraint=True, name="ck_lapangan_jenis", values_callable=lambda cls: [item.value for item in cls]),
        nullable=False,
    )
    tarif_per_jam: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    dibuat_pada: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pemesanan: Mapped[list["Pemesanan"]] = relationship(back_populates="lapangan")
