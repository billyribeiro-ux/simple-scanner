"""phase 9 counterfactual calibration

Revision ID: 0006_phase9_calibration
Revises: 0005_phase8_replay_aware_models
Create Date: 2026-07-01
"""

from __future__ import annotations

from alembic import op


revision = "0006_phase9_calibration"
down_revision = "0005_phase8_replay_aware_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS model_calibration_audits (
            id VARCHAR(96) PRIMARY KEY,
            calibration_audit_id VARCHAR(96) NOT NULL UNIQUE,
            model_version VARCHAR(128) NOT NULL,
            validation_report_id VARCHAR(96),
            replay_run_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            outcome_source VARCHAR(64) NOT NULL,
            score_bins_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            grade_bins_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            action_bins_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            rank_correlation_score NUMERIC(18, 6) NOT NULL DEFAULT 0,
            monotonicity_pass BOOLEAN NOT NULL DEFAULT false,
            separation_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            stability_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            rejection_reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS model_calibration_bins (
            id VARCHAR(96) PRIMARY KEY,
            calibration_audit_id VARCHAR(96) NOT NULL,
            bin_type VARCHAR(32) NOT NULL,
            bin_key VARCHAR(64) NOT NULL,
            sample_size INTEGER NOT NULL DEFAULT 0,
            observed_average_r NUMERIC(18, 6) NOT NULL DEFAULT 0,
            observed_win_rate NUMERIC(18, 6) NOT NULL DEFAULT 0,
            profit_factor NUMERIC(18, 6) NOT NULL DEFAULT 0,
            max_drawdown_r NUMERIC(18, 6) NOT NULL DEFAULT 0,
            metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS model_comparisons (
            comparison_id VARCHAR(96) PRIMARY KEY,
            comparison_type VARCHAR(64) NOT NULL,
            model_versions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            validation_report_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            calibration_audit_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            replay_run_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_calibration_audits_model_created ON model_calibration_audits(model_version, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_calibration_audits_audit_id ON model_calibration_audits(calibration_audit_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_calibration_bins_audit_type ON model_calibration_bins(calibration_audit_id, bin_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_comparisons_created ON model_comparisons(created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_model_comparisons_created")
    op.execute("DROP INDEX IF EXISTS ix_calibration_bins_audit_type")
    op.execute("DROP INDEX IF EXISTS ix_calibration_audits_audit_id")
    op.execute("DROP INDEX IF EXISTS ix_calibration_audits_model_created")
    op.execute("DROP TABLE IF EXISTS model_comparisons")
    op.execute("DROP TABLE IF EXISTS model_calibration_bins")
    op.execute("DROP TABLE IF EXISTS model_calibration_audits")
