"""Endpoint akun pengguna dan penerbitan API key."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from futsalbook.inti.database import dapatkan_db
from futsalbook.inti.enums import PeranPengguna
from futsalbook.inti.keamanan import (
    autentikasi_pengguna,
    buat_kunci_api,
    butuh_peran,
    hash_kunci_api,
)
from futsalbook.model.pengguna import Pengguna
from futsalbook.repositori.pengguna import RepositoriPengguna
from futsalbook.skema.pengguna import PenggunaBaca, PenggunaBuat, PenggunaDibuat, PenggunaStatusUbah

router = APIRouter(prefix="/pengguna", tags=["Pengguna"])
SesiDB = Annotated[Session, Depends(dapatkan_db)]
PenggunaMasuk = Annotated[Pengguna, Depends(autentikasi_pengguna)]


def _pengguna_tidak_ditemukan() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "PENGGUNA_TIDAK_DITEMUKAN", "message": "Pengguna tidak ditemukan."},
    )


def _respons_dengan_kunci(pengguna: Pengguna, api_key: str) -> PenggunaDibuat:
    return PenggunaDibuat(**PenggunaBaca.model_validate(pengguna).model_dump(), api_key=api_key)


@router.get("/me", response_model=PenggunaBaca, summary="Profil pengguna saat ini")
def profil_saya(pengguna: PenggunaMasuk):
    """Mengembalikan profil yang terikat pada API key saat ini."""
    return pengguna


@router.get(
    "",
    response_model=list[PenggunaBaca],
    summary="Daftar pengguna",
    dependencies=[Depends(butuh_peran(PeranPengguna.ADMIN))],
)
def daftar_pengguna(
    db: SesiDB,
    batas: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Melihat daftar pengguna tanpa menampilkan hash atau API key."""
    return RepositoriPengguna(db).daftar(batas=batas, offset=offset)


@router.post(
    "",
    response_model=PenggunaDibuat,
    status_code=status.HTTP_201_CREATED,
    summary="Buat pengguna dan API key",
    dependencies=[Depends(butuh_peran(PeranPengguna.ADMIN))],
)
def buat_pengguna(data: PenggunaBuat, db: SesiDB):
    """Membuat akun; API key mentah hanya dikembalikan sekali pada respons ini."""
    repositori = RepositoriPengguna(db)
    email = str(data.email).lower()
    if repositori.berdasarkan_email(email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_SUDAH_DIGUNAKAN", "message": "Email sudah terdaftar."},
        )
    api_key = buat_kunci_api()
    pengguna = Pengguna(
        nama=data.nama.strip(),
        email=email,
        peran=data.peran,
        api_key_hash=hash_kunci_api(api_key),
        aktif=True,
    )
    repositori.simpan(pengguna)
    return _respons_dengan_kunci(pengguna, api_key)


@router.patch(
    "/{pengguna_id}/status",
    response_model=PenggunaBaca,
    summary="Ubah status pengguna",
    dependencies=[Depends(butuh_peran(PeranPengguna.ADMIN))],
)
def ubah_status_pengguna(pengguna_id: int, data: PenggunaStatusUbah, db: SesiDB, pelaku: PenggunaMasuk):
    """Mengaktifkan atau menonaktifkan akun; admin tidak dapat menonaktifkan dirinya sendiri."""
    repositori = RepositoriPengguna(db)
    pengguna = repositori.berdasarkan_id(pengguna_id)
    if pengguna is None:
        raise _pengguna_tidak_ditemukan()
    if pengguna.id == pelaku.id and not data.aktif:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "TIDAK_DAPAT_NONAKTIFKAN_DIRI", "message": "Admin tidak dapat menonaktifkan akunnya sendiri."},
        )
    pengguna.aktif = data.aktif
    return repositori.simpan(pengguna)


@router.post(
    "/{pengguna_id}/rotasi-kunci",
    response_model=PenggunaDibuat,
    summary="Rotasi API key pengguna",
    dependencies=[Depends(butuh_peran(PeranPengguna.ADMIN))],
)
def rotasi_kunci(pengguna_id: int, db: SesiDB):
    """Menerbitkan API key baru sehingga kunci sebelumnya tidak lagi dapat digunakan."""
    repositori = RepositoriPengguna(db)
    pengguna = repositori.berdasarkan_id(pengguna_id)
    if pengguna is None:
        raise _pengguna_tidak_ditemukan()
    api_key = buat_kunci_api()
    pengguna.api_key_hash = hash_kunci_api(api_key)
    repositori.simpan(pengguna)
    return _respons_dengan_kunci(pengguna, api_key)
