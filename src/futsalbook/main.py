"""Titik masuk aplikasi FastAPI dan penanganan kesalahan terpusat."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from futsalbook import __version__
from futsalbook.inti.konfigurasi import dapatkan_pengaturan
from futsalbook.router import lapangan, pembayaran, pemesanan, pengguna

pengaturan = dapatkan_pengaturan()
logging.basicConfig(level=pengaturan.log_level.upper())
logger = logging.getLogger("futsalbook")

app = FastAPI(
    title=pengaturan.nama_aplikasi,
    description=(
        "REST API untuk pengelolaan lapangan, pemesanan, pembayaran, dan pengguna FutsalBook. "
        "Semua endpoint bisnis memerlukan header `X-API-Key`; hak akses ditentukan melalui peran pengguna."
    ),
    version=__version__,
    contact={"name": "Tim FutsalBook"},
    openapi_tags=[
        {"name": "Lapangan", "description": "Daftar dan pengelolaan lapangan futsal."},
        {"name": "Pengguna", "description": "Profil pengguna dan pengelolaan API key."},
        {"name": "Pemesanan", "description": "Pembuatan, pencarian, dan perubahan status pemesanan."},
        {"name": "Pembayaran", "description": "Pencatatan dan verifikasi pembayaran pemesanan."},
        {"name": "Kesehatan", "description": "Pemeriksaan ketersediaan proses API."},
    ],
)

app.include_router(pengguna.router, prefix=pengaturan.api_versi)
app.include_router(lapangan.router, prefix=pengaturan.api_versi)
app.include_router(pemesanan.router, prefix=pengaturan.api_versi)
app.include_router(pembayaran.router, prefix=pengaturan.api_versi)


@app.get("/", tags=["Kesehatan"], summary="Informasi API")
def beranda():
    """Menunjukkan nama API dan lokasi dokumentasi interaktif."""
    return {"nama": pengaturan.nama_aplikasi, "versi": __version__, "dokumentasi": "/docs"}


@app.get("/health", tags=["Kesehatan"], summary="Pemeriksaan kesehatan")
def pemeriksaan_kesehatan():
    """Pemeriksaan liveness; tidak memuat kredensial ataupun informasi internal."""
    return {"status": "ok"}


def _pesan_validasi(error: dict) -> str:
    """Mengubah sebagian pesan validasi umum menjadi bahasa Indonesia."""
    jenis = error.get("type", "")
    kamus = {
        "missing": "Bidang ini wajib diisi.",
        "string_too_short": "Teks lebih pendek dari batas minimum.",
        "string_too_long": "Teks lebih panjang dari batas maksimum.",
        "greater_than": "Nilai harus lebih besar dari batas minimum.",
        "greater_than_equal": "Nilai harus lebih besar atau sama dengan batas minimum.",
        "less_than": "Nilai harus lebih kecil dari batas maksimum.",
        "less_than_equal": "Nilai harus lebih kecil atau sama dengan batas maksimum.",
        "decimal_max_digits": "Jumlah digit angka melebihi batas yang diizinkan.",
        "decimal_max_places": "Jumlah angka di belakang desimal melebihi batas yang diizinkan.",
        "enum": "Nilai bukan anggota pilihan yang diizinkan.",
        "int_parsing": "Nilai harus berupa bilangan bulat.",
        "bool_parsing": "Nilai harus berupa boolean (true atau false).",
        "datetime_parsing": "Format tanggal atau waktu tidak valid.",
        "email": "Format alamat email tidak valid.",
    }
    if jenis in kamus:
        return kamus[jenis]
    pesan = error.get("msg", "Nilai tidak valid.")
    return pesan.removeprefix("Value error, ").removeprefix("Input should be ")


@app.exception_handler(RequestValidationError)
async def penangan_validasi(request: Request, exc: RequestValidationError):
    """Menyamakan format respons ketika kontrak data tidak terpenuhi."""
    detail = [
        {
            "field": " -> ".join(str(bagian) for bagian in error.get("loc", ()) if bagian != "body"),
            "message": _pesan_validasi(error),
            "type": error.get("type", "validation_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "code": "VALIDASI_GAGAL",
            "message": "Permintaan tidak sesuai dengan kontrak data API.",
            "path": request.url.path,
            "details": detail,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def penangan_http(request: Request, exc: StarletteHTTPException):
    """Mengubah kesalahan HTTP menjadi satu bentuk JSON yang konsisten."""
    detail = exc.detail
    if isinstance(detail, dict):
        kode = detail.get("code", "KESALAHAN_HTTP")
        pesan = detail.get("message", "Permintaan tidak dapat diproses.")
        rincian = detail.get("details")
    else:
        kode_dasar = {404: "SUMBER_TIDAK_DITEMUKAN", 405: "METODE_TIDAK_DIDUKUNG"}
        kode = kode_dasar.get(exc.status_code, "KESALAHAN_HTTP")
        pesan = str(detail)
        rincian = None
    isi = {
        "status": "error",
        "code": kode,
        "message": pesan,
        "path": request.url.path,
    }
    if rincian is not None:
        isi["details"] = rincian
    return JSONResponse(status_code=exc.status_code, content=isi, headers=exc.headers)


@app.exception_handler(IntegrityError)
async def penangan_integritas(request: Request, exc: IntegrityError):
    """Menyamarkan pesan basis data dan mengembalikan konflik yang aman."""
    logger.info("Konflik integritas data pada %s", request.url.path)
    return JSONResponse(
        status_code=409,
        content={
            "status": "error",
            "code": "KONFLIK_DATA",
            "message": "Operasi bertentangan dengan data yang sudah tersimpan atau batasan basis data.",
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def penangan_internal(request: Request, exc: Exception):
    """Mengembalikan pesan 500 aman tanpa traceback atau kredensial ke klien."""
    logger.exception("Kesalahan internal saat memproses %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "code": "KESALAHAN_INTERNAL",
            "message": "Terjadi kesalahan internal. Silakan coba kembali atau hubungi pengelola.",
            "path": request.url.path,
        },
    )
