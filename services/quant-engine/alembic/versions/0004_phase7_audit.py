"""phase 7 replay audit sensitivity

Revision ID: 0004_phase7_audit
Revises: 0003_phase6_replay
Create Date: 2026-07-01
"""

from __future__ import annotations

from alembic import op


revision = "0004_phase7_audit"
down_revision = "0003_phase6_replay"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE replay_runs ADD COLUMN IF NOT EXISTS config_hash VARCHAR(64)")
    op.execute("ALTER TABLE replay_runs ADD COLUMN IF NOT EXISTS input_fingerprint VARCHAR(64)")
    op.execute("ALTER TABLE replay_runs ADD COLUMN IF NOT EXISTS candidate_fingerprint VARCHAR(64)")
    op.execute("ALTER TABLE replay_runs ADD COLUMN IF NOT EXISTS replay_config_version VARCHAR(64)")
    op.execute("ALTER TABLE replay_runs ADD COLUMN IF NOT EXISTS feature_set_version VARCHAR(64)")
    op.execute("ALTER TABLE replay_runs ADD COLUMN IF NOT EXISTS candidate_config_version VARCHAR(64)")
    op.execute("ALTER TABLE replay_runs ADD COLUMN IF NOT EXISTS label_config_version VARCHAR(64)")
    op.execute("ALTER TABLE replay_runs ADD COLUMN IF NOT EXISTS stale_window_status_json JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("CREATE INDEX IF NOT EXISTS ix_replay_runs_config_hash ON replay_runs(config_hash)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS replay_sensitivity_runs (
            sensitivity_run_id VARCHAR(96) PRIMARY KEY,
            replay_run_id VARCHAR(96) NOT NULL,
            config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            gate_results_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            fragility_flags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS replay_sensitivity_scenarios (
            scenario_id VARCHAR(96) PRIMARY KEY,
            sensitivity_run_id VARCHAR(96) NOT NULL,
            replay_run_id VARCHAR(96) NOT NULL,
            slippage_bps NUMERIC(18, 6) NOT NULL,
            spread_bps NUMERIC(18, 6) NOT NULL,
            intrabar_path_policy VARCHAR(64) NOT NULL,
            same_bar_stop_target_policy VARCHAR(64) NOT NULL,
            summary_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            gate_results_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS backtest_comparisons (
            comparison_id VARCHAR(96) PRIMARY KEY,
            label_run_id VARCHAR(96),
            replay_run_id VARCHAR(96) NOT NULL,
            comparison_type VARCHAR(64) NOT NULL,
            summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_sensitivity_runs_replay_created ON replay_sensitivity_runs(replay_run_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sensitivity_scenarios_run_cost ON replay_sensitivity_scenarios(sensitivity_run_id, slippage_bps, spread_bps)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_backtest_comparisons_replay_created ON backtest_comparisons(replay_run_id, created_at)")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                BEGIN
                    ALTER TABLE bars DROP CONSTRAINT IF EXISTS bars_pkey;
                    ALTER TABLE bars ADD CONSTRAINT bars_pkey PRIMARY KEY (id, timestamp_utc);
                    PERFORM create_hypertable('bars', 'timestamp_utc', if_not_exists => TRUE, migrate_data => TRUE);
                EXCEPTION WHEN OTHERS THEN
                    RAISE NOTICE 'bars hypertable not created: %', SQLERRM;
                END;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_backtest_comparisons_replay_created")
    op.execute("DROP INDEX IF EXISTS ix_sensitivity_scenarios_run_cost")
    op.execute("DROP INDEX IF EXISTS ix_sensitivity_runs_replay_created")
    op.execute("DROP INDEX IF EXISTS ix_replay_runs_config_hash")
    op.execute("DROP TABLE IF EXISTS backtest_comparisons")
    op.execute("DROP TABLE IF EXISTS replay_sensitivity_scenarios")
    op.execute("DROP TABLE IF EXISTS replay_sensitivity_runs")
    op.execute("ALTER TABLE replay_runs DROP COLUMN IF EXISTS stale_window_status_json")
    op.execute("ALTER TABLE replay_runs DROP COLUMN IF EXISTS label_config_version")
    op.execute("ALTER TABLE replay_runs DROP COLUMN IF EXISTS candidate_config_version")
    op.execute("ALTER TABLE replay_runs DROP COLUMN IF EXISTS feature_set_version")
    op.execute("ALTER TABLE replay_runs DROP COLUMN IF EXISTS replay_config_version")
    op.execute("ALTER TABLE replay_runs DROP COLUMN IF EXISTS candidate_fingerprint")
    op.execute("ALTER TABLE replay_runs DROP COLUMN IF EXISTS input_fingerprint")
    op.execute("ALTER TABLE replay_runs DROP COLUMN IF EXISTS config_hash")
