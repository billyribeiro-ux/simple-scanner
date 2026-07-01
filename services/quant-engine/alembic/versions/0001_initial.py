"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "symbols",
        sa.Column("symbol", sa.String(length=16), primary_key=True),
        sa.Column("name", sa.String(length=255)),
        sa.Column("asset_type", sa.String(length=32), nullable=False, server_default="equity"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "bars",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("symbol", sa.String(length=16), nullable=False, index=True),
        sa.Column("interval", sa.String(length=8), nullable=False, index=True),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("timestamp_et", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(18, 6), nullable=False),
        sa.Column("high", sa.Numeric(18, 6), nullable=False),
        sa.Column("low", sa.Numeric(18, 6), nullable=False),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("vwap", sa.Numeric(18, 6)),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("ingestion_time", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("quality_flags", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_bars_symbol_interval_ts", "bars", ["symbol", "interval", "timestamp_utc"], unique=True)
    op.create_table(
        "features",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("symbol", sa.String(length=16), nullable=False, index=True),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("feature_set_version", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_table(
        "labels",
        sa.Column("label_id", sa.String(length=64), primary_key=True),
        sa.Column("symbol", sa.String(length=16), nullable=False, index=True),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("side", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    for table_name in [
        "quotes",
        "regimes",
        "model_runs",
        "model_metrics",
        "live_signals",
        "closed_signals",
        "daily_reviews",
        "provider_requests",
        "exports",
    ]:
        op.create_table(
            table_name,
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("payload", sa.JSON(), nullable=False),
        )


def downgrade() -> None:
    for table_name in [
        "exports",
        "provider_requests",
        "daily_reviews",
        "closed_signals",
        "live_signals",
        "model_metrics",
        "model_runs",
        "regimes",
        "quotes",
        "labels",
        "features",
        "bars",
        "symbols",
    ]:
        op.drop_table(table_name)
