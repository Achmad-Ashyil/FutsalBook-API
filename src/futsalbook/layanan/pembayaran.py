"""Kasus penggunaan pencatatan dan verifikasi pembayaran."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from futsalbook.inti.enums import StatusPembayaran, StatusPemesanan
from futsalbook.model.pembayaran import Pembayaran
from futsalbook.model.pengguna import Pengguna
from futsalbook.repositori.pembayaran import RepositoriPembayaran
from futsalbook.repositori.pemesanan import RepositoriPemesanan
from futsalbook.skema.pembayaran import PembayaranBuat


def buat_pembayaran(db: Session, data: PembayaranBuat) -> Pembayaran:
    """Membuat pembayaran selama pemesanan masih menunggu pembayaran."""
    pemesanan = RepositoriPemesanan(db).berdasarkan_id(data.pemesanan_id)
    if pemesanan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PEMESANAN_TIDAK_DITEMUKAN", "message": "Pemesanan tidak ditemukan."},
        )
    if pemesanan.status != StatusPemesanan.MENUNGGU_PEMBAYARAN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PEMESANAN_TIDAK_MENUNGGU", "message": "Pemesanan tidak sedang menunggu pembayaran."},
        )

    repositori = RepositoriPembayaran(db)
    if repositori.memiliki_pembayaran_aktif(pemesanan.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PEMBAYARAN_SUDAH_ADA", "message": "Pemesanan sudah memiliki pembayaran yang aktif atau berhasil."},
        )
    pembayaran = Pembayaran(
        pemesanan_id=pemesanan.id,
        jumlah=pemesanan.total_biaya,
        metode=data.metode,
        status=StatusPembayaran.MENUNGGU,
    )
    return repositori.simpan(pembayaran)


def ubah_status_pembayaran(
    db: Session, pembayaran: Pembayaran, status_baru: StatusPembayaran, pemeriksa: Pengguna
) -> Pembayaran:
    """Mencatat verifikasi staf; pembayaran berhasil mengonfirmasi pemesanan."""
    if pembayaran.status != StatusPembayaran.MENUNGGU:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PEMBAYARAN_SUDAH_FINAL", "message": "Status pembayaran sudah final dan tidak dapat diubah."},
        )

    pemesanan = RepositoriPemesanan(db).berdasarkan_id(pembayaran.pemesanan_id)
    if status_baru == StatusPembayaran.BERHASIL:
        if pemesanan is None or pemesanan.status != StatusPemesanan.MENUNGGU_PEMBAYARAN:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "PEMESANAN_TIDAK_MENUNGGU", "message": "Pemesanan sudah tidak menunggu pembayaran."},
            )
        pemesanan.status = StatusPemesanan.DIKONFIRMASI

    pembayaran.status = status_baru
    pembayaran.diverifikasi_oleh_id = pemeriksa.id
    pembayaran.diverifikasi_pada = datetime.now(timezone.utc)
    db.commit()
    db.refresh(pembayaran)
    return pembayaran
