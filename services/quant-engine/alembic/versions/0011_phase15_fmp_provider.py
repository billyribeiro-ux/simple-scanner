"""phase 15 fmp provider entitlement and ingestion runs

Revision ID: 0011_phase15_fmp_provider
Revises: 0010_phase14_scheduler_worker
Create Date: 2026-07-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011_phase15_fmp_provider"
down_revision = "0010_phase14_scheduler_worker"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_capability_checks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("check_id", sa.String(length=96), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("endpoint_key", sa.String(length=64), nullable=False),
        sa.Column("endpoint_category", sa.String(length=64), nullable=False),
        sa.Column("symbol_scope_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("request_type", sa.String(length=32), server_default="REST", nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_class", sa.String(length=128), nullable=True),
        sa.Column("response_shape_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("sample_symbol", sa.String(length=16), nullable=True),
        sa.Column("sample_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("entitlement_notes_json", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("check_id", name="uq_provider_capability_checks_check_id"),
    )
    op.create_index("ix_provider_capability_checks_check_id", "provider_capability_checks", ["check_id"], unique=False)
    op.create_index("ix_provider_capability_checks_endpoint_key", "provider_capability_checks", ["endpoint_key"], unique=False)
    op.create_index(
        "ix_provider_capability_checks_endpoint_checked",
        "provider_capability_checks",
        ["provider", "endpoint_key", "checked_at"],
        unique=False,
    )
    op.create_index("ix_provider_capability_checks_provider", "provider_capability_checks", ["provider"], unique=False)
    op.create_index("ix_provider_capability_checks_status", "provider_capability_checks", ["status", "checked_at"], unique=False)

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ingestion_run_id", sa.String(length=96), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("ingestion_type", sa.String(length=64), nullable=False),
        sa.Column("symbols_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("intervals_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("records_fetched", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("records_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("provider_request_ids_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("dirty_windows_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("errors_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("warnings_json", sa.JSON(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ingestion_run_id", name="uq_ingestion_runs_run_id"),
    )
    op.create_index("ix_ingestion_runs_ingestion_run_id", "ingestion_runs", ["ingestion_run_id"], unique=False)
    op.create_index("ix_ingestion_runs_provider", "ingestion_runs", ["provider"], unique=False)
    op.create_index("ix_ingestion_runs_ingestion_type", "ingestion_runs", ["ingestion_type"], unique=False)
    op.create_index(
        "ix_ingestion_runs_provider_type_created",
        "ingestion_runs",
        ["provider", "ingestion_type", "created_at"],
        unique=False,
    )
    op.create_index("ix_ingestion_runs_status_created", "ingestion_runs", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ingestion_runs_status_created", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_provider_type_created", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_ingestion_type", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_provider", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_ingestion_run_id", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
    op.drop_index("ix_provider_capability_checks_status", table_name="provider_capability_checks")
    op.drop_index("ix_provider_capability_checks_provider", table_name="provider_capability_checks")
    op.drop_index("ix_provider_capability_checks_endpoint_checked", table_name="provider_capability_checks")
    op.drop_index("ix_provider_capability_checks_endpoint_key", table_name="provider_capability_checks")
    op.drop_index("ix_provider_capability_checks_check_id", table_name="provider_capability_checks")
    op.drop_table("provider_capability_checks")
