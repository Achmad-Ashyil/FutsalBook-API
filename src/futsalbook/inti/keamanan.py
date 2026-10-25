"""Fungsi keamanan untuk API key dan otorisasi peran."""

import hashlib
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from futsalbook.inti.database import dapatkan_db
from futsalbook.inti.enums import PeranPengguna
from futsalbook.model.pengguna import Pengguna
from futsalbook.repositori.pengguna import RepositoriPengguna

_kepala_kunci_api = APIKeyHeader(name="X-API-Key", auto_error=False, description="API key pengguna FutsalBook.")


def buat_kunci_api() -> str:
    """Membuat API key berentropi tinggi; nilai asli hanya ditampilkan sekali."""
    return secrets.token_urlsafe(32)


def hash_kunci_api(kunci: str) -> str:
    """Menghasilkan hash SHA-256 dari API key untuk penyimpanan."""
    return hashlib.sha256(kunci.encode("utf-8")).hexdigest()


def autentikasi_pengguna(
    x_api_key: str | None = Depends(_kepala_kunci_api),
    db: Session = Depends(dapatkan_db),
) -> Pengguna:
    """Memvalidasi API key dan mengembalikan pengguna aktif."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "API_KEY_DIBUTUHKAN", "message": "Header X-API-Key wajib disertakan."},
            headers={"WWW-Authenticate": "APIKey"},
        )
    pengguna = RepositoriPengguna(db).berdasarkan_hash_kunci(hash_kunci_api(x_api_key))
    if pengguna is None or not pengguna.aktif:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "API_KEY_TIDAK_VALID", "message": "API key tidak valid atau pengguna nonaktif."},
            headers={"WWW-Authenticate": "APIKey"},
        )
    return pengguna


def butuh_peran(*peran_diizinkan: PeranPengguna):
    """Membuat dependency yang menolak pengguna tanpa peran yang sesuai."""

    def periksa_peran(pengguna: Pengguna = Depends(autentikasi_pengguna)) -> Pengguna:
        if pengguna.peran not in peran_diizinkan:
            daftar = ", ".join(item.value for item in peran_diizinkan)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "AKSES_DITOLAK",
                    "message": f"Peran {pengguna.peran.value} tidak diizinkan; peran yang diperlukan: {daftar}.",
                },
            )
        return pengguna

    return periksa_peran
