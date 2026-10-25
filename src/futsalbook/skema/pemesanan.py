"""Kontrak data pemesanan lapangan."""

from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from futsalbook.inti.enums import StatusPemesanan


class PemesananBuat(BaseModel):
    lapangan_id: int = Field(gt=0)
    mulai: datetime
    selesai: datetime

    @model_validator(mode="after")
    def validasi_waktu(self):
        if self.mulai.tzinfo is None or self.mulai.utcoffset() is None:
            raise ValueError("Waktu mulai harus menyertakan zona waktu, misalnya +08:00 atau Z.")
        if self.selesai.tzinfo is None or self.selesai.utcoffset() is None:
            raise ValueError("Waktu selesai harus menyertakan zona waktu, misalnya +08:00 atau Z.")
        if self.mulai <= datetime.now(timezone.utc):
            raise ValueError("Waktu mulai harus berada di masa depan.")
        if self.selesai <= self.mulai:
            raise ValueError("Waktu selesai harus setelah waktu mulai.")
        durasi_detik = (self.selesai - self.mulai).total_seconds()
        if durasi_detik % 3600 != 0:
            raise ValueError("Pemesanan harus berdurasi kelipatan satu jam penuh.")
        return self


class PemesananStatusUbah(BaseModel):
    status: StatusPemesanan


class PemesananBaca(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pengguna_id: int
    lapangan_id: int
    mulai: datetime
    selesai: datetime
    status: StatusPemesanan
    total_biaya: Decimal
    dibuat_pada: datetime
