# FutsalBook API

> Proyek tugas Pemrograman Lanjut — backend REST API berbahasa Indonesia.

> Proyek tugas Pemrograman Lanjut — backend REST API berbahasa Indonesia.

Backend pemesanan lapangan futsal berbasis **FastAPI**, **Pydantic v2**, **SQLAlchemy 2**, dan **PostgreSQL**. Proyek ini disusun modular dengan kontrak data, autentikasi `X-API-Key` per pengguna, pembatasan peran (`ADMIN`, `STAFF`, `CUSTOMER`), migrasi basis data, pengujian otomatis, dan quality gate.

## 1. Fitur inti

- Mengelola lapangan: melihat, menambah, memperbarui, dan menonaktifkan lapangan.
- Mengelola pengguna: membuat pengguna dan API key, melihat profil, menonaktifkan akun, serta merotasi API key.
- Memesan lapangan dengan pemeriksaan jam masa depan, tarif per jam, dan benturan jadwal.
- Mencatat pembayaran transfer bank, tunai, atau QRIS; staf/admin dapat memverifikasi hasil pembayaran.
- Pembayaran yang berhasil mengubah status pemesanan menjadi `DIKONFIRMASI`.
- Penanganan error terpusat dengan bentuk respons JSON yang konsisten.
- Dokumentasi OpenAPI interaktif di `/docs` dan ReDoc di `/redoc`.
- Minimal 15 pengujian otomatis dengan FastAPI `TestClient` dan Pytest.

> Integrasi ini **mencatat** pembayaran dan verifikasi internal. Ini bukan integrasi gateway pembayaran sungguhan dan tidak memproses uang secara langsung.

## 2. Arsitektur modular

```text
src/futsalbook/
├── main.py                 # Pembuatan aplikasi, router, handler error
├── cli.py                  # Perintah administrasi untuk membuat pengguna
├── inti/
│   ├── konfigurasi.py      # Pydantic Settings dan environment
│   ├── database.py        # Engine, session, dan Base SQLAlchemy
│   ├── enums.py           # Peran dan status domain
│   └── keamanan.py        # X-API-Key dan RBAC melalui Depends
├── model/                  # Model SQLAlchemy: pengguna, lapangan, pemesanan, pembayaran
├── skema/                  # Kontrak Pydantic: buat, ubah, dan baca
├── layanan/                # Aturan bisnis pemesanan dan pembayaran
└── router/                 # Endpoint per domain
migrations/                 # Versi skema PostgreSQL via Alembic
.python-version             # Versi Python acuan untuk uv
tests/                      # Unit dan pengujian API menggunakan TestClient
.github/workflows/ci.yml    # Lint, tes otomatis, dan coverage
pyproject.toml              # Metadata paket, dependensi, konfigurasi pytest/ruff/coverage
uv.lock                     # Dihasilkan dengan uv lock lalu dikomit
```

### Keputusan rancangan penting

- API business menggunakan resource berorientasi kata benda: `/lapangan`, `/pengguna`, `/pemesanan`, dan `/pembayaran`.
- Kontrak permintaan, pembaruan, dan respons dipisah. API key mentah hanya diberikan saat akun dibuat atau kunci dirotasi; yang tersimpan di basis data adalah hash SHA-256.
- `X-API-Key` dipublikasikan sebagai skema keamanan OpenAPI, sehingga bisa diisi melalui tombol **Authorize** di Swagger UI.
- Pengguna `CUSTOMER` hanya dapat membaca dan mengelola pemesanan/pembayaran miliknya. `STAFF` mengelola lapangan, pemesanan, dan verifikasi pembayaran. `ADMIN` memiliki akses administratif, termasuk manajemen pengguna dan penonaktifan lapangan.
- Data transaksi tidak dihapus permanen ketika pemesanan dibatalkan. Status berubah menjadi `DIBATALKAN` supaya riwayat tetap ada.
- Jadwal memakai interval setengah terbuka `[mulai, selesai)`, sehingga pemesanan 18.00–19.00 dan 19.00–20.00 tidak dianggap bertabrakan. Migrasi PostgreSQL juga menambahkan exclusion constraint `btree_gist` untuk melindungi dari benturan saat permintaan bersamaan.
- Pemesanan menggunakan kelipatan satu jam penuh sesuai tarif per jam. Waktu permintaan harus mencantumkan zona waktu.

## 3. Persiapan lokal

Prasyarat: Python 3.11–3.13, Git, Docker dengan Docker Compose, serta `uv`.

### Instalasi `uv`

Panduan instalasi resmi tersedia di <https://docs.astral.sh/uv/getting-started/installation/>. Setelah instalasi, pastikan perintah `uv --version` berjalan.

### Jalankan PostgreSQL

Dari direktori proyek:

```bash
docker compose up -d postgres
```

Konfigurasi lokal:

```bash
cp .env.example .env
```

Di PowerShell Windows:

```powershell
Copy-Item .env.example .env
```

Nilai bawaan `.env.example` sesuai dengan PostgreSQL pada `docker-compose.yml` untuk pengembangan lokal. **Jangan commit `.env`**; berkas itu sudah masuk `.gitignore`.

### Pasang dependensi yang terkunci

```bash
uv lock
uv sync --locked --all-groups
```

`uv lock` menghasilkan `uv.lock` yang mematok versi dan hash artefak. Simpan berkas ini di Git agar instalasi tim tetap konsisten. Lingkungan pembuatan artefak ini tidak dapat mengakses PyPI, jadi lockfile tidak dibuat secara palsu; jalankan dua perintah di atas sekali pada mesin Anda yang memiliki jaringan, lalu sertakan `uv.lock` dalam commit. Setelah lockfile tersedia, gunakan `uv sync --locked --all-groups`.

### Buat tabel

```bash
uv run alembic upgrade head
```

Jalankan migrasi setiap kali menarik versi proyek yang membawa migrasi baru.

## 4. Buat pengguna pertama

Buat pengguna administrator melalui CLI; langkah ini diperlukan karena API belum memiliki endpoint registrasi publik:

```bash
uv run python -m futsalbook.cli buat-pengguna --nama "Admin FutsalBook" --email admin@futsalbook.local --peran ADMIN
```

CLI menampilkan API key. **Salin dan simpan di tempat aman saat itu juga.** API key asli tidak bisa dibaca kembali dari basis data. Buat akun `STAFF` dan `CUSTOMER` dari endpoint `POST /api/v1/pengguna` setelah masuk sebagai admin, atau gunakan CLI untuk akun awal lainnya.

## 5. Jalankan API

```bash
uv run uvicorn futsalbook.main:app --reload
```

- Beranda: <http://127.0.0.1:8000/>
- Pemeriksaan kesehatan: <http://127.0.0.1:8000/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

Pada Swagger UI, klik **Authorize**, masukkan API key pada skema `X-API-Key`, lalu coba endpoint yang sesuai dengan peran akun.

## 6. Ringkasan kontrak endpoint

Semua endpoint di bawah prefix `/api/v1` membutuhkan `X-API-Key`, kecuali `/`, `/health`, `/docs`, `/redoc`, dan dokumen OpenAPI.

| Metode | Endpoint | Hak akses | Kegunaan |
|---|---|---|---|
| `GET` | `/lapangan` | Semua pengguna aktif | Daftar dan filter lapangan |
| `POST` | `/lapangan` | `ADMIN`, `STAFF` | Membuat lapangan |
| `GET` | `/lapangan/{id}` | Semua pengguna aktif | Detail lapangan |
| `PATCH` | `/lapangan/{id}` | `ADMIN`, `STAFF` | Mengubah data atau status aktif |
| `DELETE` | `/lapangan/{id}` | `ADMIN` | Menonaktifkan lapangan (soft delete) |
| `GET` | `/pengguna/me` | Semua pengguna aktif | Profil akun saat ini |
| `GET` | `/pengguna` | `ADMIN` | Daftar pengguna tanpa kredensial |
| `POST` | `/pengguna` | `ADMIN` | Membuat akun dan menerbitkan API key |
| `PATCH` | `/pengguna/{id}/status` | `ADMIN` | Mengaktifkan/nonaktifkan akun |
| `POST` | `/pengguna/{id}/rotasi-kunci` | `ADMIN` | Mengganti API key dan mengembalikannya sekali |
| `GET` | `/pemesanan` | Semua pengguna aktif | Daftar; pelanggan hanya miliknya |
| `POST` | `/pemesanan` | `CUSTOMER` | Memesan lapangan |
| `GET` | `/pemesanan/{id}` | Pemilik, `STAFF`, `ADMIN` | Detail pemesanan |
| `PATCH` | `/pemesanan/{id}/status` | `STAFF`, `ADMIN` | Membatalkan yang belum dibayar atau menyelesaikan yang dikonfirmasi |
| `DELETE` | `/pemesanan/{id}` | Pemilik, `STAFF`, `ADMIN` | Membatalkan pemesanan yang belum dibayar; riwayat dipertahankan |
| `GET` | `/pembayaran` | Semua pengguna aktif | Daftar pembayaran sesuai hak akses |
| `POST` | `/pembayaran` | Pengguna aktif | Membuat catatan pembayaran untuk pemesanan yang boleh diakses |
| `GET` | `/pembayaran/{id}` | Pemilik, `STAFF`, `ADMIN` | Detail pembayaran |
| `PATCH` | `/pembayaran/{id}/status` | `STAFF`, `ADMIN` | Verifikasi pembayaran `BERHASIL` atau `GAGAL` |

### Alur pemesanan

1. `CUSTOMER` melihat lapangan aktif melalui `GET /api/v1/lapangan`.
2. Pelanggan membuat pemesanan melalui `POST /api/v1/pemesanan` menggunakan `lapangan_id`, `mulai`, dan `selesai` (tanggal/waktu ISO 8601 dengan zona waktu).
3. Pemesanan dibuat dengan status `MENUNGGU_PEMBAYARAN` dan total biaya dihitung dari tarif lapangan.
4. Pelanggan membuat catatan pembayaran melalui `POST /api/v1/pembayaran`.
5. `STAFF` atau `ADMIN` memverifikasi hasil pembayaran lewat `PATCH /api/v1/pembayaran/{id}/status` dengan status `BERHASIL` atau `GAGAL`.
6. Pembayaran `BERHASIL` secara otomatis mengubah pemesanan menjadi `DIKONFIRMASI`. Staf/admin dapat mengubah pemesanan yang dikonfirmasi menjadi `SELESAI`.

Status HTTP penting: `200` berhasil, `201` resource dibuat, `204` operasi tanpa isi respons, `401` API key tidak valid/tidak ada, `403` hak akses ditolak, `404` resource tidak ditemukan, `409` konflik aturan bisnis/data, dan `422` kontrak request tidak valid.

## 7. Jalankan tes dan quality gate

```bash
uv run pytest --cov=futsalbook --cov-report=term-missing --cov-fail-under=75
uv run ruff check .
```

Pengujian memakai basis data SQLite sementara supaya unit/integration test dapat dijalankan tanpa PostgreSQL aktif. PostgreSQL tetap menjadi basis data target aplikasi. Pengujian utama mengacu pada pola **Arrange–Act–Assert**, fixture pengguna, API key, dan basis data terisolasi.

CI GitHub Actions menjalankan sinkronisasi dependensi, lint melalui Ruff, tes otomatis, dan batas minimal cakupan kode 75%. Jika `uv.lock` belum tersedia, alur CI akan membuatnya sementara agar pemeriksaan tetap dapat berjalan; untuk reproducibility yang benar sesuai materi Pekan 05, jalankan `uv lock` secara lokal dan commit berkas `uv.lock` ke repositori sebelum mengandalkan instalasi terkunci. Pemeriksaan PostgreSQL langsung perlu dilakukan di mesin yang menjalankan layanan PostgreSQL; tes otomatis yang disertakan menggunakan SQLite sementara untuk isolasi.

## 8. Migrasi dan perubahan skema

Setiap perubahan struktur basis data harus disertai migrasi Alembic. Untuk membuat revisi migrasi setelah model berubah:

```bash
uv run alembic revision --autogenerate -m "jelaskan perubahan skema"
```

Periksa dan edit file migrasi hasil generator sebelum menggunakannya; autogenerate tidak selalu mengenali setiap batasan PostgreSQL khusus. Terapkan perubahan menggunakan `uv run alembic upgrade head`.

## 9. Alur Git yang disarankan

Gunakan branch fitur dan Conventional Commits, misalnya:

```bash
git switch -c feat/pemesanan-lapangan
git add .
git commit -m "feat(pemesanan): tambah aturan benturan jadwal"
git push -u origin feat/pemesanan-lapangan
```

Buka Pull Request untuk review sebelum digabungkan ke `main`. Contoh tipe commit: `feat`, `fix`, `test`, `docs`, `refactor`, dan `chore`. Untuk rilis, ikuti SemVer: MAJOR untuk perubahan kontrak yang tidak kompatibel, MINOR untuk fitur yang kompatibel, PATCH untuk perbaikan yang kompatibel.

### Inisialisasi repositori dan push pertama

Setelah proyek diekstrak dan `uv.lock` dibuat, jalankan perintah berikut dari direktori proyek. Buat repositori kosong di GitHub terlebih dahulu, lalu ganti `<URL_REPOSITORI_ANDA>` dengan URL repositori milik Anda.

```bash
git init
git switch -c main
git add .
git commit -m "feat(api): inisialisasi backend FutsalBook"
git remote add origin <URL_REPOSITORI_ANDA>
git push -u origin main
```

Jika repositori lokal sudah terhubung ke Git, jangan jalankan `git init` atau menambahkan remote yang sama lagi; cukup commit perubahan dan push ke branch yang sesuai.

## 10. Catatan keamanan sebelum produksi

- Ganti kredensial PostgreSQL dan gunakan secret manager atau environment variables pada server.
- Jangan memasukkan `.env`, API key, dump basis data, atau kredensial ke Git.
- Terapkan HTTPS/TLS, pembatasan percobaan kunci, audit log, rotasi kunci berkala, backup, dan pemantauan saat deployment.
- Verifikasi pembayaran hanya membuktikan bahwa staf/admin mencatat transaksi sebagai berhasil; sistem ini belum memanggil penyedia pembayaran eksternal.
- Migrasi jadwal memakai exclusion constraint PostgreSQL untuk mengurangi risiko benturan akibat permintaan bersamaan. Saat mengembangkan SQLite test, pengujian logika benturan berjalan melalui service; constraint PostgreSQL divalidasi pada lingkungan PostgreSQL.
