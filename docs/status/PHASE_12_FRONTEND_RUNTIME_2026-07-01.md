# Phase 12 Frontend Runtime

Status date: 2026-07-01

## Target

- Node: `24.18.0`
- Package manager: `pnpm@11.9.0` through Corepack
- SvelteKit: `2.68.0`
- Svelte: `5.56.4`
- TypeScript: strict

## Verified Local Path

Homebrew Node `25.3.0` is not used for acceptance. The target runtime is available through NVM:

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
```

Verified:

- `node --version`: `v24.18.0`
- `corepack pnpm --version`: `11.9.0`
- `make frontend-doctor`: pass

## Nested pnpm Fix

`COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check` initially failed because root scripts and Playwright startup used nested bare `pnpm`, which resolved to a newer shim. Phase 12 changed root package scripts and `apps/web/playwright.config.ts` to call `corepack pnpm` internally.

After the fix, these exact commands passed under Node `24.18.0`:

```bash
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm install --frozen-lockfile
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e
```

Playwright emitted only the local `NO_COLOR`/`FORCE_COLOR` warning from the environment; tests passed.

## Result

Frontend target-runtime acceptance is complete on Node `24.18.0` and pnpm `11.9.0`.
