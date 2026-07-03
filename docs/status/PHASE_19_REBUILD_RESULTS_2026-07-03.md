# Phase 19 Rebuild Results - 2026-07-03

Phase 19 rebuilt derived artifacts from persisted Phase 18 FMP bars and quotes. Feature, candidate, label, and replay rebuilds made no FMP requests.

## Rebuild Order

1. Feature rebuild from persisted bars.
2. Candidate rebuild from persisted features.
3. Label rebuild from persisted bars, features, and candidates.
4. Small-scope replay for `SPY,QQQ,AAPL,NVDA` on `1min`.
5. Optional default-universe intraday replay for all default symbols on `1min,5min,15min`.
6. Daily replay not-applicable cleanup for `1day` replay windows.
7. Freshness and research-cycle dry-run recheck.

## Results

| Step | Result |
| --- | --- |
| Features | 11999 bars read, 11999 features written, 140 dirty feature windows cleared |
| Candidates | 11999 features read, 14976 candidate rows written on final all-interval pass, 7711 actionable candidates observed, 140 dirty candidate windows cleared |
| Labels | 14976 candidate rows read on final all-interval pass, 2088 label rows written, 140 dirty label windows cleared |
| Small replay | `SPY,QQQ,AAPL,NVDA`, `1min`, strict stale inputs clean, replay run IDs `replay_20260703132342_48a6b35debfd62244361ea09` and `replay_20260703132343_df74191456eb8e03eaec364e` |
| Default intraday replay | All default symbols, `1min,5min,15min`, replay run IDs `replay_20260703132536_549bebf359fa0e6d9261108a` and `replay_20260703132540_d77a7add68d69518dc6b1c4a` |
| Daily replay cleanup | 40 `1day` replay windows marked clean as `candidate_market_replay_is_intraday_only` |
| Final audit | 0 dirty windows |

Replay metrics are diagnostic research artifacts only. They are not live-fill proof and not profitability claims.

## Export Evidence

| Export | SHA-256 |
| --- | --- |
| `exports/phase19_feature_rebuild_report_20260703T132340_9a603451ed54.json` | `b6f7a0855cb610e02591c1697a4d9bf0087a3cd49db34fccf16774e09262fd10` |
| `exports/phase19_candidate_rebuild_report_20260703T132535_b53a870c1991.json` | `9e5a54c5b8b7a062ad9afa3f7ad76015b29c8de6c1b6b2657381c7ad7d99e04d` |
| `exports/phase19_label_rebuild_report_20260703T132536_fb4fa48ac8b0.json` | `f2e6a2ee3ffeb80567eefd547fc00c9dc3cdfa101adce09a96420591b221832a` |
| `exports/phase19_replay_report_20260703T132544_d8beb5f13450.json` | `2a0eff41ece96b31bcf1f9350d32554698c98edec54450edc374e505daf6fc30` |
| `exports/phase19_replay_report_20260703T132706_24c375e58c47.json` | `c7537c64ed3586be42e32bbbc5ec14c7354ec0e40c7a84c82ca9fee8418fcb3c` |
