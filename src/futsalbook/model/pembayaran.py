"""Model pencatatan pembayaran pemesanan."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from futsalbook.inti.database import BasisModel
from futsalbook.inti.enums import MetodePembayaran, StatusPembayaran

if TYPE_CHECKING:
    from futsalbook.model.pemesanan import Pemesanan


class Pembayaran(BasisModel):
    __tablename__ = "pembayaran"
    __table_args__ = (
        CheckConstraint("jumlah > 0", name="ck_pembayaran_jumlah_positif"),
        Index(
            "uq_pembayaran_aktif_per_pemesanan",
            "pemesanan_id",
            unique=True,
            postgresql_where=text("status IN ('MENUNGGU', 'BERHASIL')"),
            sqlite_where=text("status IN ('MENUNGGU', 'BERHASIL')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pemesanan_id: Mapped[int] = mapped_column(
        ForeignKey("pemesanan.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    jumlah: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    metode: Mapped[MetodePembayaran] = mapped_column(
        Enum(MetodePembayaran, native_enum=False, create_constraint=True, name="ck_pembayaran_metode", values_callable=lambda cls: [item.value for item in cls]),
        nullable=False,
    )
    status: Mapped[StatusPembayaran] = mapped_column(
        Enum(StatusPembayaran, native_enum=False, create_constraint=True, name="ck_pembayaran_status", values_callable=lambda cls: [item.value for item in cls]),
        nullable=False,
        default=StatusPembayaran.MENUNGGU,
    )
    diverifikasi_oleh_id: Mapped[int | None] = mapped_column(
        ForeignKey("pengguna.id", ondelete="RESTRICT"), nullable=True
    )
    dibuat_pada: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    diverifikasi_pada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pemesanan: Mapped["Pemesanan"] = relationship(back_populates="pembayaran")
