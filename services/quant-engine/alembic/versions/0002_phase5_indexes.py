"""phase 5 repository runtime indexes

Revision ID: 0002_phase5_indexes
Revises: 0001_initial
Create Date: 2026-07-01
"""

from __future__ import annotations

from alembic import op


revision = "0002_phase5_indexes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_features_lookup_version",
        "features",
        ["symbol", "interval", "timestamp_utc", "feature_set_version"],
        unique=False,
    )
    op.create_index(
        "ix_labels_symbol_ts_setup_side_outcome",
        "labels",
        ["symbol", "timestamp_utc", "setup_type", "side", "outcome"],
        unique=False,
    )
    op.create_index(
        "ix_live_signals_ticker_ts_status",
        "live_signals",
        ["ticker", "timestamp_utc", "status"],
        unique=False,
    )
    op.create_index(
        "ix_validation_reports_model_purpose_created",
        "validation_reports",
        ["model_version", "purpose", "created_at"],
        unique=False,
    )
    op.create_index("ix_scanner_runs_started", "scanner_runs", ["started_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_scanner_runs_started", table_name="scanner_runs")
    op.drop_index("ix_validation_reports_model_purpose_created", table_name="validation_reports")
    op.drop_index("ix_live_signals_ticker_ts_status", table_name="live_signals")
    op.drop_index("ix_labels_symbol_ts_setup_side_outcome", table_name="labels")
    op.drop_index("ix_features_lookup_version", table_name="features")
