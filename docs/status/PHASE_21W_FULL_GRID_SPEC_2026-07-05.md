# Phase 21W Full Default Sensitivity Grid Spec

Date: 2026-07-05
Grid version: `replay_sensitivity.full_default_grid.v1`
Grid hash: `1f7c8a8a7b14e40768954acf273280866b768d8f5516abbc29c6a3187511201b`
Scenario count: `75`

## Dimensions

- Slippage bps: `0`, `1`, `2`, `5`, `10`
- Spread bps: `0`, `1`, `2`, `5`, `10`
- Intrabar path policies: `conservative`, `open_high_low_close`, `open_low_high_close`
- Same-bar stop/target policy: `conservative_stop_first`
- Commission/cost assumptions: replay base `commission_per_share` is preserved from the source replay config; Phase 21W varies only slippage and spread costs.
- Target/stop assumptions: replay base `stop_mode`, `target_mode`, `target_1_r`, `target_2_r`, `target_3_r`, partial-exit mode, and hold constraints are preserved from the source replay config; Phase 21W does not vary target/stop geometry.

The dimensions exist to stress execution-cost sensitivity, spread sensitivity, and OHLC path ambiguity without changing the strategy definition, candidate generation, labels, stale gates, or replay source data.

## Deterministic Keys

Scenario rows persist with this unique key shape:

- `sensitivity_run_id`
- `scenario_id`
- `replay_run_id`
- `grid_version`

`scenario_id` is a deterministic hash of the sensitivity run ID, replay run ID, grid version, and replay scenario config. The table below records deterministic config hashes for the default grid order; runtime scenario IDs additionally bind these configs to the exact sensitivity run and replay run.

| # | Slippage bps | Spread bps | Intrabar path policy | Same-bar policy | Deterministic config hash |
|---:|---:|---:|---|---|---|
| 1 | 0 | 0 | `conservative` | `conservative_stop_first` | `05e704e741ffbfd0` |
| 2 | 0 | 0 | `open_high_low_close` | `conservative_stop_first` | `18cd2837b7fd8cff` |
| 3 | 0 | 0 | `open_low_high_close` | `conservative_stop_first` | `094222a09f4523f1` |
| 4 | 0 | 1 | `conservative` | `conservative_stop_first` | `52c2c36f4dbcc918` |
| 5 | 0 | 1 | `open_high_low_close` | `conservative_stop_first` | `3a2fd7cbf89f9919` |
| 6 | 0 | 1 | `open_low_high_close` | `conservative_stop_first` | `e2f2d03fb7da38c7` |
| 7 | 0 | 2 | `conservative` | `conservative_stop_first` | `aeca86c75da0d834` |
| 8 | 0 | 2 | `open_high_low_close` | `conservative_stop_first` | `90482d32761c75ce` |
| 9 | 0 | 2 | `open_low_high_close` | `conservative_stop_first` | `53169e97ed95f50a` |
| 10 | 0 | 5 | `conservative` | `conservative_stop_first` | `5f59a22b8e37b243` |
| 11 | 0 | 5 | `open_high_low_close` | `conservative_stop_first` | `74dfc608cd3869bc` |
| 12 | 0 | 5 | `open_low_high_close` | `conservative_stop_first` | `0881273d25acb1e6` |
| 13 | 0 | 10 | `conservative` | `conservative_stop_first` | `5fdf24146327d93a` |
| 14 | 0 | 10 | `open_high_low_close` | `conservative_stop_first` | `e9f00fd2d7333786` |
| 15 | 0 | 10 | `open_low_high_close` | `conservative_stop_first` | `0ca176bcff2eaeb1` |
| 16 | 1 | 0 | `conservative` | `conservative_stop_first` | `1b585b8e92842ded` |
| 17 | 1 | 0 | `open_high_low_close` | `conservative_stop_first` | `2ecc4eb1f69c64a8` |
| 18 | 1 | 0 | `open_low_high_close` | `conservative_stop_first` | `9f02f7513eb0bfcf` |
| 19 | 1 | 1 | `conservative` | `conservative_stop_first` | `b6bbc35b41fd7be6` |
| 20 | 1 | 1 | `open_high_low_close` | `conservative_stop_first` | `baaac421a6c73388` |
| 21 | 1 | 1 | `open_low_high_close` | `conservative_stop_first` | `9df27a9a0b939dea` |
| 22 | 1 | 2 | `conservative` | `conservative_stop_first` | `21ef18f901c57ee4` |
| 23 | 1 | 2 | `open_high_low_close` | `conservative_stop_first` | `d8680aff237bb159` |
| 24 | 1 | 2 | `open_low_high_close` | `conservative_stop_first` | `91f79b585c5ff697` |
| 25 | 1 | 5 | `conservative` | `conservative_stop_first` | `86b6198b101a1142` |
| 26 | 1 | 5 | `open_high_low_close` | `conservative_stop_first` | `7de3e5553c3af6ca` |
| 27 | 1 | 5 | `open_low_high_close` | `conservative_stop_first` | `89939492b670fe58` |
| 28 | 1 | 10 | `conservative` | `conservative_stop_first` | `98189a07750ab8e1` |
| 29 | 1 | 10 | `open_high_low_close` | `conservative_stop_first` | `f744e816a567616b` |
| 30 | 1 | 10 | `open_low_high_close` | `conservative_stop_first` | `e7a8ed05b1af3683` |
| 31 | 2 | 0 | `conservative` | `conservative_stop_first` | `0aa9c87c4ce4aff5` |
| 32 | 2 | 0 | `open_high_low_close` | `conservative_stop_first` | `e3406266fd589e3d` |
| 33 | 2 | 0 | `open_low_high_close` | `conservative_stop_first` | `53539ee5d2aad94f` |
| 34 | 2 | 1 | `conservative` | `conservative_stop_first` | `64dff05f0f18c8fd` |
| 35 | 2 | 1 | `open_high_low_close` | `conservative_stop_first` | `4f0fe830af4557e5` |
| 36 | 2 | 1 | `open_low_high_close` | `conservative_stop_first` | `08a628945c75216a` |
| 37 | 2 | 2 | `conservative` | `conservative_stop_first` | `a95f7b9fbe7daea9` |
| 38 | 2 | 2 | `open_high_low_close` | `conservative_stop_first` | `b6bbbcc8201c9949` |
| 39 | 2 | 2 | `open_low_high_close` | `conservative_stop_first` | `57b8aab3493401be` |
| 40 | 2 | 5 | `conservative` | `conservative_stop_first` | `df8ea40db1192050` |
| 41 | 2 | 5 | `open_high_low_close` | `conservative_stop_first` | `f933f72b2754384c` |
| 42 | 2 | 5 | `open_low_high_close` | `conservative_stop_first` | `c263b78e67df8c49` |
| 43 | 2 | 10 | `conservative` | `conservative_stop_first` | `0eb01097bd5c7b74` |
| 44 | 2 | 10 | `open_high_low_close` | `conservative_stop_first` | `25f90dc1d9131d73` |
| 45 | 2 | 10 | `open_low_high_close` | `conservative_stop_first` | `a5b7d945e1d12363` |
| 46 | 5 | 0 | `conservative` | `conservative_stop_first` | `350afb8ab7d15158` |
| 47 | 5 | 0 | `open_high_low_close` | `conservative_stop_first` | `65a3a93cd85bc8f2` |
| 48 | 5 | 0 | `open_low_high_close` | `conservative_stop_first` | `57e89cd3622b3d90` |
| 49 | 5 | 1 | `conservative` | `conservative_stop_first` | `b928ff4ed3e3c256` |
| 50 | 5 | 1 | `open_high_low_close` | `conservative_stop_first` | `ec4b5d5f24b7b60a` |
| 51 | 5 | 1 | `open_low_high_close` | `conservative_stop_first` | `652569a988aa671f` |
| 52 | 5 | 2 | `conservative` | `conservative_stop_first` | `dd10d62cf0489429` |
| 53 | 5 | 2 | `open_high_low_close` | `conservative_stop_first` | `71acfd59f7ffcbfd` |
| 54 | 5 | 2 | `open_low_high_close` | `conservative_stop_first` | `22e471bbad22399e` |
| 55 | 5 | 5 | `conservative` | `conservative_stop_first` | `d6eb25bf7fdcb0f9` |
| 56 | 5 | 5 | `open_high_low_close` | `conservative_stop_first` | `052fe43cc328b14f` |
| 57 | 5 | 5 | `open_low_high_close` | `conservative_stop_first` | `dafe90051f3cdb4e` |
| 58 | 5 | 10 | `conservative` | `conservative_stop_first` | `a70b87391ce00733` |
| 59 | 5 | 10 | `open_high_low_close` | `conservative_stop_first` | `dc01ae2bb3b56aa6` |
| 60 | 5 | 10 | `open_low_high_close` | `conservative_stop_first` | `c7440af3f9ff8103` |
| 61 | 10 | 0 | `conservative` | `conservative_stop_first` | `dba037fe54cbbcae` |
| 62 | 10 | 0 | `open_high_low_close` | `conservative_stop_first` | `5d318ce13857e373` |
| 63 | 10 | 0 | `open_low_high_close` | `conservative_stop_first` | `6f5fad96eb54eee6` |
| 64 | 10 | 1 | `conservative` | `conservative_stop_first` | `793c33be4c40057e` |
| 65 | 10 | 1 | `open_high_low_close` | `conservative_stop_first` | `a899fb7c0b2e4652` |
| 66 | 10 | 1 | `open_low_high_close` | `conservative_stop_first` | `ea4cb3453ab1a779` |
| 67 | 10 | 2 | `conservative` | `conservative_stop_first` | `ed737832ab7594a9` |
| 68 | 10 | 2 | `open_high_low_close` | `conservative_stop_first` | `747b31f930d50d56` |
| 69 | 10 | 2 | `open_low_high_close` | `conservative_stop_first` | `933aa0f853d2d0a8` |
| 70 | 10 | 5 | `conservative` | `conservative_stop_first` | `fb4bd471a415fe94` |
| 71 | 10 | 5 | `open_high_low_close` | `conservative_stop_first` | `34379da787e17fa6` |
| 72 | 10 | 5 | `open_low_high_close` | `conservative_stop_first` | `c68242519a957cbd` |
| 73 | 10 | 10 | `conservative` | `conservative_stop_first` | `6cc19e4deca82999` |
| 74 | 10 | 10 | `open_high_low_close` | `conservative_stop_first` | `599b9f05cfa30f37` |
| 75 | 10 | 10 | `open_low_high_close` | `conservative_stop_first` | `7f587fc5b8ad3713` |

## Activation-Grade Requirement

A sensitivity run can satisfy required activation-grade sensitivity only when:

- `grid_version` and `grid_hash` are recorded.
- `coverage_mode` is `FULL_GRID` or `CHUNKED_FULL_GRID`.
- all 75 full-default scenarios are persisted for the replay run.
- `completion_status=COMPLETE`.
- `full_default_grid_complete=true`.
- `partial_grid_disclosure=false`.
- model review still separately requires `pass_fail=pass`; a complete full-grid run that fails robustness remains valid evidence but blocks promotion.

Diagnostic sensitivity modes such as `TIERED_ESSENTIAL`, `SAMPLED`, `PARTIAL_TIMEOUT`, scenario-group-only runs, or incomplete `CHUNKED_FULL_GRID` runs remain useful for investigation but cannot satisfy required activation-grade sensitivity.
