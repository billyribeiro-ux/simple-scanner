"""phase 11 research governance lifecycle."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0008_phase11_research"
down_revision = "0007_phase10_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_cycles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("research_cycle_id", sa.String(96), nullable=False),
        sa.Column("cycle_date", sa.Date, nullable=False),
        sa.Column("cycle_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("symbols_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("intervals_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("start", sa.DateTime(timezone=True)),
        sa.Column("end", sa.DateTime(timezone=True)),
        sa.Column("session", sa.String(32), nullable=False, server_default="rth"),
        sa.Column("data_cutoff_timestamp", sa.DateTime(timezone=True)),
        sa.Column("active_model_version", sa.String(128)),
        sa.Column("challenger_model_version", sa.String(128)),
        sa.Column("window_set_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("replay_run_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("counterfactual_replay_run_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("portfolio_replay_run_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("sensitivity_run_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("calibration_audit_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("drift_report_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("model_review_report_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("comparison_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("proposal_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("data_quality_report_id", sa.String(96)),
        sa.Column("stale_window_status_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("summary_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("warnings_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("config_hash", sa.String(64)),
        sa.Column("input_fingerprint", sa.String(64)),
        sa.Column("git_commit", sa.String(64)),
        sa.Column("database_revision", sa.String(64)),
        sa.Column("persistence_backend", sa.String(32)),
        sa.Column("failed_reason", sa.Text),
        sa.Column("payload_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("research_cycle_id", name="uq_research_cycles_cycle_id"),
    )
    op.create_index("ix_research_cycles_cycle_date", "research_cycles", ["cycle_date"], unique=False)
    op.create_index("ix_research_cycles_status_created", "research_cycles", ["status", "created_at"], unique=False)

    op.create_table(
        "research_cycle_artifacts",
        sa.Column("cycle_artifact_id", sa.String(96), primary_key=True),
        sa.Column("research_cycle_id", sa.String(96), nullable=False),
        sa.Column("artifact_type", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(128)),
        sa.Column("source_table", sa.String(64)),
        sa.Column("export_id", sa.String(96)),
        sa.Column("payload_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_research_cycle_artifacts_cycle", "research_cycle_artifacts", ["research_cycle_id", "artifact_type"], unique=False)

    op.create_table(
        "champion_challenger_comparisons",
        sa.Column("comparison_id", sa.String(96), primary_key=True),
        sa.Column("champion_model_version", sa.String(128)),
        sa.Column("challenger_model_version", sa.String(128)),
        sa.Column("delta_metrics_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("challenger_better_flags_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("challenger_worse_flags_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("gate_results_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("recommended_action", sa.String(64), nullable=False),
        sa.Column("readiness_status", sa.String(32), nullable=False),
        sa.Column("warnings_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("payload_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_champion_challenger_comparisons_created",
        "champion_challenger_comparisons",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "model_proposals",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("proposal_id", sa.String(96), nullable=False),
        sa.Column("research_cycle_id", sa.String(96)),
        sa.Column("proposal_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("champion_model_version", sa.String(128)),
        sa.Column("challenger_model_version", sa.String(128)),
        sa.Column("recommended_action", sa.String(64), nullable=False),
        sa.Column("readiness_status", sa.String(32), nullable=False),
        sa.Column("validation_report_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("calibration_audit_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("drift_report_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("model_review_report_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("comparison_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("replay_run_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("window_set_ids_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evidence_summary_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("champion_metrics_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("challenger_metrics_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("delta_metrics_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("pass_fail_gates_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("rejection_reasons_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("approval_required", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("approved_by", sa.String(128)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("activation_model_version", sa.String(128)),
        sa.Column("activation_id", sa.String(96)),
        sa.Column("payload_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("proposal_id", name="uq_model_proposals_proposal_id"),
    )
    op.create_index("ix_model_proposals_status_created", "model_proposals", ["status", "created_at"], unique=False)
    op.create_index("ix_model_proposals_cycle", "model_proposals", ["research_cycle_id"], unique=False)

    op.create_table(
        "model_decision_ledger",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("decision_id", sa.String(96), nullable=False),
        sa.Column("decision_type", sa.String(64), nullable=False),
        sa.Column("research_cycle_id", sa.String(96)),
        sa.Column("proposal_id", sa.String(96)),
        sa.Column("model_version", sa.String(128)),
        sa.Column("previous_model_version", sa.String(128)),
        sa.Column("decision_status", sa.String(32), nullable=False),
        sa.Column("reason_codes_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evidence_refs_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("actor", sa.String(128)),
        sa.Column("metadata_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("payload_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("decision_id", name="uq_model_decision_ledger_decision_id"),
    )
    op.create_index("ix_model_decision_ledger_type_created", "model_decision_ledger", ["decision_type", "created_at"], unique=False)
    op.create_index("ix_model_decision_ledger_cycle", "model_decision_ledger", ["research_cycle_id"], unique=False)
    op.create_index("ix_model_decision_ledger_proposal", "model_decision_ledger", ["proposal_id"], unique=False)
    op.create_index("ix_model_decision_ledger_model", "model_decision_ledger", ["model_version"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_model_decision_ledger_model", table_name="model_decision_ledger")
    op.drop_index("ix_model_decision_ledger_proposal", table_name="model_decision_ledger")
    op.drop_index("ix_model_decision_ledger_cycle", table_name="model_decision_ledger")
    op.drop_index("ix_model_decision_ledger_type_created", table_name="model_decision_ledger")
    op.drop_table("model_decision_ledger")
    op.drop_index("ix_model_proposals_cycle", table_name="model_proposals")
    op.drop_index("ix_model_proposals_status_created", table_name="model_proposals")
    op.drop_table("model_proposals")
    op.drop_index("ix_champion_challenger_comparisons_created", table_name="champion_challenger_comparisons")
    op.drop_table("champion_challenger_comparisons")
    op.drop_index("ix_research_cycle_artifacts_cycle", table_name="research_cycle_artifacts")
    op.drop_table("research_cycle_artifacts")
    op.drop_index("ix_research_cycles_status_created", table_name="research_cycles")
    op.drop_index("ix_research_cycles_cycle_date", table_name="research_cycles")
    op.drop_table("research_cycles")
