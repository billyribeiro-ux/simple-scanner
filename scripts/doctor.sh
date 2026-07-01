#!/usr/bin/env bash
set -u

ok() {
  printf "ok      %s\n" "$1"
}

warn() {
  printf "warning %s\n" "$1"
}

missing() {
  printf "missing %s\n" "$1"
}

run_timeout() {
  seconds="$1"
  shift
  perl -e 'alarm shift; exec @ARGV' "$seconds" "$@"
}

expected_node="24.18.0"
expected_python="3.14.6"
service_dir="services/quant-engine"
venv_bin="$service_dir/.venv/bin"

if [ -f ".node-version" ] && [ "$(cat .node-version)" = "$expected_node" ]; then
  ok ".node-version targets $expected_node"
else
  warn ".node-version should target $expected_node"
fi

if [ -f ".python-version" ] && [ "$(cat .python-version)" = "$expected_python" ]; then
  ok ".python-version targets $expected_python"
else
  warn ".python-version should target Python $expected_python"
fi

if command -v node >/dev/null 2>&1; then
  node_version="$(node --version | sed 's/^v//')"
  if [ "$node_version" = "$expected_node" ]; then
    ok "node $node_version"
  else
    warn "node $node_version found; project target is $expected_node"
  fi
else
  missing "node; install Node $expected_node"
fi

if command -v corepack >/dev/null 2>&1; then
  ok "corepack available"
  pnpm_version="$(COREPACK_ENABLE_DOWNLOAD_PROMPT=0 run_timeout 20 corepack pnpm --version 2>/dev/null || true)"
  if [ -n "$pnpm_version" ]; then
    ok "corepack pnpm $pnpm_version"
  else
    warn "corepack pnpm did not report a version within 20s; run corepack prepare pnpm@11.5.2 --activate deliberately"
  fi
else
  missing "corepack; install/enable Corepack before pnpm commands"
fi

if command -v python3.14 >/dev/null 2>&1; then
  python_version="$(python3.14 --version 2>&1 | awk '{print $2}')"
  if [ "$python_version" = "$expected_python" ]; then
    ok "python3.14 $python_version"
  else
    warn "python3.14 $python_version found; project target is $expected_python"
  fi
else
  missing "python3.14; install Python $expected_python with pyenv, asdf, uv python install, or a manual python.org build"
fi

if [ -x "$venv_bin/python" ]; then
  ok "backend venv exists"
  venv_python_version="$("$venv_bin/python" --version 2>&1 | awk '{print $2}')"
  if [ "$venv_python_version" = "$expected_python" ]; then
    ok "backend venv python $venv_python_version"
  else
    warn "backend venv python $venv_python_version found; expected $expected_python"
  fi
else
  missing "backend venv; run make setup-backend after installing Python $expected_python"
fi

for tool in pytest ruff mypy alembic uvicorn; do
  if [ -x "$venv_bin/$tool" ]; then
    ok "backend venv tool $tool"
  else
    missing "backend venv tool $tool"
  fi
done

if [ -x "$venv_bin/python" ]; then
  if "$venv_bin/python" - <<'PY' >/dev/null 2>&1
import alembic, fastapi, httpx, numpy, pandas, polars, pydantic, sqlalchemy, uvicorn
PY
  then
    ok "backend core dependencies import"
  else
    warn "backend dependency import check failed; rerun make setup-backend"
  fi
  persistence_backend="$(PYTHONPATH="$service_dir" "$venv_bin/python" - <<'PY' 2>/dev/null || true
from app.db.repositories import persistence_backend_info

info = persistence_backend_info()
print(
    f"{info['persistence_backend']} {info['runtime_mode']} "
    f"database_url_kind={info['database_url_kind']} "
    f"database_reachable={info['database_reachable']} "
    f"fallback_enabled={info['fallback_enabled']}"
)
PY
)"
  if [ -n "$persistence_backend" ]; then
    ok "active API persistence backend $persistence_backend"
  else
    warn "could not inspect active API persistence backend"
  fi
fi

if docker info >/dev/null 2>&1; then
  ok "docker daemon reachable"
  if docker compose ps >/dev/null 2>&1; then
    ok "docker compose available"
    docker compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}" 2>/dev/null || true
  else
    warn "docker compose did not report service status"
  fi
else
  warn "docker daemon is not reachable; database services and migrations are blocked, pure quant tests do not require Docker"
fi

if [ -n "${DATABASE_URL:-}" ]; then
  ok "DATABASE_URL present"
else
  warn "DATABASE_URL missing; local sqlite persistence is used by API fallback, Postgres migrations need a database URL or Alembic default"
fi

if [ -n "${FMP_API_KEY:-}" ]; then
  ok "FMP_API_KEY present"
else
  warn "FMP_API_KEY missing; live FMP ingestion/scanner are blocked, pure quant tests do not require it"
fi

if git check-ignore -q .env && git check-ignore -q .env.local; then
  ok ".env and .env.local are git-ignored"
else
  warn ".env or .env.local is not git-ignored"
fi

if git check-ignore -q data/local_repo.sqlite3 && git check-ignore -q exports/example.csv && git check-ignore -q model_artifacts/example.json; then
  ok "local persistence/export/model artifact paths are git-ignored"
else
  warn "one or more local runtime artifact paths are not git-ignored"
fi

printf "\nDoctor finished. Review warnings for optional config, local version drift, or missing live-provider credentials.\n"
