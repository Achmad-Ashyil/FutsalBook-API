"""Kontrak data pengguna dan penerbitan API key."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from futsalbook.inti.enums import PeranPengguna


class PenggunaBuat(BaseModel):
    nama: str = Field(min_length=2, max_length=100, examples=["Pengguna FutsalBook"])
    email: EmailStr
    peran: PeranPengguna = PeranPengguna.CUSTOMER


class PenggunaBaca(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str
    email: EmailStr
    peran: PeranPengguna
    aktif: bool
    dibuat_pada: datetime


class PenggunaDibuat(PenggunaBaca):
    """Respons satu kali yang memuat API key baru."""

    api_key: str


class PenggunaStatusUbah(BaseModel):
    aktif: bool
