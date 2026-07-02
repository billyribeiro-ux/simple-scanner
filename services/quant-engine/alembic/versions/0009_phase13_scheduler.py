"""phase 13 non-autonomous scheduler

Revision ID: 0009_phase13_scheduler
Revises: 0008_phase11_research
Create Date: 2026-07-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_phase13_scheduler"
down_revision = "0008_phase11_research"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduler_jobs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.String(length=96), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default="100"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("failed_reason", sa.Text),
        sa.Column("payload_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("warnings_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("research_cycle_id", sa.String(length=96)),
        sa.Column("created_by", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("job_id", name="uq_scheduler_jobs_job_id"),
    )
    op.create_index("ix_scheduler_jobs_status_scheduled", "scheduler_jobs", ["status", "scheduled_for", "priority"], unique=False)
    op.create_index("ix_scheduler_jobs_type_status", "scheduler_jobs", ["job_type", "status"], unique=False)
    op.create_index("ix_scheduler_jobs_research_cycle", "scheduler_jobs", ["research_cycle_id"], unique=False)

    op.create_table(
        "scheduler_job_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(length=96), nullable=False),
        sa.Column("job_id", sa.String(length=96), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("metadata_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("event_id", name="uq_scheduler_job_events_event_id"),
    )
    op.create_index("ix_scheduler_job_events_job_created", "scheduler_job_events", ["job_id", "created_at"], unique=False)
    op.create_index("ix_scheduler_job_events_type_created", "scheduler_job_events", ["event_type", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_scheduler_job_events_type_created", table_name="scheduler_job_events")
    op.drop_index("ix_scheduler_job_events_job_created", table_name="scheduler_job_events")
    op.drop_table("scheduler_job_events")
    op.drop_index("ix_scheduler_jobs_research_cycle", table_name="scheduler_jobs")
    op.drop_index("ix_scheduler_jobs_type_status", table_name="scheduler_jobs")
    op.drop_index("ix_scheduler_jobs_status_scheduled", table_name="scheduler_jobs")
    op.drop_table("scheduler_jobs")
