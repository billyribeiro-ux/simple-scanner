"""phase 16 fmp review snapshots and freshness

Revision ID: 0012_phase16_fmp_freshness
Revises: 0011_phase15_fmp_provider
Create Date: 2026-07-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012_phase16_fmp_freshness"
down_revision = "0011_phase15_fmp_provider"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "provider_capability_checks",
        sa.Column("operator_review_status", sa.String(length=32), server_default="UNREVIEWED", nullable=False),
    )
    op.add_column("provider_capability_checks", sa.Column("reviewed_by", sa.String(length=128), nullable=True))
    op.add_column("provider_capability_checks", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("provider_capability_checks", sa.Column("review_notes", sa.Text(), nullable=True))
    op.create_index(
        "ix_provider_capability_checks_review",
        "provider_capability_checks",
        ["provider", "operator_review_status", "checked_at"],
        unique=False,
    )

    op.create_table(
        "quote_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("quote_snapshot_id", sa.String(length=96), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("endpoint_key", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_timestamp", sa.String(length=64), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("bid", sa.Float(), nullable=True),
        sa.Column("ask", sa.Float(), nullable=True),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("previous_close", sa.Float(), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("change", sa.Float(), nullable=True),
        sa.Column("change_percent", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), server_default="fmp", nullable=False),
        sa.Column("ingestion_run_id", sa.String(length=96), nullable=True),
        sa.Column("provider_request_id", sa.String(length=96), nullable=True),
        sa.Column("raw_fields_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("data_quality_flags_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "endpoint_key", "symbol", "timestamp_utc", name="uq_quote_snapshots_provider_symbol_ts"),
        sa.UniqueConstraint("quote_snapshot_id", name="uq_quote_snapshots_snapshot_id"),
    )
    op.create_index("ix_quote_snapshots_quote_snapshot_id", "quote_snapshots", ["quote_snapshot_id"], unique=False)
    op.create_index("ix_quote_snapshots_provider", "quote_snapshots", ["provider"], unique=False)
    op.create_index("ix_quote_snapshots_endpoint_key", "quote_snapshots", ["endpoint_key"], unique=False)
    op.create_index("ix_quote_snapshots_symbol", "quote_snapshots", ["symbol"], unique=False)
    op.create_index("ix_quote_snapshots_timestamp_utc", "quote_snapshots", ["timestamp_utc"], unique=False)
    op.create_index("ix_quote_snapshots_symbol_timestamp", "quote_snapshots", ["symbol", "timestamp_utc"], unique=False)
    op.create_index(
        "ix_quote_snapshots_provider_endpoint",
        "quote_snapshots",
        ["provider", "endpoint_key", "timestamp_utc"],
        unique=False,
    )

    op.create_table(
        "data_freshness_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("freshness_report_id", sa.String(length=96), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("symbols_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("intervals_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("required_capability_endpoints_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("latest_bars_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("latest_quotes_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("missing_items_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("stale_items_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("dirty_windows_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("capability_summary_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("warnings_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("recommendations_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("max_bar_age_minutes_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("max_quote_age_seconds", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("freshness_report_id", name="uq_data_freshness_reports_report_id"),
    )
    op.create_index("ix_data_freshness_reports_freshness_report_id", "data_freshness_reports", ["freshness_report_id"], unique=False)
    op.create_index("ix_data_freshness_reports_provider", "data_freshness_reports", ["provider"], unique=False)
    op.create_index("ix_data_freshness_reports_status", "data_freshness_reports", ["status"], unique=False)
    op.create_index("ix_data_freshness_reports_generated_at", "data_freshness_reports", ["generated_at"], unique=False)
    op.create_index(
        "ix_data_freshness_reports_status_generated",
        "data_freshness_reports",
        ["status", "generated_at"],
        unique=False,
    )
    op.create_index(
        "ix_data_freshness_reports_provider_generated",
        "data_freshness_reports",
        ["provider", "generated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_data_freshness_reports_provider_generated", table_name="data_freshness_reports")
    op.drop_index("ix_data_freshness_reports_status_generated", table_name="data_freshness_reports")
    op.drop_index("ix_data_freshness_reports_generated_at", table_name="data_freshness_reports")
    op.drop_index("ix_data_freshness_reports_status", table_name="data_freshness_reports")
    op.drop_index("ix_data_freshness_reports_provider", table_name="data_freshness_reports")
    op.drop_index("ix_data_freshness_reports_freshness_report_id", table_name="data_freshness_reports")
    op.drop_table("data_freshness_reports")
    op.drop_index("ix_quote_snapshots_provider_endpoint", table_name="quote_snapshots")
    op.drop_index("ix_quote_snapshots_symbol_timestamp", table_name="quote_snapshots")
    op.drop_index("ix_quote_snapshots_timestamp_utc", table_name="quote_snapshots")
    op.drop_index("ix_quote_snapshots_symbol", table_name="quote_snapshots")
    op.drop_index("ix_quote_snapshots_endpoint_key", table_name="quote_snapshots")
    op.drop_index("ix_quote_snapshots_provider", table_name="quote_snapshots")
    op.drop_index("ix_quote_snapshots_quote_snapshot_id", table_name="quote_snapshots")
    op.drop_table("quote_snapshots")
    op.drop_index("ix_provider_capability_checks_review", table_name="provider_capability_checks")
    op.drop_column("provider_capability_checks", "review_notes")
    op.drop_column("provider_capability_checks", "reviewed_at")
    op.drop_column("provider_capability_checks", "reviewed_by")
    op.drop_column("provider_capability_checks", "operator_review_status")
