"""Endpoint pencatatan pembayaran dan verifikasinya."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from futsalbook.inti.database import dapatkan_db
from futsalbook.inti.enums import PeranPengguna, StatusPembayaran
from futsalbook.inti.keamanan import autentikasi_pengguna, butuh_peran
from futsalbook.layanan.pembayaran import buat_pembayaran, ubah_status_pembayaran
from futsalbook.model.pengguna import Pengguna
from futsalbook.repositori.pembayaran import RepositoriPembayaran
from futsalbook.repositori.pemesanan import RepositoriPemesanan
from futsalbook.skema.pembayaran import PembayaranBaca, PembayaranBuat, PembayaranStatusUbah

router = APIRouter(prefix="/pembayaran", tags=["Pembayaran"])
SesiDB = Annotated[Session, Depends(dapatkan_db)]
PenggunaMasuk = Annotated[Pengguna, Depends(autentikasi_pengguna)]


def _pembayaran_tidak_ditemukan() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "PEMBAYARAN_TIDAK_DITEMUKAN", "message": "Pembayaran tidak ditemukan."},
    )


@router.post("", response_model=PembayaranBaca, status_code=status.HTTP_201_CREATED, summary="Buat pembayaran")
def mulai_pembayaran(data: PembayaranBuat, db: SesiDB, pengguna: PenggunaMasuk):
    """Membuat catatan pembayaran untuk pemesanan milik pengguna atau yang dikelola staf."""
    pemesanan = RepositoriPemesanan(db).berdasarkan_id(data.pemesanan_id)
    if pemesanan is not None and pengguna.peran == PeranPengguna.CUSTOMER:
        if pemesanan.pengguna_id != pengguna.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "AKSES_DITOLAK", "message": "Anda hanya dapat membayar pemesanan milik sendiri."},
            )
    if pengguna.peran == PeranPengguna.CUSTOMER and pemesanan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PEMESANAN_TIDAK_DITEMUKAN", "message": "Pemesanan tidak ditemukan."},
        )
    return buat_pembayaran(db, data)


@router.get("", response_model=list[PembayaranBaca], summary="Daftar pembayaran")
def daftar_pembayaran(
    db: SesiDB,
    pengguna: PenggunaMasuk,
    status_pembayaran: StatusPembayaran | None = Query(default=None, alias="status"),
    batas: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Pelanggan hanya melihat pembayaran miliknya; staf/admin dapat melihat semua."""
    pengguna_id = pengguna.id if pengguna.peran == PeranPengguna.CUSTOMER else None
    return RepositoriPembayaran(db).daftar(
        batas=batas, offset=offset, pengguna_id=pengguna_id, status=status_pembayaran
    )


@router.get("/{pembayaran_id}", response_model=PembayaranBaca, summary="Detail pembayaran")
def detail_pembayaran(pembayaran_id: int, db: SesiDB, pengguna: PenggunaMasuk):
    """Melihat pembayaran dengan validasi kepemilikan."""
    repositori = RepositoriPembayaran(db)
    pembayaran = repositori.berdasarkan_id(pembayaran_id)
    if pembayaran is None:
        raise _pembayaran_tidak_ditemukan()
    pemesanan = RepositoriPemesanan(db).berdasarkan_id(pembayaran.pemesanan_id)
    if pengguna.peran == PeranPengguna.CUSTOMER and pemesanan.pengguna_id != pengguna.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AKSES_DITOLAK", "message": "Anda hanya dapat melihat pembayaran milik sendiri."},
        )
    return pembayaran


@router.patch(
    "/{pembayaran_id}/status",
    response_model=PembayaranBaca,
    summary="Verifikasi pembayaran",
    dependencies=[Depends(butuh_peran(PeranPengguna.ADMIN, PeranPengguna.STAFF))],
)
def verifikasi_pembayaran(
    pembayaran_id: int,
    data: PembayaranStatusUbah,
    db: SesiDB,
    pemeriksa: Pengguna = Depends(autentikasi_pengguna),
):
    """Staf/admin mencatat hasil verifikasi; pembayaran berhasil mengonfirmasi pesanan."""
    pembayaran = RepositoriPembayaran(db).berdasarkan_id(pembayaran_id)
    if pembayaran is None:
        raise _pembayaran_tidak_ditemukan()
    return ubah_status_pembayaran(db, pembayaran, data.status, pemeriksa)
