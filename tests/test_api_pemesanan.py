"""Pengujian integrasi pemesanan, validasi bisnis, dan kepemilikan."""

from datetime import datetime, timedelta, timezone


def waktu_mendatang():
    """Menghasilkan jam mulai beberapa hari ke depan pada batas jam penuh."""
    awal = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(days=3)
    return awal, awal + timedelta(hours=2)


def buat_lapangan(client, header, nama="Lapangan Pesan", tarif=100000):
    respons = client.post(
        "/api/v1/lapangan",
        headers=header,
        json={"nama": nama, "lokasi": "Samata, Gowa", "jenis": "VINYL", "tarif_per_jam": tarif},
    )
    assert respons.status_code == 201
    return respons.json()


def buat_pemesanan(client, header, lapangan_id, mulai=None, selesai=None):
    if mulai is None or selesai is None:
        mulai, selesai = waktu_mendatang()
    return client.post(
        "/api/v1/pemesanan",
        headers=header,
        json={"lapangan_id": lapangan_id, "mulai": mulai.isoformat(), "selesai": selesai.isoformat()},
    )


def test_pelanggan_dapat_memesan_dan_total_dihitung_dari_tarif(client, data_pengguna):
    lapangan = buat_lapangan(client, data_pengguna["headers"]["admin"], tarif=125000)
    mulai, selesai = waktu_mendatang()
    respons = buat_pemesanan(
        client, data_pengguna["headers"]["customer"], lapangan["id"], mulai, selesai
    )
    assert respons.status_code == 201
    assert respons.json()["status"] == "MENUNGGU_PEMBAYARAN"
    assert respons.json()["total_biaya"] == "250000.00"
    assert respons.json()["pengguna_id"] == data_pengguna["customer"]["id"]


def test_pengguna_staff_tidak_dapat_membuat_pemesanan_pelanggan(client, data_pengguna):
    lapangan = buat_lapangan(client, data_pengguna["headers"]["admin"])
    mulai, selesai = waktu_mendatang()
    respons = buat_pemesanan(client, data_pengguna["headers"]["staff"], lapangan["id"], mulai, selesai)
    assert respons.status_code == 403


def test_pemesanan_ditolak_jika_jadwal_berbenturan(client, data_pengguna):
    lapangan = buat_lapangan(client, data_pengguna["headers"]["admin"])
    mulai, selesai = waktu_mendatang()
    pertama = buat_pemesanan(client, data_pengguna["headers"]["customer"], lapangan["id"], mulai, selesai)
    kedua = buat_pemesanan(client, data_pengguna["headers"]["customer2"], lapangan["id"], mulai, selesai)
    assert pertama.status_code == 201
    assert kedua.status_code == 409
    assert kedua.json()["code"] == "JADWAL_BENTROK"


def test_jadwal_berurutan_tepat_di_batas_tidak_dianggap_bentrok(client, data_pengguna):
    lapangan = buat_lapangan(client, data_pengguna["headers"]["admin"])
    mulai, _ = waktu_mendatang()
    pertama = buat_pemesanan(
        client, data_pengguna["headers"]["customer"], lapangan["id"], mulai, mulai + timedelta(hours=1)
    )
    kedua = buat_pemesanan(
        client,
        data_pengguna["headers"]["customer2"],
        lapangan["id"],
        mulai + timedelta(hours=1),
        mulai + timedelta(hours=2),
    )
    assert pertama.status_code == 201
    assert kedua.status_code == 201


def test_pemesanan_ditolak_untuk_lapangan_nonaktif(client, data_pengguna):
    header_admin = data_pengguna["headers"]["admin"]
    lapangan = buat_lapangan(client, header_admin)
    nonaktif = client.patch(
        f"/api/v1/lapangan/{lapangan['id']}", headers=header_admin, json={"aktif": False}
    )
    assert nonaktif.status_code == 200
    mulai, selesai = waktu_mendatang()
    respons = buat_pemesanan(client, data_pengguna["headers"]["customer"], lapangan["id"], mulai, selesai)
    assert respons.status_code == 409
    assert respons.json()["code"] == "LAPANGAN_NONAKTIF"


def test_pemesanan_ditolak_jika_lapangan_tidak_ditemukan(client, data_pengguna):
    mulai, selesai = waktu_mendatang()
    respons = buat_pemesanan(client, data_pengguna["headers"]["customer"], 999, mulai, selesai)
    assert respons.status_code == 404
    assert respons.json()["code"] == "LAPANGAN_TIDAK_DITEMUKAN"


def test_pelanggan_hanya_melihat_pemesanan_milik_sendiri(client, data_pengguna):
    lapangan = buat_lapangan(client, data_pengguna["headers"]["admin"])
    milik_satu = buat_pemesanan(client, data_pengguna["headers"]["customer"], lapangan["id"])
    assert milik_satu.status_code == 201
    id_pemesanan = milik_satu.json()["id"]
    daftar_dua = client.get("/api/v1/pemesanan", headers=data_pengguna["headers"]["customer2"])
    detail_dua = client.get(
        f"/api/v1/pemesanan/{id_pemesanan}", headers=data_pengguna["headers"]["customer2"]
    )
    assert daftar_dua.status_code == 200 and daftar_dua.json() == []
    assert detail_dua.status_code == 403


def test_pelanggan_dapat_membatalkan_pemesanan_yang_menunggu(client, data_pengguna):
    lapangan = buat_lapangan(client, data_pengguna["headers"]["admin"])
    pemesanan = buat_pemesanan(client, data_pengguna["headers"]["customer"], lapangan["id"])
    respons = client.delete(
        f"/api/v1/pemesanan/{pemesanan.json()['id']}", headers=data_pengguna["headers"]["customer"]
    )
    assert respons.status_code == 204
    daftar = client.get("/api/v1/pemesanan", headers=data_pengguna["headers"]["customer"])
    assert daftar.json()[0]["status"] == "DIBATALKAN"


def test_slot_dapat_dipesan_lagi_setelah_pemesanan_dibatalkan(client, data_pengguna):
    lapangan = buat_lapangan(client, data_pengguna["headers"]["admin"])
    mulai, selesai = waktu_mendatang()
    pemesanan = buat_pemesanan(client, data_pengguna["headers"]["customer"], lapangan["id"], mulai, selesai)
    client.delete(
        f"/api/v1/pemesanan/{pemesanan.json()['id']}", headers=data_pengguna["headers"]["customer"]
    )
    berikutnya = buat_pemesanan(client, data_pengguna["headers"]["customer2"], lapangan["id"], mulai, selesai)
    assert berikutnya.status_code == 201


def test_staf_tidak_bisa_mengonfirmasi_pemesanan_langsung(client, data_pengguna):
    lapangan = buat_lapangan(client, data_pengguna["headers"]["admin"])
    pemesanan = buat_pemesanan(client, data_pengguna["headers"]["customer"], lapangan["id"])
    respons = client.patch(
        f"/api/v1/pemesanan/{pemesanan.json()['id']}/status",
        headers=data_pengguna["headers"]["staff"],
        json={"status": "DIKONFIRMASI"},
    )
    assert respons.status_code == 409
    assert respons.json()["code"] == "KONFIRMASI_MELALUI_PEMBAYARAN"


def test_pelanggan_tidak_dapat_mengubah_status_pemesanan_via_endpoint_staf(client, data_pengguna):
    lapangan = buat_lapangan(client, data_pengguna["headers"]["admin"])
    pemesanan = buat_pemesanan(client, data_pengguna["headers"]["customer"], lapangan["id"])
    respons = client.patch(
        f"/api/v1/pemesanan/{pemesanan.json()['id']}/status",
        headers=data_pengguna["headers"]["customer"],
        json={"status": "DIBATALKAN"},
    )
    assert respons.status_code == 403


def test_pengguna_tidak_bisa_membatalkan_pemesanan_pelanggan_lain(client, data_pengguna):
    lapangan = buat_lapangan(client, data_pengguna["headers"]["admin"])
    pemesanan = buat_pemesanan(client, data_pengguna["headers"]["customer"], lapangan["id"])
    respons = client.delete(
        f"/api/v1/pemesanan/{pemesanan.json()['id']}", headers=data_pengguna["headers"]["customer2"]
    )
    assert respons.status_code == 403


def test_filter_daftar_pemesanan_berdasarkan_status(client, data_pengguna):
    lapangan = buat_lapangan(client, data_pengguna["headers"]["admin"])
    pemesanan = buat_pemesanan(client, data_pengguna["headers"]["customer"], lapangan["id"])
    client.delete(
        f"/api/v1/pemesanan/{pemesanan.json()['id']}", headers=data_pengguna["headers"]["customer"]
    )
    respons = client.get(
        "/api/v1/pemesanan?status=DIBATALKAN", headers=data_pengguna["headers"]["admin"]
    )
    assert respons.status_code == 200
    assert all(item["status"] == "DIBATALKAN" for item in respons.json())
