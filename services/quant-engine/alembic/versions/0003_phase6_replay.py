"""phase 6 replay persistence

Revision ID: 0003_phase6_replay
Revises: 0002_phase5_indexes
Create Date: 2026-07-01
"""

from __future__ import annotations

from alembic import op


revision = "0003_phase6_replay"
down_revision = "0002_phase5_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS replay_runs (
            replay_run_id VARCHAR(96) PRIMARY KEY,
            simulation_type VARCHAR(64) NOT NULL,
            backend VARCHAR(32) NOT NULL,
            start TIMESTAMPTZ,
            "end" TIMESTAMPTZ,
            symbols_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            intervals_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            summary_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            per_symbol_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            per_setup_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            per_regime_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            per_time_bucket_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            skip_breakdown_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS simulated_trades (
            trade_id VARCHAR(96) PRIMARY KEY,
            replay_run_id VARCHAR(96) NOT NULL,
            candidate_id VARCHAR(96),
            symbol VARCHAR(16) NOT NULL,
            interval VARCHAR(8) NOT NULL,
            side VARCHAR(16) NOT NULL,
            setup_type VARCHAR(128) NOT NULL,
            signal_timestamp_utc TIMESTAMPTZ NOT NULL,
            entry_timestamp_utc TIMESTAMPTZ,
            exit_timestamp_utc TIMESTAMPTZ,
            entry_price NUMERIC(18, 6),
            stop_price NUMERIC(18, 6),
            target_1 NUMERIC(18, 6),
            target_2 NUMERIC(18, 6),
            target_3 NUMERIC(18, 6),
            exit_price NUMERIC(18, 6),
            exit_reason VARCHAR(64),
            realized_r NUMERIC(18, 6) NOT NULL DEFAULT 0,
            mfe_r NUMERIC(18, 6) NOT NULL DEFAULT 0,
            mae_r NUMERIC(18, 6) NOT NULL DEFAULT 0,
            bars_held INTEGER NOT NULL DEFAULT 0,
            minutes_held NUMERIC(18, 6) NOT NULL DEFAULT 0,
            same_bar_ambiguous BOOLEAN NOT NULL DEFAULT false,
            ambiguity_policy VARCHAR(64),
            slippage_bps NUMERIC(18, 6) NOT NULL DEFAULT 0,
            spread_bps NUMERIC(18, 6) NOT NULL DEFAULT 0,
            commission NUMERIC(18, 6) NOT NULL DEFAULT 0,
            market_regime VARCHAR(64),
            time_bucket VARCHAR(64),
            signal_score NUMERIC(18, 6),
            expected_r NUMERIC(18, 6),
            status VARCHAR(32) NOT NULL,
            skip_reason VARCHAR(64),
            metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pipeline_build_windows (
            build_window_id VARCHAR(96) PRIMARY KEY,
            artifact_type VARCHAR(32) NOT NULL,
            symbol VARCHAR(16) NOT NULL,
            interval VARCHAR(8) NOT NULL,
            session_date DATE,
            start TIMESTAMPTZ,
            "end" TIMESTAMPTZ,
            version VARCHAR(96) NOT NULL,
            dirty BOOLEAN NOT NULL DEFAULT true,
            stale_reason VARCHAR(128),
            payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_pipeline_window UNIQUE(artifact_type, symbol, interval, session_date, version)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_replay_runs_created_type ON replay_runs(created_at, simulation_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_replay_runs_simulation_type ON replay_runs(simulation_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_simulated_trades_run_symbol_setup_side ON simulated_trades(replay_run_id, symbol, setup_type, side)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_simulated_trades_run_status ON simulated_trades(replay_run_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_simulated_trades_signal_ts ON simulated_trades(signal_timestamp_utc)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_candidate_signals_replay_lookup ON candidate_signals(symbol, interval, timestamp_utc, setup_type, side)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pipeline_windows_lookup ON pipeline_build_windows(artifact_type, symbol, interval, session_date, dirty)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_live_signals_symbol_ts_status_model ON live_signals(ticker, timestamp_utc, status, model_version)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_live_signals_symbol_ts_status_model")
    op.execute("DROP INDEX IF EXISTS ix_pipeline_windows_lookup")
    op.execute("DROP INDEX IF EXISTS ix_candidate_signals_replay_lookup")
    op.execute("DROP INDEX IF EXISTS ix_simulated_trades_signal_ts")
    op.execute("DROP INDEX IF EXISTS ix_simulated_trades_run_status")
    op.execute("DROP INDEX IF EXISTS ix_simulated_trades_run_symbol_setup_side")
    op.execute("DROP INDEX IF EXISTS ix_replay_runs_simulation_type")
    op.execute("DROP INDEX IF EXISTS ix_replay_runs_created_type")
    op.execute("DROP TABLE IF EXISTS pipeline_build_windows")
    op.execute("DROP TABLE IF EXISTS simulated_trades")
    op.execute("DROP TABLE IF EXISTS replay_runs")
