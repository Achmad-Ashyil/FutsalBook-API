"""Kontrak data pembayaran."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from futsalbook.inti.enums import MetodePembayaran, StatusPembayaran


class PembayaranBuat(BaseModel):
    pemesanan_id: int = Field(gt=0)
    metode: MetodePembayaran


class PembayaranStatusUbah(BaseModel):
    status: Literal[StatusPembayaran.BERHASIL, StatusPembayaran.GAGAL]


class PembayaranBaca(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pemesanan_id: int
    jumlah: Decimal
    metode: MetodePembayaran
    status: StatusPembayaran
    diverifikasi_oleh_id: int | None
    dibuat_pada: datetime
    diverifikasi_pada: datetime | None
