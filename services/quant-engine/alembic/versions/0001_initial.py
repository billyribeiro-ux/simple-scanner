"""initial persistence schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

BASELINE_METADATA = sa.MetaData()


def utc_created_updated() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


symbols = sa.Table(
    "symbols",
    BASELINE_METADATA,
    sa.Column("symbol", sa.String(16), primary_key=True),
    sa.Column("name", sa.String(255)),
    sa.Column("exchange", sa.String(64)),
    sa.Column("asset_type", sa.String(32), nullable=False, server_default="equity"),
    sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    sa.Column("provider", sa.String(32), nullable=False, server_default="fmp"),
    sa.Column("metadata_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
    *utc_created_updated(),
)

bars = sa.Table(
    "bars",
    BASELINE_METADATA,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("symbol", sa.String(16), nullable=False),
    sa.Column("interval", sa.String(8), nullable=False),
    sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
    sa.Column("timestamp_et", sa.DateTime(timezone=True)),
    sa.Column("session_date", sa.Date),
    sa.Column("open", sa.Numeric(18, 6), nullable=False),
    sa.Column("high", sa.Numeric(18, 6), nullable=False),
    sa.Column("low", sa.Numeric(18, 6), nullable=False),
    sa.Column("close", sa.Numeric(18, 6), nullable=False),
    sa.Column("volume", sa.BigInteger, nullable=False),
    sa.Column("vwap", sa.Numeric(18, 6)),
    sa.Column("source", sa.String(64), nullable=False),
    sa.Column("quality_flags_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("payload_json", sa.JSON, nullable=False),
    *utc_created_updated(),
    sa.UniqueConstraint("symbol", "interval", "timestamp_utc", "source", name="uq_bars_symbol_interval_ts_source"),
)

features = sa.Table(
    "features",
    BASELINE_METADATA,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("symbol", sa.String(16), nullable=False),
    sa.Column("interval", sa.String(8), nullable=False),
    sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
    sa.Column("session_date", sa.Date),
    sa.Column("feature_set_version", sa.String(64), nullable=False),
    sa.Column("market_regime", sa.String(64)),
    sa.Column("ticker_regime", sa.String(64)),
    sa.Column("data_quality_flags_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("payload_json", sa.JSON, nullable=False),
    *utc_created_updated(),
    sa.UniqueConstraint("symbol", "interval", "timestamp_utc", "feature_set_version", name="uq_features_symbol_interval_ts_version"),
)

candidate_signals = sa.Table(
    "candidate_signals",
    BASELINE_METADATA,
    sa.Column("candidate_id", sa.String(64), primary_key=True),
    sa.Column("symbol", sa.String(16), nullable=False),
    sa.Column("interval", sa.String(8), nullable=False),
    sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
    sa.Column("side", sa.String(16), nullable=False),
    sa.Column("setup_type", sa.String(128), nullable=False),
    sa.Column("reason_codes_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("warning_codes_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("payload_json", sa.JSON, nullable=False),
    *utc_created_updated(),
    sa.UniqueConstraint("symbol", "interval", "timestamp_utc", "side", "setup_type", name="uq_candidate_signal_key"),
)

labels = sa.Table(
    "labels",
    BASELINE_METADATA,
    sa.Column("label_id", sa.String(64), primary_key=True),
    sa.Column("symbol", sa.String(16), nullable=False),
    sa.Column("interval", sa.String(8), nullable=False),
    sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
    sa.Column("side", sa.String(16), nullable=False),
    sa.Column("setup_type", sa.String(128), nullable=False),
    sa.Column("label_config_version", sa.String(64), nullable=False),
    sa.Column("entry_price", sa.Numeric(18, 6), nullable=False),
    sa.Column("stop_price", sa.Numeric(18, 6), nullable=False),
    sa.Column("target_1", sa.Numeric(18, 6), nullable=False),
    sa.Column("target_2", sa.Numeric(18, 6), nullable=False),
    sa.Column("target_3", sa.Numeric(18, 6), nullable=False),
    sa.Column("realized_r", sa.Numeric(18, 6), nullable=False),
    sa.Column("outcome", sa.String(16), nullable=False),
    sa.Column("market_regime", sa.String(64)),
    sa.Column("exit_timestamp_utc", sa.DateTime(timezone=True)),
    sa.Column("payload_json", sa.JSON, nullable=False),
    *utc_created_updated(),
    sa.UniqueConstraint("symbol", "interval", "timestamp_utc", "side", "setup_type", "label_config_version", name="uq_label_key"),
)

validation_reports = sa.Table(
    "validation_reports",
    BASELINE_METADATA,
    sa.Column("report_id", sa.String(64), primary_key=True),
    sa.Column("model_version", sa.String(128)),
    sa.Column("purpose", sa.String(32), nullable=False, server_default="validation"),
    sa.Column("activation_decision", sa.String(32), nullable=False),
    sa.Column("rejection_reasons_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("summary_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("per_symbol_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("per_setup_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("per_regime_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("leakage_warnings_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("payload_json", sa.JSON, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
)

validation_windows = sa.Table(
    "validation_windows",
    BASELINE_METADATA,
    sa.Column("window_id", sa.String(64), primary_key=True),
    sa.Column("report_id", sa.String(64), nullable=False),
    sa.Column("window_name", sa.String(64), nullable=False),
    sa.Column("train_start", sa.DateTime(timezone=True)),
    sa.Column("train_end", sa.DateTime(timezone=True)),
    sa.Column("validation_start", sa.DateTime(timezone=True)),
    sa.Column("validation_end", sa.DateTime(timezone=True)),
    sa.Column("test_start", sa.DateTime(timezone=True)),
    sa.Column("test_end", sa.DateTime(timezone=True)),
    sa.Column("accepted", sa.Boolean, nullable=False, server_default=sa.text("false")),
    sa.Column("metrics_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("rejection_reasons_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("payload_json", sa.JSON, nullable=False),
)

model_runs = sa.Table(
    "model_runs",
    BASELINE_METADATA,
    sa.Column("model_version", sa.String(128), primary_key=True),
    sa.Column("model_type", sa.String(64), nullable=False),
    sa.Column("feature_set_version", sa.String(64)),
    sa.Column("label_config_version", sa.String(64)),
    sa.Column("training_start", sa.DateTime(timezone=True)),
    sa.Column("training_end", sa.DateTime(timezone=True)),
    sa.Column("activation_decision", sa.String(32), nullable=False),
    sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("false")),
    sa.Column("metrics_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("validation_metrics_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("payload_json", sa.JSON, nullable=False),
    sa.Column("artifact_path", sa.Text),
    sa.Column("code_version", sa.String(64)),
    *utc_created_updated(),
)

model_artifacts = sa.Table(
    "model_artifacts",
    BASELINE_METADATA,
    sa.Column("artifact_id", sa.String(64), primary_key=True),
    sa.Column("model_version", sa.String(128), nullable=False),
    sa.Column("artifact_type", sa.String(64), nullable=False),
    sa.Column("path", sa.Text, nullable=False),
    sa.Column("sha256", sa.String(64)),
    sa.Column("payload_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
)

active_models = sa.Table(
    "active_models",
    BASELINE_METADATA,
    sa.Column("active_model_id", sa.String(64), primary_key=True),
    sa.Column("model_version", sa.String(128), nullable=False),
    sa.Column("model_type", sa.String(64), nullable=False),
    sa.Column("strategy_scope", sa.String(64), nullable=False, server_default="default"),
    sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    sa.Column("validation_report_id", sa.String(64)),
    sa.Column("payload_json", sa.JSON, nullable=False),
    sa.UniqueConstraint("model_type", "strategy_scope", name="uq_active_models_type_scope"),
)

live_signals = sa.Table(
    "live_signals",
    BASELINE_METADATA,
    sa.Column("signal_id", sa.String(64), primary_key=True),
    sa.Column("scanner_run_id", sa.String(64)),
    sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
    sa.Column("ticker", sa.String(16), nullable=False),
    sa.Column("side", sa.String(16), nullable=False),
    sa.Column("setup_type", sa.String(128), nullable=False),
    sa.Column("confidence_score", sa.Numeric(10, 6), nullable=False),
    sa.Column("expected_r", sa.Numeric(18, 6), nullable=False),
    sa.Column("model_version", sa.String(128), nullable=False),
    sa.Column("status", sa.String(32), nullable=False),
    sa.Column("payload_json", sa.JSON, nullable=False),
    *utc_created_updated(),
)

closed_signals = sa.Table(
    "closed_signals",
    BASELINE_METADATA,
    sa.Column("signal_id", sa.String(64), primary_key=True),
    sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("exit_price", sa.Numeric(18, 6)),
    sa.Column("exit_reason", sa.String(128)),
    sa.Column("realized_r", sa.Numeric(18, 6)),
    sa.Column("payload_json", sa.JSON, nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
)

scanner_runs = sa.Table(
    "scanner_runs",
    BASELINE_METADATA,
    sa.Column("scanner_run_id", sa.String(64), primary_key=True),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("stopped_at", sa.DateTime(timezone=True)),
    sa.Column("status", sa.String(32), nullable=False),
    sa.Column("symbols_json", sa.JSON, nullable=False, server_default=sa.text("'[]'::jsonb")),
    sa.Column("confidence_threshold", sa.Numeric(10, 6)),
    sa.Column("model_version", sa.String(128)),
    sa.Column("latest_error", sa.Text),
    sa.Column("stats_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
    *utc_created_updated(),
)

provider_requests = sa.Table(
    "provider_requests",
    BASELINE_METADATA,
    sa.Column("request_id", sa.String(64), primary_key=True),
    sa.Column("provider", sa.String(32), nullable=False),
    sa.Column("endpoint", sa.String(128), nullable=False),
    sa.Column("method", sa.String(16), nullable=False, server_default="GET"),
    sa.Column("symbol", sa.String(16)),
    sa.Column("interval", sa.String(8)),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("finished_at", sa.DateTime(timezone=True)),
    sa.Column("status", sa.String(32), nullable=False),
    sa.Column("response_status", sa.Integer),
    sa.Column("row_count", sa.Integer),
    sa.Column("cache_hit", sa.Boolean, nullable=False, server_default=sa.text("false")),
    sa.Column("error_message", sa.Text),
    sa.Column("metadata_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
)

exports = sa.Table(
    "exports",
    BASELINE_METADATA,
    sa.Column("export_id", sa.String(64), primary_key=True),
    sa.Column("export_type", sa.String(64), nullable=False),
    sa.Column("format", sa.String(16), nullable=False),
    sa.Column("path", sa.Text, nullable=False),
    sa.Column("row_count", sa.Integer, nullable=False, server_default="0"),
    sa.Column("source_run_id", sa.String(64)),
    sa.Column("payload_json", sa.JSON, nullable=False, server_default=sa.text("'{}'::jsonb")),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
)

daily_reviews = sa.Table(
    "daily_reviews",
    BASELINE_METADATA,
    sa.Column("review_id", sa.String(64), primary_key=True),
    sa.Column("review_date", sa.Date, nullable=False, unique=True),
    sa.Column("payload_json", sa.JSON, nullable=False),
    *utc_created_updated(),
)

BASELINE_TABLES = [
    symbols,
    bars,
    features,
    candidate_signals,
    labels,
    validation_reports,
    validation_windows,
    model_runs,
    model_artifacts,
    active_models,
    live_signals,
    closed_signals,
    scanner_runs,
    provider_requests,
    exports,
    daily_reviews,
]

BASELINE_TABLE_NAMES = [table.name for table in BASELINE_TABLES]


def upgrade() -> None:
    bind = op.get_bind()
    for table in BASELINE_TABLES:
        table.create(bind=bind)
    op.create_index("ix_bars_lookup", "bars", ["symbol", "interval", "timestamp_utc"], unique=False)
    op.create_index("ix_features_lookup", "features", ["symbol", "interval", "timestamp_utc"], unique=False)
    op.create_index("ix_live_signals_latest", "live_signals", ["timestamp_utc", "ticker"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_live_signals_latest", table_name="live_signals")
    op.drop_index("ix_features_lookup", table_name="features")
    op.drop_index("ix_bars_lookup", table_name="bars")
    for table_name in reversed(BASELINE_TABLE_NAMES):
        op.drop_table(table_name)
