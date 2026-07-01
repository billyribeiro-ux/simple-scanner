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
    missing = sorted(EXPECTED_TABLES - tables)
    print(f"alembic_version={version_row[0] if version_row else 'missing'}")
    print(f"tables={len(tables)}")
    print(f"missing_tables={','.join(missing) if missing else 'none'}")
    print(f"extensions={','.join(extensions)}")
    return 1 if missing or version_row is None else 0


if __name__ == "__main__":
    sys.exit(main())
