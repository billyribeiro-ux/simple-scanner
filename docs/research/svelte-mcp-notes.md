# Svelte MCP Notes

Research date: 2026-06-30.

- A Svelte-specific MCP server was not exposed in this Codex session.
- Official Svelte docs were used instead through `https://svelte.dev/llms.txt`, `https://svelte.dev/llms-full.txt`, the Svelte 5 migration guide, TypeScript docs, and SvelteKit type docs.
- Svelte 5 runes are required for component state: `$state`, `$derived`, and `$effect`.
- Event handlers should use property syntax such as `onclick` instead of legacy `on:click`.
- `@phosphor-icons/svelte` returned 404 from npm during package verification; `phosphor-svelte@3.1.0` is used instead. Its components use an `Icon` suffix such as `ActivityIcon`.
- Frontend API requests must not receive the FMP API key. The browser talks to the FastAPI backend or SvelteKit server endpoints only.
