"""Endpoint REST untuk pengelolaan lapangan."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from futsalbook.inti.database import dapatkan_db
from futsalbook.inti.enums import JenisLapangan, PeranPengguna
from futsalbook.inti.keamanan import autentikasi_pengguna, butuh_peran
from futsalbook.model.lapangan import Lapangan
from futsalbook.model.pengguna import Pengguna
from futsalbook.repositori.lapangan import RepositoriLapangan
from futsalbook.skema.lapangan import LapanganBaca, LapanganBuat, LapanganUbah

router = APIRouter(prefix="/lapangan", tags=["Lapangan"])
SesiDB = Annotated[Session, Depends(dapatkan_db)]
PenggunaMasuk = Annotated[Pengguna, Depends(autentikasi_pengguna)]


def _lapangan_tidak_ditemukan() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "LAPANGAN_TIDAK_DITEMUKAN", "message": "Lapangan tidak ditemukan."},
    )


@router.get("", response_model=list[LapanganBaca], summary="Daftar lapangan")
def daftar_lapangan(
    db: SesiDB,
    pengguna: PenggunaMasuk,
    jenis: JenisLapangan | None = Query(default=None, description="Filter berdasarkan jenis lapangan."),
    aktif: bool | None = Query(default=None, description="Filter status aktif; pelanggan hanya melihat lapangan aktif."),
    batas: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Menampilkan lapangan dengan filter dan paginasi sederhana."""
    repositori = RepositoriLapangan(db)
    return repositori.daftar(
        batas=batas,
        offset=offset,
        jenis=jenis,
        aktif=aktif if pengguna.peran != PeranPengguna.CUSTOMER else None,
        hanya_aktif=pengguna.peran == PeranPengguna.CUSTOMER,
    )


@router.post(
    "",
    response_model=LapanganBaca,
    status_code=status.HTTP_201_CREATED,
    summary="Tambah lapangan",
    dependencies=[Depends(butuh_peran(PeranPengguna.ADMIN, PeranPengguna.STAFF))],
)
def tambah_lapangan(data: LapanganBuat, db: SesiDB):
    """Mendaftarkan lapangan baru; nama lapangan harus unik."""
    return RepositoriLapangan(db).simpan(Lapangan(**data.model_dump()))


@router.get("/{lapangan_id}", response_model=LapanganBaca, summary="Detail lapangan")
def detail_lapangan(lapangan_id: int, db: SesiDB, pengguna: PenggunaMasuk):
    """Mendapatkan satu lapangan berdasarkan ID."""
    lapangan = RepositoriLapangan(db).berdasarkan_id(lapangan_id)
    if lapangan is None or (pengguna.peran == PeranPengguna.CUSTOMER and not lapangan.aktif):
        raise _lapangan_tidak_ditemukan()
    return lapangan


@router.patch(
    "/{lapangan_id}",
    response_model=LapanganBaca,
    summary="Ubah lapangan",
    dependencies=[Depends(butuh_peran(PeranPengguna.ADMIN, PeranPengguna.STAFF))],
)
def ubah_lapangan(lapangan_id: int, data: LapanganUbah, db: SesiDB):
    """Mengubah data lapangan; penonaktifan dilakukan tanpa menghapus riwayat."""
    repositori = RepositoriLapangan(db)
    lapangan = repositori.berdasarkan_id(lapangan_id)
    if lapangan is None:
        raise _lapangan_tidak_ditemukan()
    for nama, nilai in data.model_dump(exclude_unset=True).items():
        setattr(lapangan, nama, nilai)
    return repositori.simpan(lapangan)


@router.delete(
    "/{lapangan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Nonaktifkan lapangan",
    dependencies=[Depends(butuh_peran(PeranPengguna.ADMIN))],
)
def nonaktifkan_lapangan(lapangan_id: int, db: SesiDB):
    """Menonaktifkan lapangan dengan lembut agar riwayat transaksi tetap utuh."""
    repositori = RepositoriLapangan(db)
    lapangan = repositori.berdasarkan_id(lapangan_id)
    if lapangan is None:
        raise _lapangan_tidak_ditemukan()
    lapangan.aktif = False
    repositori.simpan(lapangan)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
