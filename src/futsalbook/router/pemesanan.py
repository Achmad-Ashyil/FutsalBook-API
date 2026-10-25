"""Endpoint pemesanan dan transisi statusnya."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from futsalbook.inti.database import dapatkan_db
from futsalbook.inti.enums import PeranPengguna, StatusPemesanan
from futsalbook.inti.keamanan import autentikasi_pengguna, butuh_peran
from futsalbook.layanan.pemesanan import batalkan_pemesanan, buat_pemesanan, ubah_status_pemesanan
from futsalbook.model.pengguna import Pengguna
from futsalbook.repositori.pemesanan import RepositoriPemesanan
from futsalbook.skema.pemesanan import PemesananBaca, PemesananBuat, PemesananStatusUbah

router = APIRouter(prefix="/pemesanan", tags=["Pemesanan"])
SesiDB = Annotated[Session, Depends(dapatkan_db)]
PenggunaMasuk = Annotated[Pengguna, Depends(autentikasi_pengguna)]


def _pemesanan_tidak_ditemukan() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "PEMESANAN_TIDAK_DITEMUKAN", "message": "Pemesanan tidak ditemukan."},
    )


@router.post("", response_model=PemesananBaca, status_code=status.HTTP_201_CREATED, summary="Buat pemesanan")
def pesan_lapangan(
    data: PemesananBuat,
    db: SesiDB,
    pengguna: Pengguna = Depends(butuh_peran(PeranPengguna.CUSTOMER)),
):
    """Membuat pemesanan untuk pengguna CUSTOMER yang sedang terautentikasi."""
    return buat_pemesanan(db, pengguna, data)


@router.get("", response_model=list[PemesananBaca], summary="Daftar pemesanan")
def daftar_pemesanan(
    db: SesiDB,
    pengguna: PenggunaMasuk,
    status_pemesanan: StatusPemesanan | None = Query(default=None, alias="status"),
    batas: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Pelanggan hanya melihat pemesanannya; staf/admin melihat semua."""
    pengguna_id = pengguna.id if pengguna.peran == PeranPengguna.CUSTOMER else None
    return RepositoriPemesanan(db).daftar(
        batas=batas, offset=offset, pengguna_id=pengguna_id, status=status_pemesanan
    )


@router.get("/{pemesanan_id}", response_model=PemesananBaca, summary="Detail pemesanan")
def detail_pemesanan(pemesanan_id: int, db: SesiDB, pengguna: PenggunaMasuk):
    """Melihat detail pemesanan sesuai hak akses."""
    pemesanan = RepositoriPemesanan(db).berdasarkan_id(pemesanan_id)
    if pemesanan is None:
        raise _pemesanan_tidak_ditemukan()
    if pengguna.peran == PeranPengguna.CUSTOMER and pemesanan.pengguna_id != pengguna.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AKSES_DITOLAK", "message": "Anda hanya dapat melihat pemesanan milik sendiri."},
        )
    return pemesanan


@router.patch(
    "/{pemesanan_id}/status",
    response_model=PemesananBaca,
    summary="Ubah status pemesanan",
    dependencies=[Depends(butuh_peran(PeranPengguna.ADMIN, PeranPengguna.STAFF))],
)
def ubah_status(pemesanan_id: int, data: PemesananStatusUbah, db: SesiDB):
    """Mengubah status sesuai aturan transisi yang diperbolehkan."""
    pemesanan = RepositoriPemesanan(db).berdasarkan_id(pemesanan_id)
    if pemesanan is None:
        raise _pemesanan_tidak_ditemukan()
    return ubah_status_pemesanan(db, pemesanan, data.status)


@router.delete(
    "/{pemesanan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Batalkan pemesanan yang belum dibayar",
)
def batalkan(pemesanan_id: int, db: SesiDB, pengguna: PenggunaMasuk):
    """Membatalkan pemesanan yang masih menunggu pembayaran tanpa menghapus riwayat."""
    pemesanan = RepositoriPemesanan(db).berdasarkan_id(pemesanan_id)
    if pemesanan is None:
        raise _pemesanan_tidak_ditemukan()
    if pengguna.peran == PeranPengguna.CUSTOMER and pemesanan.pengguna_id != pengguna.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "AKSES_DITOLAK", "message": "Anda hanya dapat membatalkan pemesanan milik sendiri."},
        )
    batalkan_pemesanan(db, pemesanan)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
