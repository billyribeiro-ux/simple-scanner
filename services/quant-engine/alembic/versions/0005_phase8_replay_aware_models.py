"""phase 8 replay aware model evidence

Revision ID: 0005_phase8_replay_aware_models
Revises: 0004_phase7_audit
Create Date: 2026-07-01
"""

from __future__ import annotations

from alembic import op


revision = "0005_phase8_replay_aware_models"
down_revision = "0004_phase7_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS model_evidence_cells (
            id VARCHAR(96) PRIMARY KEY,
            model_version VARCHAR(128) NOT NULL,
            cell_key VARCHAR(512) NOT NULL,
            dimensions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            hierarchy_level VARCHAR(64) NOT NULL,
            parent_cell_key VARCHAR(512),
            metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            sample_size INTEGER NOT NULL DEFAULT 0,
            observed_outcome_count INTEGER NOT NULL DEFAULT 0,
            average_r NUMERIC(18, 6) NOT NULL DEFAULT 0,
            median_r NUMERIC(18, 6) NOT NULL DEFAULT 0,
            profit_factor NUMERIC(18, 6) NOT NULL DEFAULT 0,
            max_drawdown_r NUMERIC(18, 6) NOT NULL DEFAULT 0,
            robustness_score NUMERIC(18, 6),
            fragility_flags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            evidence_quality_grade VARCHAR(32) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_model_evidence_cell_key UNIQUE(model_version, cell_key)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_score_audits (
            id VARCHAR(96) PRIMARY KEY,
            score_id VARCHAR(96) NOT NULL UNIQUE,
            model_version VARCHAR(128) NOT NULL,
            candidate_id VARCHAR(96),
            symbol VARCHAR(16) NOT NULL,
            interval VARCHAR(8) NOT NULL,
            timestamp_utc TIMESTAMPTZ NOT NULL,
            side VARCHAR(16) NOT NULL,
            setup_type VARCHAR(128) NOT NULL,
            signal_quality_score NUMERIC(18, 6) NOT NULL DEFAULT 0,
            grade VARCHAR(16) NOT NULL,
            action VARCHAR(16) NOT NULL,
            expected_r_estimate NUMERIC(18, 6) NOT NULL DEFAULT 0,
            score_components_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            suppression_reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            evidence_cell_keys_used_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            warnings_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            payload_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_evidence_cells_model_level ON model_evidence_cells(model_version, hierarchy_level)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_evidence_cells_cell_key ON model_evidence_cells(cell_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_score_audits_model_created ON candidate_score_audits(model_version, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_score_audits_symbol_ts ON candidate_score_audits(symbol, timestamp_utc)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_score_audits_score_id ON candidate_score_audits(score_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_score_audits_score_id")
    op.execute("DROP INDEX IF EXISTS ix_score_audits_symbol_ts")
    op.execute("DROP INDEX IF EXISTS ix_score_audits_model_created")
    op.execute("DROP INDEX IF EXISTS ix_model_evidence_cells_cell_key")
    op.execute("DROP INDEX IF EXISTS ix_model_evidence_cells_model_level")
    op.execute("DROP TABLE IF EXISTS candidate_score_audits")
    op.execute("DROP TABLE IF EXISTS model_evidence_cells")
