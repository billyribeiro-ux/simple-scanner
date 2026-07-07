from __future__ import annotations

import os
from collections.abc import Iterable
from urllib.parse import quote

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.db.repositories import EXPECTED_TABLES, _sync_postgres_url

FIXTURE_PREFIXES = ("parity-", "test-", "smoke-", "fixture-")
FIXTURE_EXACT_OR_FRAGMENT = ("parity-model-accepted", "parity-proposal", "parity-review")


def _default_evidence_url() -> str:
    user = os.environ.get("LOCAL_POSTGRES_USER", "amd")
    password = os.environ.get("LOCAL_POSTGRES_PASSWORD", "amd")
    host = os.environ.get("LOCAL_POSTGRES_HOST", "localhost")
    port = os.environ.get("LOCAL_POSTGRES_PORT", "15432")
    database = os.environ.get("LOCAL_POSTGRES_DB", "adaptive_market_decoder")
    return f"postgresql+psycopg://{quote(user)}:{quote(password)}@{host}:{port}/{database}"


def _database_url() -> str:
    return _sync_postgres_url(os.environ.get("DATABASE_URL") or _default_evidence_url())


def _descriptor(database_url: str) -> dict[str, object]:
    parsed = make_url(database_url)
    return {
        "driver": parsed.drivername,
        "host": parsed.host,
        "port": parsed.port,
        "database": parsed.database,
        "role": os.environ.get("AMD_DB_ROLE") or "evidence",
    }


def _quoted(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _count(connection, table: str) -> int:
    return int(connection.execute(text(f"SELECT COUNT(*) FROM {_quoted(table)}")).scalar_one())


def _text_like_conditions(columns: Iterable[str]) -> str:
    checks: list[str] = []
    for column in columns:
        expr = f"lower(CAST({_quoted(column)} AS TEXT))"
        for prefix in FIXTURE_PREFIXES:
            checks.append(f"{expr} LIKE '{prefix}%'")
            checks.append(f"{expr} LIKE '%\"{prefix}%'")
        for fragment in FIXTURE_EXACT_OR_FRAGMENT:
            checks.append(f"{expr} LIKE '%{fragment}%'")
    return " OR ".join(checks) or "false"


def _fixture_count(connection, table: str, columns: list[str]) -> int:
    condition = _text_like_conditions(columns)
    return int(connection.execute(text(f"SELECT COUNT(*) FROM {_quoted(table)} WHERE {condition}")).scalar_one())


def _sample_fixtures(connection, table: str, columns: list[str], limit: int = 8) -> list[str]:
    condition = _text_like_conditions(columns)
    id_columns = [column for column in columns if column.endswith("_id") or column in {"model_version", "status"}]
    if not id_columns:
        return []
    select_expr = " || ' | ' || ".join(f"COALESCE(CAST({_quoted(column)} AS TEXT), '')" for column in id_columns[:4])
    rows = connection.execute(
        text(f"SELECT DISTINCT {select_expr} AS sample FROM {_quoted(table)} WHERE {condition} LIMIT :limit"),
        {"limit": limit},
    ).fetchall()
    return [str(row._mapping["sample"]) for row in rows]


def main() -> None:
    database_url = _database_url()
    engine = create_engine(database_url, future=True)
    descriptor = _descriptor(database_url)
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names(schema="public"))
    expected_tables = sorted(EXPECTED_TABLES & table_names)
    missing_tables = sorted(EXPECTED_TABLES - table_names)

    with engine.connect() as connection:
        revision = (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            if "alembic_version" in table_names
            else None
        )
        rows: list[dict[str, object]] = []
        fixture_total = 0
        total_rows = 0
        samples: dict[str, list[str]] = {}
        for table in expected_tables:
            total = _count(connection, table)
            columns = [
                column["name"]
                for column in inspector.get_columns(table, schema="public")
                if str(column["type"]).lower().startswith(("varchar", "text", "json"))
                or column["name"].endswith("_id")
                or column["name"] in {"model_version", "status", "source"}
            ]
            fixtures = _fixture_count(connection, table, columns) if total and columns else 0
            if fixtures:
                samples[table] = _sample_fixtures(connection, table, columns)
            total_rows += total
            fixture_total += fixtures
            rows.append({"table": table, "rows": total, "fixture_rows": fixtures, "live_rows": total - fixtures})

    if not total_rows:
        status = "EMPTY"
    elif fixture_total:
        status = "CONTAMINATED"
    elif missing_tables:
        status = "UNKNOWN"
    else:
        status = "CLEAN"

    print("# Evidence DB Audit")
    print()
    print(f"- database: `{descriptor['database']}`")
    print(f"- host: `{descriptor['host']}`")
    print(f"- port: `{descriptor['port']}`")
    print(f"- role: `{descriptor['role']}`")
    print(f"- alembic_revision: `{revision}`")
    print(f"- contaminated_status: `{status}`")
    print(f"- total_rows: `{total_rows}`")
    print(f"- fixture_rows: `{fixture_total}`")
    print(f"- missing_tables: `{','.join(missing_tables) if missing_tables else 'none'}`")
    print()
    print("| Table | Rows | Fixture Rows | Live Rows |")
    print("|---|---:|---:|---:|")
    for row in rows:
        print(f"| `{row['table']}` | {row['rows']} | {row['fixture_rows']} | {row['live_rows']} |")
    if samples:
        print()
        print("## Fixture Samples")
        for table, table_samples in sorted(samples.items()):
            print()
            print(f"- `{table}`")
            for sample in table_samples:
                print(f"  - `{sample}`")


if __name__ == "__main__":
    main()
