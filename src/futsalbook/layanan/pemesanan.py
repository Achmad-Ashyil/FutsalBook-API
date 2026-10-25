"""Kasus penggunaan pemesanan dan aturan benturan jadwal."""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from futsalbook.inti.enums import StatusPemesanan
from futsalbook.model.pemesanan import Pemesanan
from futsalbook.model.pengguna import Pengguna
from futsalbook.repositori.lapangan import RepositoriLapangan
from futsalbook.repositori.pemesanan import RepositoriPemesanan
from futsalbook.skema.pemesanan import PemesananBuat


def buat_pemesanan(db: Session, pengguna: Pengguna, data: PemesananBuat) -> Pemesanan:
    """Memvalidasi lapangan, memeriksa benturan, lalu menyimpan pemesanan."""
    lapangan = RepositoriLapangan(db).berdasarkan_id(data.lapangan_id)
    if lapangan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LAPANGAN_TIDAK_DITEMUKAN", "message": "Lapangan tidak ditemukan."},
        )
    if not lapangan.aktif:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "LAPANGAN_NONAKTIF", "message": "Lapangan sedang tidak tersedia untuk dipesan."},
        )

    repositori = RepositoriPemesanan(db)
    if repositori.ada_benturan(data.lapangan_id, data.mulai, data.selesai):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "JADWAL_BENTROK", "message": "Lapangan sudah dipesan pada rentang waktu tersebut."},
        )

    jam = Decimal(int((data.selesai - data.mulai).total_seconds() // 3600))
    pemesanan = Pemesanan(
        pengguna_id=pengguna.id,
        lapangan_id=lapangan.id,
        mulai=data.mulai,
        selesai=data.selesai,
        status=StatusPemesanan.MENUNGGU_PEMBAYARAN,
        total_biaya=lapangan.tarif_per_jam * jam,
    )
    return repositori.simpan(pemesanan)


def ubah_status_pemesanan(
    db: Session, pemesanan: Pemesanan, status_baru: StatusPemesanan
) -> Pemesanan:
    """Menerapkan transisi status yang diizinkan staf/admin."""
    if status_baru == StatusPemesanan.DIKONFIRMASI:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "KONFIRMASI_MELALUI_PEMBAYARAN",
                "message": "Pemesanan dikonfirmasi otomatis setelah pembayaran berhasil diverifikasi.",
            },
        )
    transisi_diizinkan = {
        StatusPemesanan.MENUNGGU_PEMBAYARAN: {StatusPemesanan.DIBATALKAN},
        StatusPemesanan.DIKONFIRMASI: {StatusPemesanan.SELESAI},
        StatusPemesanan.DIBATALKAN: set(),
        StatusPemesanan.SELESAI: set(),
    }
    if status_baru not in transisi_diizinkan[pemesanan.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "TRANSISI_STATUS_TIDAK_VALID",
                "message": f"Status tidak dapat diubah dari {pemesanan.status.value} ke {status_baru.value}.",
            },
        )
    pemesanan.status = status_baru
    db.commit()
    db.refresh(pemesanan)
    return pemesanan


def batalkan_pemesanan(db: Session, pemesanan: Pemesanan) -> None:
    """Membatalkan pemesanan yang belum dibayar; baris tetap disimpan untuk audit."""
    if pemesanan.status != StatusPemesanan.MENUNGGU_PEMBAYARAN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PEMESANAN_TIDAK_DAPAT_DIBATALKAN",
                "message": "Hanya pemesanan yang menunggu pembayaran yang dapat dibatalkan melalui operasi ini.",
            },
        )
    pemesanan.status = StatusPemesanan.DIBATALKAN
    db.commit()
