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
expected_pnpm="11.9.0"

if [ -s "$HOME/.nvm/nvm.sh" ]; then
  # shellcheck disable=SC1091
  . "$HOME/.nvm/nvm.sh"
  nvm use "$expected_node" >/dev/null 2>&1 || true
fi

if [ -f ".node-version" ] && [ "$(cat .node-version)" = "$expected_node" ]; then
  ok ".node-version targets $expected_node"
else
  warn ".node-version should target $expected_node"
fi

if [ -f "package.json" ] && grep -q "\"node\": \"$expected_node\"" package.json; then
  ok "package.json engines.node targets $expected_node"
else
  warn "package.json engines.node should target $expected_node"
fi

if command -v node >/dev/null 2>&1; then
  node_output="$(node --version 2>&1 || true)"
  node_version="${node_output#v}"
  if [ "$node_version" = "$expected_node" ]; then
    ok "node $node_version"
  else
    warn "node is not usable at target $expected_node: $node_output"
  fi
else
  missing "node; install Node $expected_node"
fi

if command -v corepack >/dev/null 2>&1; then
  ok "corepack available"
  pnpm_version="$(COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --version 2>/dev/null || true)"
  if [ "$pnpm_version" = "$expected_pnpm" ]; then
    ok "corepack pnpm $pnpm_version"
  elif [ -n "$pnpm_version" ]; then
    warn "corepack pnpm $pnpm_version found; expected $expected_pnpm"
  else
    warn "corepack pnpm did not report a version; run corepack prepare pnpm@$expected_pnpm --activate"
  fi
else
  missing "corepack; use Node $expected_node with bundled Corepack"
fi

if [ -f "apps/web/package.json" ]; then
  ok "apps/web package present"
else
  missing "apps/web/package.json"
fi

if grep -q '"@sveltejs/kit"' apps/web/package.json 2>/dev/null; then
  sveltekit_version="$(node -e "const p=require('./apps/web/package.json'); console.log(p.dependencies['@sveltejs/kit'])" 2>/dev/null || true)"
  ok "SvelteKit dependency $sveltekit_version"
else
  missing "@sveltejs/kit dependency"
fi

if grep -q '"strict": true' apps/web/tsconfig.json 2>/dev/null; then
  ok "apps/web TypeScript strict enabled"
else
  warn "apps/web tsconfig should keep strict=true"
fi

if grep -RInE 'FMP_API_KEY|DATABASE_URL|PRIVATE_|SECRET|TOKEN|PASSWORD' apps/web/src packages/shared/src >/dev/null 2>&1; then
  warn "frontend source contains secret-shaped identifiers; review before shipping"
else
  ok "frontend source has no secret-shaped env references"
fi

printf "\nFrontend doctor finished. Run from Node %s for target-runtime acceptance.\n" "$expected_node"
