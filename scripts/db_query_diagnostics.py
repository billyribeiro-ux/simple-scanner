from __future__ import annotations

import os
import sys
from collections.abc import Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, RowMapping

DEFAULT_POSTGRES_USER = os.environ.get("LOCAL_POSTGRES_USER", "amd")
DEFAULT_POSTGRES_PASSWORD = os.environ.get("LOCAL_POSTGRES_PASSWORD", "amd")
DEFAULT_POSTGRES_HOST = os.environ.get("LOCAL_POSTGRES_HOST", "localhost")
DEFAULT_POSTGRES_PORT = os.environ.get("LOCAL_POSTGRES_PORT", "15432")
DEFAULT_POSTGRES_DB = os.environ.get("LOCAL_POSTGRES_DB", "adaptive_market_decoder")


def _database_url() -> str:
    default_url = (
        "postgresql+psycopg://"
        + f"{DEFAULT_POSTGRES_USER}:{DEFAULT_POSTGRES_PASSWORD}"
        + f"@{DEFAULT_POSTGRES_HOST}:{DEFAULT_POSTGRES_PORT}/{DEFAULT_POSTGRES_DB}"
    )
    return (os.environ.get("DATABASE_URL") or default_url).replace("+asyncpg", "+psycopg")


def _scalar(connection: Connection, sql: str) -> str | int | None:
    return connection.execute(text(sql)).scalar()


def _rows(connection: Connection, sql: str) -> Sequence[RowMapping]:
    return connection.execute(text(sql)).mappings().all()


def main() -> int:
    engine = create_engine(_database_url())
    with engine.connect() as connection:
        version = _scalar(connection, "select version_num from alembic_version")
        print(f"alembic_version={version}")
        for table in (
            "symbols",
            "bars",
            "features",
            "candidate_signals",
            "labels",
            "replay_runs",
            "simulated_trades",
            "replay_sensitivity_runs",
            "replay_sensitivity_scenarios",
            "replay_window_sets",
            "replay_window_results",
            "model_calibration_drift_reports",
            "model_calibration_drift_windows",
            "model_review_reports",
            "backtest_comparisons",
            "validation_reports",
            "exports",
            "pipeline_build_windows",
        ):
            # table is drawn from the fixed tuple above, never from external input.
            count = _scalar(connection, f'select count(*) from "{table}"')  # noqa: S608
            print(f"{table}.rows={count}")
        dirty = _rows(
            connection,
            """
            select artifact_type, count(*) as windows
            from pipeline_build_windows
            where dirty = true
            group by artifact_type
            order by artifact_type
            """,
        )
        print(
            "dirty_windows="
            + (
                ",".join(f"{row['artifact_type']}:{row['windows']}" for row in dirty)
                if dirty
                else "none"
            )
        )
        replay = _rows(
            connection,
            """
            select replay_run_id, simulation_type, config_hash, input_fingerprint, created_at
            from replay_runs
            order by created_at desc
            limit 5
            """,
        )
        for row in replay:
            print(
                f"replay={row['replay_run_id']} simulation_type={row['simulation_type']} "
                + f"config_hash={row['config_hash']} input_fingerprint={row['input_fingerprint']} created_at={row['created_at']}"
            )
        window_sets = _rows(
            connection,
            """
            select window_set_id, status, created_at
            from replay_window_sets
            order by created_at desc
            limit 5
            """,
        )
        for row in window_sets:
            print(f"window_set={row['window_set_id']} status={row['status']} created_at={row['created_at']}")
        drift_reports = _rows(
            connection,
            """
            select drift_report_id, model_version, severity, created_at
            from model_calibration_drift_reports
            order by created_at desc
            limit 5
            """,
        )
        for row in drift_reports:
            print(
                f"drift_report={row['drift_report_id']} model_version={row['model_version']} "
                + f"severity={row['severity']} created_at={row['created_at']}"
            )
        review_reports = _rows(
            connection,
            """
            select review_report_id, model_version, readiness_status, created_at
            from model_review_reports
            order by created_at desc
            limit 5
            """,
        )
        for row in review_reports:
            print(
                f"model_review={row['review_report_id']} model_version={row['model_version']} "
                + f"readiness_status={row['readiness_status']} created_at={row['created_at']}"
            )
        try:
            hypertables = _rows(
                connection,
                "select hypertable_name from timescaledb_information.hypertables order by hypertable_name",
            )
        except Exception:
            hypertables: Sequence[RowMapping] = []
        print(
            "timescale_hypertables="
            + (",".join(row["hypertable_name"] for row in hypertables) if hypertables else "none")
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
