from __future__ import annotations

import sqlalchemy as sa

metadata = sa.MetaData()

symbols = sa.Table(
    "symbols",
    metadata,
    sa.Column("symbol", sa.String(16), primary_key=True),
    sa.Column("name", sa.String(255)),
    sa.Column("asset_type", sa.String(32), nullable=False, server_default="equity"),
    sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
)

bars = sa.Table(
    "bars",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("symbol", sa.String(16), nullable=False, index=True),
    sa.Column("interval", sa.String(8), nullable=False, index=True),
    sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False, index=True),
    sa.Column("timestamp_et", sa.DateTime(timezone=True), nullable=False),
    sa.Column("open", sa.Numeric(18, 6), nullable=False),
    sa.Column("high", sa.Numeric(18, 6), nullable=False),
    sa.Column("low", sa.Numeric(18, 6), nullable=False),
    sa.Column("close", sa.Numeric(18, 6), nullable=False),
    sa.Column("volume", sa.BigInteger, nullable=False),
    sa.Column("vwap", sa.Numeric(18, 6)),
    sa.Column("source", sa.String(32), nullable=False),
    sa.Column("ingestion_time", sa.DateTime(timezone=True), server_default=sa.func.now()),
    sa.Column("quality_flags", sa.JSON, nullable=False, server_default="[]"),
    sa.UniqueConstraint("symbol", "interval", "timestamp_utc", name="uq_bars_symbol_interval_ts"),
)


def json_table(name: str) -> sa.Table:
    return sa.Table(
        name,
        metadata,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("payload", sa.JSON, nullable=False),
    )


quotes = json_table("quotes")
features = sa.Table(
    "features",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("symbol", sa.String(16), nullable=False, index=True),
    sa.Column("interval", sa.String(8), nullable=False, index=True),
    sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False, index=True),
    sa.Column("timestamp_et", sa.DateTime(timezone=True), nullable=False),
    sa.Column("session_date", sa.Date, nullable=False, index=True),
    sa.Column("feature_set_version", sa.String(64), nullable=False),
    sa.Column("data_quality_flags", sa.JSON, nullable=False, server_default="[]"),
    sa.Column("payload", sa.JSON, nullable=False),
    sa.UniqueConstraint("symbol", "interval", "timestamp_utc", "feature_set_version", name="uq_features_symbol_interval_ts_version"),
)
labels = sa.Table(
    "labels",
    metadata,
    sa.Column("label_id", sa.String(64), primary_key=True),
    sa.Column("symbol", sa.String(16), nullable=False, index=True),
    sa.Column("interval", sa.String(8), nullable=False, index=True),
    sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False, index=True),
    sa.Column("side", sa.String(16), nullable=False),
    sa.Column("setup_type", sa.String(128), nullable=False, index=True),
    sa.Column("label_config_version", sa.String(64), nullable=False),
    sa.Column("entry_price", sa.Numeric(18, 6), nullable=False),
    sa.Column("stop_price", sa.Numeric(18, 6), nullable=False),
    sa.Column("target_1", sa.Numeric(18, 6), nullable=False),
    sa.Column("target_2", sa.Numeric(18, 6), nullable=False),
    sa.Column("target_3", sa.Numeric(18, 6), nullable=False),
    sa.Column("realized_r", sa.Numeric(18, 6), nullable=False),
    sa.Column("outcome", sa.String(16), nullable=False),
    sa.Column("payload", sa.JSON, nullable=False),
)
regimes = json_table("regimes")
model_runs = json_table("model_runs")
model_metrics = json_table("model_metrics")
live_signals = json_table("live_signals")
closed_signals = json_table("closed_signals")
daily_reviews = json_table("daily_reviews")
provider_requests = json_table("provider_requests")
exports = json_table("exports")
