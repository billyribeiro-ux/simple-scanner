from __future__ import annotations

import os
from urllib.parse import quote

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.db.repositories import _sync_postgres_url


def _default_test_url() -> str:
    user = os.environ.get("LOCAL_POSTGRES_USER", "amd")
    password = os.environ.get("LOCAL_POSTGRES_PASSWORD", "amd")
    host = os.environ.get("LOCAL_POSTGRES_HOST", "localhost")
    port = os.environ.get("LOCAL_POSTGRES_PORT", "15432")
    database = os.environ.get("LOCAL_POSTGRES_TEST_DB", "adaptive_market_decoder_test")
    return f"postgresql+psycopg://{quote(user)}:{quote(password)}@{host}:{port}/{database}"


def main() -> None:
    test_url = _sync_postgres_url(os.environ.get("TEST_DATABASE_URL") or _default_test_url())
    parsed = make_url(test_url)
    database = parsed.database
    if not database:
        raise SystemExit("TEST_DATABASE_URL must include a database name")
    admin_url = parsed.set(database="postgres")
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :database"),
            {"database": database},
        ).scalar_one_or_none()
        if not exists:
            safe_name = '"' + database.replace('"', '""') + '"'
            connection.execute(text(f"CREATE DATABASE {safe_name}"))
    print("test_database_ready")


if __name__ == "__main__":
    main()
