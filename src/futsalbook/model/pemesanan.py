"""Model transaksi pemesanan lapangan."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from futsalbook.inti.database import BasisModel
from futsalbook.inti.enums import StatusPemesanan

if TYPE_CHECKING:
    from futsalbook.model.lapangan import Lapangan
    from futsalbook.model.pembayaran import Pembayaran
    from futsalbook.model.pengguna import Pengguna


class Pemesanan(BasisModel):
    __tablename__ = "pemesanan"
    __table_args__ = (
        CheckConstraint("selesai > mulai", name="ck_pemesanan_jam_valid"),
        CheckConstraint("total_biaya > 0", name="ck_pemesanan_biaya_positif"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pengguna_id: Mapped[int] = mapped_column(ForeignKey("pengguna.id", ondelete="RESTRICT"), index=True)
    lapangan_id: Mapped[int] = mapped_column(ForeignKey("lapangan.id", ondelete="RESTRICT"), index=True)
    mulai: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    selesai: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[StatusPemesanan] = mapped_column(
        Enum(StatusPemesanan, native_enum=False, create_constraint=True, name="ck_pemesanan_status", values_callable=lambda cls: [item.value for item in cls]),
        nullable=False,
        default=StatusPemesanan.MENUNGGU_PEMBAYARAN,
    )
    total_biaya: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    dibuat_pada: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pengguna: Mapped["Pengguna"] = relationship(back_populates="pemesanan")
    lapangan: Mapped["Lapangan"] = relationship(back_populates="pemesanan")
    pembayaran: Mapped[list["Pembayaran"]] = relationship(back_populates="pemesanan")
