"""phase 14 bounded scheduler worker leases

Revision ID: 0010_phase14_scheduler_worker
Revises: 0009_phase13_scheduler
Create Date: 2026-07-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_phase14_scheduler_worker"
down_revision = "0009_phase13_scheduler"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scheduler_jobs", sa.Column("lease_owner", sa.String(length=128), nullable=True))
    op.add_column("scheduler_jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("scheduler_jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("scheduler_jobs", sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("scheduler_jobs", sa.Column("max_attempts", sa.Integer, nullable=False, server_default="1"))
    op.add_column("scheduler_jobs", sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="900"))
    op.add_column("scheduler_jobs", sa.Column("last_error", sa.Text, nullable=True))
    op.create_index(
        "ix_scheduler_jobs_lease_expires",
        "scheduler_jobs",
        ["status", "lease_expires_at"],
        unique=False,
    )
    op.create_index("ix_scheduler_jobs_lease_owner", "scheduler_jobs", ["lease_owner"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_scheduler_jobs_lease_owner", table_name="scheduler_jobs")
    op.drop_index("ix_scheduler_jobs_lease_expires", table_name="scheduler_jobs")
    op.drop_column("scheduler_jobs", "last_error")
    op.drop_column("scheduler_jobs", "timeout_seconds")
    op.drop_column("scheduler_jobs", "max_attempts")
    op.drop_column("scheduler_jobs", "attempt_count")
    op.drop_column("scheduler_jobs", "heartbeat_at")
    op.drop_column("scheduler_jobs", "lease_expires_at")
    op.drop_column("scheduler_jobs", "lease_owner")
