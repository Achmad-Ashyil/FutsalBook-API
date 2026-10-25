"""Konfigurasi lingkungan migrasi Alembic."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from futsalbook.inti.konfigurasi import dapatkan_pengaturan
from futsalbook.inti.database import BasisModel
from futsalbook import model  # noqa: F401 - mendaftarkan semua model ke metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", dapatkan_pengaturan().database_url.replace("%", "%%"))
target_metadata = BasisModel.metadata


def jalankan_migrasi_offline() -> None:
    """Menghasilkan SQL migrasi tanpa membuka koneksi."""
    context.configure(
        url=dapatkan_pengaturan().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def jalankan_migrasi_online() -> None:
    """Menjalankan migrasi menggunakan koneksi basis data."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    jalankan_migrasi_offline()
else:
    jalankan_migrasi_online()
