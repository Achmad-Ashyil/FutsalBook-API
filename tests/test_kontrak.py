"""Unit test untuk validasi kontrak Pydantic dan fungsi keamanan."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from futsalbook.inti.keamanan import hash_kunci_api
from futsalbook.skema.lapangan import LapanganBuat, LapanganUbah
from futsalbook.skema.pemesanan import PemesananBuat


def test_lapangan_menerima_kontrak_valid():
    lapangan = LapanganBuat(nama="Lapangan A", lokasi="Samata", jenis="SINTETIS", tarif_per_jam="150000.00")
    assert lapangan.tarif_per_jam == Decimal("150000.00")


def test_lapangan_menolak_tarif_nol():
    with pytest.raises(ValidationError):
        LapanganBuat(nama="Lapangan A", lokasi="Samata", jenis="SINTETIS", tarif_per_jam=0)


def test_lapangan_menolak_jenis_di_luar_kontrak():
    with pytest.raises(ValidationError):
        LapanganBuat(nama="Lapangan A", lokasi="Samata", jenis="RUMPUT", tarif_per_jam=150000)


def test_pembaruan_lapangan_menolak_objek_kosong():
    with pytest.raises(ValidationError):
        LapanganUbah()


def test_pembaruan_lapangan_menolak_null_eksplisit():
    with pytest.raises(ValidationError):
        LapanganUbah(nama=None)


def test_pemesanan_menolak_waktu_tanpa_zona_waktu():
    awal = datetime.now().replace(microsecond=0) + timedelta(days=3)
    with pytest.raises(ValidationError):
        PemesananBuat(lapangan_id=1, mulai=awal, selesai=awal + timedelta(hours=1))


def test_pemesanan_menolak_waktu_mulai_di_masa_lalu():
    awal = datetime.now(timezone.utc) - timedelta(days=1)
    with pytest.raises(ValidationError):
        PemesananBuat(lapangan_id=1, mulai=awal, selesai=awal + timedelta(hours=1))


def test_pemesanan_menolak_waktu_selesai_sebelum_mulai():
    awal = datetime.now(timezone.utc) + timedelta(days=3)
    with pytest.raises(ValidationError):
        PemesananBuat(lapangan_id=1, mulai=awal, selesai=awal - timedelta(hours=1))


def test_pemesanan_harus_kelipatan_satu_jam():
    awal = datetime.now(timezone.utc) + timedelta(days=3)
    with pytest.raises(ValidationError):
        PemesananBuat(lapangan_id=1, mulai=awal, selesai=awal + timedelta(minutes=90))


def test_pemesanan_valid_diterima():
    awal = datetime.now(timezone.utc) + timedelta(days=3)
    pemesanan = PemesananBuat(lapangan_id=2, mulai=awal, selesai=awal + timedelta(hours=2))
    assert pemesanan.lapangan_id == 2
    assert pemesanan.selesai - pemesanan.mulai == timedelta(hours=2)


def test_hash_api_key_deterministik_dan_tidak_sama_dengan_kunci_asli():
    kunci = "kunci-rahasia-contoh"
    hasil = hash_kunci_api(kunci)
    assert hasil == hash_kunci_api(kunci)
    assert hasil != kunci
    assert len(hasil) == 64
