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

expected_node="24.18.0"
expected_python="3.14.6"

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
else
  missing "corepack; install/enable Corepack before pnpm commands"
fi

if command -v corepack >/dev/null 2>&1; then
  pnpm_version="$(corepack pnpm --version 2>/dev/null || true)"
  if [ -n "$pnpm_version" ]; then
    ok "corepack pnpm $pnpm_version"
  else
    warn "corepack pnpm did not report a version"
  fi
else
  warn "pnpm check skipped because corepack is unavailable"
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

if [ -x "services/quant-engine/.venv/bin/python" ]; then
  ok "backend venv exists"
else
  missing "backend venv; run make setup-backend after installing Python $expected_python"
fi

if docker info >/dev/null 2>&1; then
  ok "docker daemon reachable"
else
  warn "docker daemon is not reachable; database services and migrations are blocked, pure quant tests do not require Docker"
fi

if [ -n "${FMP_API_KEY:-}" ]; then
  ok "FMP_API_KEY present"
else
  warn "FMP_API_KEY missing; live FMP ingestion/scanner are blocked, pure quant tests do not require it"
fi

if [ -n "${DATABASE_URL:-}" ]; then
  ok "DATABASE_URL present"
else
  warn "DATABASE_URL missing; local docker defaults may still work once Docker is running"
fi

printf "\nDoctor finished. Missing target runtime tools block full backend verification, not pure quant unit tests.\n"
