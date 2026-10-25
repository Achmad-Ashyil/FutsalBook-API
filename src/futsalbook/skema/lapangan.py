"""Kontrak data lapangan."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from futsalbook.inti.enums import JenisLapangan


class LapanganBuat(BaseModel):
    nama: str = Field(min_length=2, max_length=100, examples=["Lapangan A"])
    lokasi: str = Field(min_length=3, max_length=200, examples=["Jl. Pendidikan No. 10"])
    jenis: JenisLapangan
    tarif_per_jam: Decimal = Field(gt=0, max_digits=12, decimal_places=2, examples=[150000])


class LapanganUbah(BaseModel):
    nama: str | None = Field(default=None, min_length=2, max_length=100)
    lokasi: str | None = Field(default=None, min_length=3, max_length=200)
    jenis: JenisLapangan | None = None
    tarif_per_jam: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    aktif: bool | None = None

    @model_validator(mode="after")
    def validasi_bidang_perubahan(self):
        if not self.model_fields_set:
            raise ValueError("Minimal satu bidang harus dikirim untuk memperbarui lapangan.")
        if any(getattr(self, nama) is None for nama in self.model_fields_set):
            raise ValueError("Bidang yang dikirim tidak boleh bernilai null.")
        return self


class LapanganBaca(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str
    lokasi: str
    jenis: JenisLapangan
    tarif_per_jam: Decimal
    aktif: bool
    dibuat_pada: datetime
