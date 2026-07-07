from __future__ import annotations

from pathlib import Path


def test_initial_migration_does_not_import_live_schema_metadata() -> None:
    migration_path = (
        Path(__file__).parents[1] / "alembic" / "versions" / "0001_initial.py"
    )
    source = migration_path.read_text()

    forbidden_patterns = [
        "from app.db.schema import metadata",
        "import app.db.schema",
        "metadata.create_all",
        "metadata.sorted_tables",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in source

