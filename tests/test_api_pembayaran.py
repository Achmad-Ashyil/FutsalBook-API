"""Pengujian integrasi alur pembayaran dan verifikasi."""

from datetime import datetime, timedelta, timezone


def buat_pemesanan(client, data_pengguna, nama_lapangan="Lapangan Bayar"):
    lapangan = client.post(
        "/api/v1/lapangan",
        headers=data_pengguna["headers"]["admin"],
        json={"nama": nama_lapangan, "lokasi": "Samata, Gowa", "jenis": "SINTETIS", "tarif_per_jam": 175000},
    )
    assert lapangan.status_code == 201
    mulai = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(days=4)
    pemesanan = client.post(
        "/api/v1/pemesanan",
        headers=data_pengguna["headers"]["customer"],
        json={
            "lapangan_id": lapangan.json()["id"],
            "mulai": mulai.isoformat(),
            "selesai": (mulai + timedelta(hours=2)).isoformat(),
        },
    )
    assert pemesanan.status_code == 201
    return pemesanan.json()


def buat_pembayaran(client, header, id_pemesanan, metode="QRIS"):
    return client.post(
        "/api/v1/pembayaran", headers=header, json={"pemesanan_id": id_pemesanan, "metode": metode}
    )


def test_pelanggan_dapat_membuat_pembayaran(client, data_pengguna):
    pemesanan = buat_pemesanan(client, data_pengguna)
    respons = buat_pembayaran(client, data_pengguna["headers"]["customer"], pemesanan["id"])
    assert respons.status_code == 201
    assert respons.json()["jumlah"] == "350000.00"
    assert respons.json()["status"] == "MENUNGGU"


def test_pelanggan_tidak_dapat_membayar_pemesanan_milik_orang_lain(client, data_pengguna):
    pemesanan = buat_pemesanan(client, data_pengguna)
    respons = buat_pembayaran(client, data_pengguna["headers"]["customer2"], pemesanan["id"])
    assert respons.status_code == 403


def test_pembayaran_berhasil_mengonfirmasi_pemesanan(client, data_pengguna):
    pemesanan = buat_pemesanan(client, data_pengguna)
    pembayaran = buat_pembayaran(client, data_pengguna["headers"]["customer"], pemesanan["id"])
    hasil = client.patch(
        f"/api/v1/pembayaran/{pembayaran.json()['id']}/status",
        headers=data_pengguna["headers"]["staff"],
        json={"status": "BERHASIL"},
    )
    detail_pemesanan = client.get(
        f"/api/v1/pemesanan/{pemesanan['id']}", headers=data_pengguna["headers"]["customer"]
    )
    assert hasil.status_code == 200
    assert hasil.json()["status"] == "BERHASIL"
    assert hasil.json()["diverifikasi_oleh_id"] == data_pengguna["staff"]["id"]
    assert detail_pemesanan.json()["status"] == "DIKONFIRMASI"


def test_pembayaran_final_tidak_bisa_diverifikasi_dua_kali(client, data_pengguna):
    pemesanan = buat_pemesanan(client, data_pengguna)
    pembayaran = buat_pembayaran(client, data_pengguna["headers"]["customer"], pemesanan["id"])
    url = f"/api/v1/pembayaran/{pembayaran.json()['id']}/status"
    pertama = client.patch(url, headers=data_pengguna["headers"]["staff"], json={"status": "GAGAL"})
    kedua = client.patch(url, headers=data_pengguna["headers"]["staff"], json={"status": "BERHASIL"})
    assert pertama.status_code == 200
    assert kedua.status_code == 409
    assert kedua.json()["code"] == "PEMBAYARAN_SUDAH_FINAL"


def test_pembayaran_gagal_dapat_dicoba_ulang(client, data_pengguna):
    pemesanan = buat_pemesanan(client, data_pengguna)
    pertama = buat_pembayaran(client, data_pengguna["headers"]["customer"], pemesanan["id"])
    client.patch(
        f"/api/v1/pembayaran/{pertama.json()['id']}/status",
        headers=data_pengguna["headers"]["staff"],
        json={"status": "GAGAL"},
    )
    kedua = buat_pembayaran(client, data_pengguna["headers"]["customer"], pemesanan["id"], metode="TRANSFER_BANK")
    assert kedua.status_code == 201
    assert kedua.json()["metode"] == "TRANSFER_BANK"


def test_pelanggan_tidak_dapat_memverifikasi_pembayaran(client, data_pengguna):
    pemesanan = buat_pemesanan(client, data_pengguna)
    pembayaran = buat_pembayaran(client, data_pengguna["headers"]["customer"], pemesanan["id"])
    respons = client.patch(
        f"/api/v1/pembayaran/{pembayaran.json()['id']}/status",
        headers=data_pengguna["headers"]["customer"],
        json={"status": "BERHASIL"},
    )
    assert respons.status_code == 403


def test_pemesanan_maksimal_satu_pembayaran_aktif(client, data_pengguna):
    pemesanan = buat_pemesanan(client, data_pengguna)
    pertama = buat_pembayaran(client, data_pengguna["headers"]["customer"], pemesanan["id"])
    kedua = buat_pembayaran(client, data_pengguna["headers"]["customer"], pemesanan["id"])
    assert pertama.status_code == 201
    assert kedua.status_code == 409
    assert kedua.json()["code"] == "PEMBAYARAN_SUDAH_ADA"


def test_pembayaran_tidak_dapat_dibuat_untuk_pemesanan_tidak_ditemukan(client, data_pengguna):
    respons = buat_pembayaran(client, data_pengguna["headers"]["customer"], 98765)
    assert respons.status_code == 404
    assert respons.json()["code"] == "PEMESANAN_TIDAK_DITEMUKAN"


def test_daftar_pembayaran_pelanggan_tidak_membocorkan_pembayaran_lain(client, data_pengguna):
    pemesanan = buat_pemesanan(client, data_pengguna)
    buat_pembayaran(client, data_pengguna["headers"]["customer"], pemesanan["id"])
    respons = client.get("/api/v1/pembayaran", headers=data_pengguna["headers"]["customer2"])
    assert respons.status_code == 200
    assert respons.json() == []


def test_endpoint_menolak_status_pembayaran_di_luar_kontrak(client, data_pengguna):
    pemesanan = buat_pemesanan(client, data_pengguna)
    pembayaran = buat_pembayaran(client, data_pengguna["headers"]["customer"], pemesanan["id"])
    respons = client.patch(
        f"/api/v1/pembayaran/{pembayaran.json()['id']}/status",
        headers=data_pengguna["headers"]["staff"],
        json={"status": "MENUNGGU"},
    )
    assert respons.status_code == 422
    assert respons.json()["code"] == "VALIDASI_GAGAL"
