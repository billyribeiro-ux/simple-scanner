"""initial persistence schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-30
"""

from __future__ import annotations

from alembic import op

from app.db.schema import metadata


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    metadata.create_all(bind=op.get_bind())
    op.create_index("ix_bars_lookup", "bars", ["symbol", "interval", "timestamp_utc"], unique=False)
    op.create_index("ix_features_lookup", "features", ["symbol", "interval", "timestamp_utc"], unique=False)
    op.create_index("ix_live_signals_latest", "live_signals", ["timestamp_utc", "ticker"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_live_signals_latest", table_name="live_signals")
    op.drop_index("ix_features_lookup", table_name="features")
    op.drop_index("ix_bars_lookup", table_name="bars")
    for table in reversed(metadata.sorted_tables):
        op.drop_table(table.name)
