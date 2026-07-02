from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase13_operator_docs_exist_and_use_current_runtime_pins() -> None:
    docs = {
        "docs/local-operator-runbook.md",
        "docs/non-autonomous-scheduler.md",
        "docs/operator-daily-procedure.md",
        "docs/docker-postgres-troubleshooting.md",
        "docs/status/PHASE_13_PLAN_2026-07-01.md",
    }
    for path in docs:
        text = _read(path)
        if path.endswith(("local-operator-runbook.md", "operator-daily-procedure.md", "PHASE_13_PLAN_2026-07-01.md")):
            assert "24.18.0" in text
            assert "11.9.0" in text
        old_pin = "11." + "5.2"
        assert old_pin not in text


def test_local_operator_runbook_contains_required_safe_commands() -> None:
    text = _read("docs/local-operator-runbook.md")
    for snippet in (
        'source "$HOME/.nvm/nvm.sh"',
        "nvm use 24.18.0",
        "corepack prepare pnpm@11.9.0 --activate",
        "make setup-backend",
        "corepack pnpm install --frozen-lockfile",
        "make db-up",
        "make db-migrate",
        "make db-inspect",
        "make db-query-diagnostics",
        "make api-dev",
        "make web-dev",
        "http://localhost:5173",
        "make scheduler-test",
        "make scheduler-status",
    ):
        assert snippet in text
    assert "No broker execution" in text
    assert "No order routing" in text
    assert "No automatic model activation" in text


def test_docker_troubleshooting_doc_records_clean_blocker_path() -> None:
    text = _read("docs/docker-postgres-troubleshooting.md")
    for snippet in (
        "docker context ls",
        "docker info",
        "docker compose config",
        "docker compose ps",
        "lsof -i :15432",
        "nc -zv localhost 15432",
        "make db-migrate",
        "make db-inspect",
        "make db-query-diagnostics",
    ):
        assert snippet in text
    assert "SQLite fallback tests do not prove local Postgres health" in text
    assert "FMP_API_KEY" not in text
