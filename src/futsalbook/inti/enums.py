"""Enumerasi domain yang digunakan API dan basis data."""

from enum import StrEnum


class PeranPengguna(StrEnum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    CUSTOMER = "CUSTOMER"


class JenisLapangan(StrEnum):
    SINTETIS = "SINTETIS"
    VINYL = "VINYL"
    SEMEN = "SEMEN"


class StatusPemesanan(StrEnum):
    MENUNGGU_PEMBAYARAN = "MENUNGGU_PEMBAYARAN"
    DIKONFIRMASI = "DIKONFIRMASI"
    DIBATALKAN = "DIBATALKAN"
    SELESAI = "SELESAI"


class MetodePembayaran(StrEnum):
    TRANSFER_BANK = "TRANSFER_BANK"
    TUNAI = "TUNAI"
    QRIS = "QRIS"


class StatusPembayaran(StrEnum):
    MENUNGGU = "MENUNGGU"
    BERHASIL = "BERHASIL"
    GAGAL = "GAGAL"
