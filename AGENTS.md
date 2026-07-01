# Adaptive Market Decoder Agent Rules

- Never hardcode, print, commit, or expose `FMP_API_KEY` or any secret-like value.
- This platform produces research signals and trade plans only. Do not add broker execution without explicit approval.
- Preserve chronological validation. Do not random-shuffle intraday samples across time.
- Normalize `APPL` to `AAPL` at all boundaries.
- Treat FMP WebSocket as entitlement-dependent and keep REST polling as the default V1 live path.
- Keep frontend code on Svelte 5 runes and current SvelteKit conventions.
- Keep global CSS limited to tokens, reset, typography, and layout primitives.
- Favor explicit, explainable signal logic over opaque black-box shortcuts.
- Add tests for leakage, provider parsing, signal scoring, and export shape when changing those subsystems.
