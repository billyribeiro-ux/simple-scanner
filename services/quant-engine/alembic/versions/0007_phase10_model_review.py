"""phase 10 model review and replay windows

Revision ID: 0007_phase10_review
Revises: 0006_phase9_calibration
Create Date: 2026-07-01
"""

from __future__ import annotations

from alembic import op


revision = "0007_phase10_review"
down_revision = "0006_phase9_calibration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS replay_window_sets (
            window_set_id VARCHAR(96) PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            description TEXT,
            symbols_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            intervals_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            setup_types_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            start TIMESTAMPTZ,
            "end" TIMESTAMPTZ,
            window_mode VARCHAR(32) NOT NULL,
            window_size_days INTEGER,
            step_days INTEGER,
            embargo_minutes INTEGER,
            session VARCHAR(32) NOT NULL DEFAULT 'rth',
            replay_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            sensitivity_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            validation_config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            status VARCHAR(32) NOT NULL,
            warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS replay_window_results (
            window_result_id VARCHAR(96) PRIMARY KEY,
            window_set_id VARCHAR(96) NOT NULL,
            window_index INTEGER NOT NULL,
            train_start TIMESTAMPTZ,
            train_end TIMESTAMPTZ,
            validation_start TIMESTAMPTZ,
            validation_end TIMESTAMPTZ,
            test_start TIMESTAMPTZ,
            test_end TIMESTAMPTZ,
            replay_start TIMESTAMPTZ,
            replay_end TIMESTAMPTZ,
            replay_run_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            counterfactual_replay_run_id VARCHAR(96),
            portfolio_replay_run_id VARCHAR(96),
            sensitivity_run_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            calibration_audit_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            comparison_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            model_versions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            status VARCHAR(32) NOT NULL,
            metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS model_calibration_drift_reports (
            drift_report_id VARCHAR(96) PRIMARY KEY,
            model_version VARCHAR(128) NOT NULL,
            calibration_audit_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            window_result_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            replay_run_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            score_bin_drift_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            grade_bin_drift_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            action_bin_drift_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            stability_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            drift_flags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            severity VARCHAR(32) NOT NULL,
            warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS model_calibration_drift_windows (
            id VARCHAR(96) PRIMARY KEY,
            drift_report_id VARCHAR(96) NOT NULL,
            window_result_id VARCHAR(96),
            window_index INTEGER NOT NULL,
            metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            flags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            severity VARCHAR(32) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS model_review_reports (
            review_report_id VARCHAR(96) PRIMARY KEY,
            model_version VARCHAR(128) NOT NULL,
            window_set_id VARCHAR(96),
            validation_report_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            calibration_audit_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            drift_report_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            sensitivity_run_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            comparison_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            readiness_status VARCHAR(32) NOT NULL,
            readiness_reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            unresolved_warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_replay_window_sets_status_created ON replay_window_sets(status, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_replay_window_results_set_index ON replay_window_results(window_set_id, window_index)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_drift_reports_model_created ON model_calibration_drift_reports(model_version, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_drift_windows_report_index ON model_calibration_drift_windows(drift_report_id, window_index)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_review_reports_model_created ON model_review_reports(model_version, created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_model_review_reports_model_created")
    op.execute("DROP INDEX IF EXISTS ix_drift_windows_report_index")
    op.execute("DROP INDEX IF EXISTS ix_drift_reports_model_created")
    op.execute("DROP INDEX IF EXISTS ix_replay_window_results_set_index")
    op.execute("DROP INDEX IF EXISTS ix_replay_window_sets_status_created")
    op.execute("DROP TABLE IF EXISTS model_review_reports")
    op.execute("DROP TABLE IF EXISTS model_calibration_drift_windows")
    op.execute("DROP TABLE IF EXISTS model_calibration_drift_reports")
    op.execute("DROP TABLE IF EXISTS replay_window_results")
    op.execute("DROP TABLE IF EXISTS replay_window_sets")
