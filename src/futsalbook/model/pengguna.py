"""Model akun pengguna FutsalBook."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from futsalbook.inti.database import BasisModel
from futsalbook.inti.enums import PeranPengguna

if TYPE_CHECKING:
    from futsalbook.model.pemesanan import Pemesanan


class Pengguna(BasisModel):
    __tablename__ = "pengguna"

    id: Mapped[int] = mapped_column(primary_key=True)
    nama: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    peran: Mapped[PeranPengguna] = mapped_column(
        Enum(PeranPengguna, native_enum=False, create_constraint=True, name="ck_pengguna_peran", values_callable=lambda cls: [item.value for item in cls]),
        nullable=False,
        default=PeranPengguna.CUSTOMER,
    )
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dibuat_pada: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pemesanan: Mapped[list["Pemesanan"]] = relationship(back_populates="pengguna")
