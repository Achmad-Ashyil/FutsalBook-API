"""Membuat tabel inti dan batasan benturan jadwal PostgreSQL."""

from alembic import op
import sqlalchemy as sa

revision = "0001_awal"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # btree_gist memungkinkan indeks GiST membandingkan ID lapangan dan rentang waktu.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "pengguna",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nama", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("peran", sa.String(length=20), nullable=False),
        sa.Column("api_key_hash", sa.String(length=64), nullable=False),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("dibuat_pada", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("peran IN ('ADMIN', 'STAFF', 'CUSTOMER')", name="ck_pengguna_peran"),
    )
    op.create_index("ix_pengguna_email", "pengguna", ["email"], unique=True)
    op.create_index("ix_pengguna_api_key_hash", "pengguna", ["api_key_hash"], unique=True)

    op.create_table(
        "lapangan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nama", sa.String(length=100), nullable=False),
        sa.Column("lokasi", sa.String(length=200), nullable=False),
        sa.Column("jenis", sa.String(length=20), nullable=False),
        sa.Column("tarif_per_jam", sa.Numeric(12, 2), nullable=False),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("dibuat_pada", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("tarif_per_jam > 0", name="ck_lapangan_tarif_positif"),
        sa.CheckConstraint("jenis IN ('SINTETIS', 'VINYL', 'SEMEN')", name="ck_lapangan_jenis"),
    )
    op.create_index("ix_lapangan_nama", "lapangan", ["nama"], unique=True)

    op.create_table(
        "pemesanan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pengguna_id", sa.Integer(), sa.ForeignKey("pengguna.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("lapangan_id", sa.Integer(), sa.ForeignKey("lapangan.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("mulai", sa.DateTime(timezone=True), nullable=False),
        sa.Column("selesai", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("total_biaya", sa.Numeric(12, 2), nullable=False),
        sa.Column("dibuat_pada", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("selesai > mulai", name="ck_pemesanan_jam_valid"),
        sa.CheckConstraint("total_biaya > 0", name="ck_pemesanan_biaya_positif"),
        sa.CheckConstraint(
            "status IN ('MENUNGGU_PEMBAYARAN', 'DIKONFIRMASI', 'DIBATALKAN', 'SELESAI')",
            name="ck_pemesanan_status",
        ),
    )
    op.create_index("ix_pemesanan_pengguna_id", "pemesanan", ["pengguna_id"])
    op.create_index("ix_pemesanan_lapangan_id", "pemesanan", ["lapangan_id"])
    op.create_index("ix_pemesanan_mulai", "pemesanan", ["mulai"])
    op.create_index("ix_pemesanan_selesai", "pemesanan", ["selesai"])
    op.execute(
        "ALTER TABLE pemesanan ADD CONSTRAINT ex_pemesanan_jadwal_tidak_bentrok "
        "EXCLUDE USING gist (lapangan_id WITH =, tstzrange(mulai, selesai, '[)') WITH &&) "
        "WHERE (status <> 'DIBATALKAN')"
    )

    op.create_table(
        "pembayaran",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pemesanan_id", sa.Integer(), sa.ForeignKey("pemesanan.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("jumlah", sa.Numeric(12, 2), nullable=False),
        sa.Column("metode", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("diverifikasi_oleh_id", sa.Integer(), sa.ForeignKey("pengguna.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("dibuat_pada", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("diverifikasi_pada", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("jumlah > 0", name="ck_pembayaran_jumlah_positif"),
        sa.CheckConstraint("metode IN ('TRANSFER_BANK', 'TUNAI', 'QRIS')", name="ck_pembayaran_metode"),
        sa.CheckConstraint("status IN ('MENUNGGU', 'BERHASIL', 'GAGAL')", name="ck_pembayaran_status"),
    )
    op.create_index("ix_pembayaran_pemesanan_id", "pembayaran", ["pemesanan_id"])
    op.execute(
        "CREATE UNIQUE INDEX uq_pembayaran_aktif_per_pemesanan ON pembayaran (pemesanan_id) "
        "WHERE status IN ('MENUNGGU', 'BERHASIL')"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_pembayaran_aktif_per_pemesanan")
    op.drop_index("ix_pembayaran_pemesanan_id", table_name="pembayaran")
    op.drop_table("pembayaran")
    op.execute("ALTER TABLE pemesanan DROP CONSTRAINT IF EXISTS ex_pemesanan_jadwal_tidak_bentrok")
    op.drop_index("ix_pemesanan_selesai", table_name="pemesanan")
    op.drop_index("ix_pemesanan_mulai", table_name="pemesanan")
    op.drop_index("ix_pemesanan_lapangan_id", table_name="pemesanan")
    op.drop_index("ix_pemesanan_pengguna_id", table_name="pemesanan")
    op.drop_table("pemesanan")
    op.drop_index("ix_lapangan_nama", table_name="lapangan")
    op.drop_table("lapangan")
    op.drop_index("ix_pengguna_api_key_hash", table_name="pengguna")
    op.drop_index("ix_pengguna_email", table_name="pengguna")
    op.drop_table("pengguna")
