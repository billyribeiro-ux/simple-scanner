from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text

EXPECTED_TABLES = {
    "active_models",
    "alembic_version",
    "bars",
    "candidate_signals",
    "closed_signals",
    "daily_reviews",
    "exports",
    "features",
    "labels",
    "live_signals",
    "model_artifacts",
    "model_runs",
    "provider_requests",
    "scanner_runs",
    "symbols",
    "validation_reports",
    "validation_windows",
}

DEFAULT_URL = "postgresql+psycopg://amd:amd@localhost:15432/adaptive_market_decoder"
EXPECTED_REVISION = "0002_phase5_indexes"
EXPECTED_INDEXES = {
    "ix_bars_lookup",
    "ix_features_lookup",
    "ix_features_lookup_version",
    "ix_labels_symbol_ts_setup_side_outcome",
    "ix_live_signals_latest",
    "ix_live_signals_ticker_ts_status",
    "ix_validation_reports_model_purpose_created",
    "ix_scanner_runs_started",
}
EXPECTED_UNIQUE_CONSTRAINTS = {
    "uq_active_models_type_scope",
    "uq_bars_symbol_interval_ts_source",
    "uq_candidate_signal_key",
    "uq_features_symbol_interval_ts_version",
    "uq_label_key",
}
EXPECTED_COLUMNS = {
    "bars": {"symbol", "interval", "timestamp_utc", "source", "payload_json"},
    "features": {"symbol", "interval", "timestamp_utc", "feature_set_version", "payload_json"},
    "labels": {"symbol", "timestamp_utc", "setup_type", "side", "outcome", "payload_json"},
    "live_signals": {"ticker", "timestamp_utc", "status", "payload_json"},
    "model_runs": {"model_version", "active", "payload_json"},
    "validation_reports": {"report_id", "model_version", "payload_json"},
    "active_models": {"model_type", "strategy_scope", "payload_json"},
    "exports": {"export_id", "payload_json"},
    "daily_reviews": {"review_date", "payload_json"},
}
EXPECTED_JSON_COLUMNS = {
    ("bars", "payload_json"),
    ("features", "payload_json"),
    ("candidate_signals", "payload_json"),
    ("labels", "payload_json"),
    ("validation_reports", "payload_json"),
    ("model_runs", "payload_json"),
    ("active_models", "payload_json"),
    ("live_signals", "payload_json"),
    ("scanner_runs", "symbols_json"),
    ("scanner_runs", "stats_json"),
    ("provider_requests", "metadata_json"),
    ("exports", "payload_json"),
    ("daily_reviews", "payload_json"),
}


def _migration_url() -> str:
    configured = os.environ.get("DATABASE_URL") or DEFAULT_URL
    return configured.replace("+asyncpg", "+psycopg")


def main() -> int:
    engine = create_engine(_migration_url())
    with engine.connect() as connection:
        tables = {
            str(row[0])
            for row in connection.execute(
                text("select tablename from pg_tables where schemaname = 'public' order by tablename")
            )
        }
        extensions = [
            str(row[0])
            for row in connection.execute(text("select extname from pg_extension order by extname"))
        ]
        version_row = connection.execute(text("select version_num from alembic_version")).first()
        indexes = {
            str(row[0])
            for row in connection.execute(
                text("select indexname from pg_indexes where schemaname = 'public'")
            )
        }
        unique_constraints = {
            str(row[0])
            for row in connection.execute(
                text(
                    """
                    select conname
                    from pg_constraint
                    where connamespace = 'public'::regnamespace
                      and contype in ('u', 'p')
                    """
                )
            )
        }
        columns = {
            (str(row[0]), str(row[1]))
            for row in connection.execute(
                text(
                    """
                    select table_name, column_name
                    from information_schema.columns
                    where table_schema = 'public'
                    """
                )
            )
        }
        json_columns = {
            (str(row[0]), str(row[1]))
            for row in connection.execute(
                text(
                    """
                    select table_name, column_name
                    from information_schema.columns
                    where table_schema = 'public'
                      and data_type in ('json', 'jsonb')
                    """
                )
            )
        }
    missing = sorted(EXPECTED_TABLES - tables)
    missing_indexes = sorted(EXPECTED_INDEXES - indexes)
    missing_constraints = sorted(EXPECTED_UNIQUE_CONSTRAINTS - unique_constraints)
    missing_columns = sorted(
        f"{table}.{column}"
        for table, expected_columns in EXPECTED_COLUMNS.items()
        for column in expected_columns
        if (table, column) not in columns
    )
    missing_json_columns = sorted(
        f"{table}.{column}" for table, column in EXPECTED_JSON_COLUMNS if (table, column) not in json_columns
    )
    version = version_row[0] if version_row else "missing"
    print(f"alembic_version={version}")
    print(f"tables={len(tables)}")
    print(f"missing_tables={','.join(missing) if missing else 'none'}")
    print(f"missing_indexes={','.join(missing_indexes) if missing_indexes else 'none'}")
    print(f"missing_constraints={','.join(missing_constraints) if missing_constraints else 'none'}")
    print(f"missing_columns={','.join(missing_columns) if missing_columns else 'none'}")
    print(f"missing_json_columns={','.join(missing_json_columns) if missing_json_columns else 'none'}")
    print(f"extensions={','.join(extensions)}")
    missing_extension = "timescaledb" not in extensions
    wrong_revision = version != EXPECTED_REVISION
    return 1 if (
        missing
        or missing_indexes
        or missing_constraints
        or missing_columns
        or missing_json_columns
        or missing_extension
        or wrong_revision
    ) else 0


if __name__ == "__main__":
    sys.exit(main())
