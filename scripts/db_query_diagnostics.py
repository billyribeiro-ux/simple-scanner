from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text

DEFAULT_URL = "postgresql+psycopg://amd:amd@localhost:15432/adaptive_market_decoder"


def _database_url() -> str:
    return (os.environ.get("DATABASE_URL") or DEFAULT_URL).replace("+asyncpg", "+psycopg")


def _scalar(connection, sql: str):
    return connection.execute(text(sql)).scalar()


def _rows(connection, sql: str):
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
            "backtest_comparisons",
            "validation_reports",
            "exports",
            "pipeline_build_windows",
        ):
            count = _scalar(connection, f'select count(*) from "{table}"')
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
        print("dirty_windows=" + (",".join(f"{row['artifact_type']}:{row['windows']}" for row in dirty) if dirty else "none"))
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
                "replay="
                f"{row['replay_run_id']} simulation_type={row['simulation_type']} "
                f"config_hash={row['config_hash']} input_fingerprint={row['input_fingerprint']} created_at={row['created_at']}"
            )
        try:
            hypertables = _rows(connection, "select hypertable_name from timescaledb_information.hypertables order by hypertable_name")
        except Exception:
            hypertables = []
        print("timescale_hypertables=" + (",".join(row["hypertable_name"] for row in hypertables) if hypertables else "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
