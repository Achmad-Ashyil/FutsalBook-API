"""Perintah administrasi untuk membuat pengguna pertama atau pengguna lokal."""

import argparse
import sys

from sqlalchemy import select

from futsalbook.inti.database import buat_sesi
from futsalbook.inti.enums import PeranPengguna
from futsalbook.inti.keamanan import buat_kunci_api, hash_kunci_api
from futsalbook.model.pengguna import Pengguna


def main() -> None:
    """Menjalankan subperintah administrasi FutsalBook."""
    parser = argparse.ArgumentParser(description="Peralatan administrasi FutsalBook")
    subparsers = parser.add_subparsers(dest="perintah", required=True)
    tambah = subparsers.add_parser("buat-pengguna", help="Buat pengguna dan terbitkan API key")
    tambah.add_argument("--nama", required=True, help="Nama pengguna")
    tambah.add_argument("--email", required=True, help="Email pengguna")
    tambah.add_argument("--peran", required=True, choices=[peran.value for peran in PeranPengguna])
    argumen = parser.parse_args()

    with buat_sesi() as db:
        email = argumen.email.strip().lower()
        if db.scalar(select(Pengguna.id).where(Pengguna.email == email)) is not None:
            print("Gagal: email sudah digunakan.", file=sys.stderr)
            raise SystemExit(2)
        api_key = buat_kunci_api()
        pengguna = Pengguna(
            nama=argumen.nama.strip(),
            email=email,
            peran=PeranPengguna(argumen.peran),
            api_key_hash=hash_kunci_api(api_key),
            aktif=True,
        )
        db.add(pengguna)
        db.commit()
        db.refresh(pengguna)
        print("Pengguna berhasil dibuat.")
        print(f"ID       : {pengguna.id}")
        print(f"Nama     : {pengguna.nama}")
        print(f"Email    : {pengguna.email}")
        print(f"Peran    : {pengguna.peran.value}")
        print(f"API key  : {api_key}")
        print("Simpan API key sekarang; kunci asli tidak disimpan di basis data.")


if __name__ == "__main__":
    main()
