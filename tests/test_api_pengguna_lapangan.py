"""Pengujian endpoint pengguna dan lapangan via TestClient."""


def buat_lapangan(client, header, nama="Lapangan A", tarif=150000):
    return client.post(
        "/api/v1/lapangan",
        headers=header,
        json={"nama": nama, "lokasi": "Samata, Gowa", "jenis": "SINTETIS", "tarif_per_jam": tarif},
    )


def test_health_tidak_memerlukan_api_key(client):
    respons = client.get("/health")
    assert respons.status_code == 200
    assert respons.json() == {"status": "ok"}


def test_openapi_mencantumkan_skema_api_key(client):
    dokumen = client.get("/openapi.json").json()
    skema = dokumen["components"]["securitySchemes"]
    assert any(item.get("name") == "X-API-Key" and item.get("type") == "apiKey" for item in skema.values())


def test_endpoint_bisnis_tanpa_key_mengembalikan_401_konsisten(client):
    respons = client.get("/api/v1/lapangan")
    assert respons.status_code == 401
    assert respons.json()["code"] == "API_KEY_DIBUTUHKAN"
    assert respons.json()["status"] == "error"


def test_api_key_tidak_valid_mengembalikan_401(client):
    respons = client.get("/api/v1/pengguna/me", headers={"X-API-Key": "kunci-salah"})
    assert respons.status_code == 401
    assert respons.json()["code"] == "API_KEY_TIDAK_VALID"


def test_profil_pelanggan_tidak_membocorkan_key_atau_hash(client, data_pengguna):
    respons = client.get("/api/v1/pengguna/me", headers=data_pengguna["headers"]["customer"])
    assert respons.status_code == 200
    assert respons.json()["email"] == "satu@example.com"
    assert "api_key" not in respons.json()
    assert "api_key_hash" not in respons.json()


def test_pengguna_nonaktif_tidak_dapat_masuk(client, data_pengguna, sesi_factory):
    from futsalbook.model import Pengguna

    with sesi_factory() as db:
        pengguna = db.get(Pengguna, data_pengguna["admin"]["id"])
        pengguna.aktif = False
        db.commit()
    respons = client.get("/api/v1/pengguna/me", headers=data_pengguna["headers"]["admin"])
    assert respons.status_code == 401


def test_pelanggan_tidak_dapat_membuat_lapangan(client, data_pengguna):
    respons = buat_lapangan(client, data_pengguna["headers"]["customer"])
    assert respons.status_code == 403
    assert respons.json()["code"] == "AKSES_DITOLAK"


def test_staf_dapat_membuat_lapangan(client, data_pengguna):
    respons = buat_lapangan(client, data_pengguna["headers"]["staff"])
    assert respons.status_code == 201
    assert respons.json()["nama"] == "Lapangan A"
    assert respons.json()["tarif_per_jam"] == "150000.00"


def test_tarif_nol_menghasilkan_422_dan_format_error_seragam(client, data_pengguna):
    respons = buat_lapangan(client, data_pengguna["headers"]["staff"], tarif=0)
    assert respons.status_code == 422
    assert respons.json()["code"] == "VALIDASI_GAGAL"
    assert respons.json()["details"][0]["message"]


def test_nama_lapangan_duplikat_menghasilkan_409(client, data_pengguna):
    header = data_pengguna["headers"]["staff"]
    assert buat_lapangan(client, header).status_code == 201
    respons = buat_lapangan(client, header)
    assert respons.status_code == 409
    assert respons.json()["code"] == "KONFLIK_DATA"


def test_pelanggan_hanya_melihat_lapangan_aktif(client, data_pengguna):
    header_admin = data_pengguna["headers"]["admin"]
    dibuat = buat_lapangan(client, header_admin)
    lapangan_id = dibuat.json()["id"]
    nonaktif = client.patch(f"/api/v1/lapangan/{lapangan_id}", headers=header_admin, json={"aktif": False})
    assert nonaktif.status_code == 200
    daftar = client.get("/api/v1/lapangan", headers=data_pengguna["headers"]["customer"])
    assert daftar.status_code == 200
    assert all(item["aktif"] for item in daftar.json())


def test_rotasi_kunci_mencabut_kunci_lama(client, data_pengguna):
    header_admin = data_pengguna["headers"]["admin"]
    id_pengguna = data_pengguna["customer"]["id"]
    respons = client.post(f"/api/v1/pengguna/{id_pengguna}/rotasi-kunci", headers=header_admin)
    assert respons.status_code == 200
    key_baru = respons.json()["api_key"]
    lama = client.get("/api/v1/pengguna/me", headers=data_pengguna["headers"]["customer"])
    baru = client.get("/api/v1/pengguna/me", headers={"X-API-Key": key_baru})
    assert lama.status_code == 401
    assert baru.status_code == 200


def test_pelanggan_tidak_dapat_melihat_daftar_pengguna(client, data_pengguna):
    respons = client.get("/api/v1/pengguna", headers=data_pengguna["headers"]["customer"])
    assert respons.status_code == 403


def test_admin_dapat_membuat_pengguna_dan_kunci(client, data_pengguna):
    respons = client.post(
        "/api/v1/pengguna",
        headers=data_pengguna["headers"]["admin"],
        json={"nama": "Pelanggan Baru", "email": "baru@example.com", "peran": "CUSTOMER"},
    )
    assert respons.status_code == 201
    assert respons.json()["api_key"]
    assert "api_key_hash" not in respons.json()
    assert client.get("/api/v1/pengguna/me", headers={"X-API-Key": respons.json()["api_key"]}).status_code == 200


def test_email_pengguna_duplikat_menghasilkan_409(client, data_pengguna):
    respons = client.post(
        "/api/v1/pengguna",
        headers=data_pengguna["headers"]["admin"],
        json={"nama": "Duplikat", "email": "admin@example.com", "peran": "STAFF"},
    )
    assert respons.status_code == 409
    assert respons.json()["code"] == "EMAIL_SUDAH_DIGUNAKAN"
