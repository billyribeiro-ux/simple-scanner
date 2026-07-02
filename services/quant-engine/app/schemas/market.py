from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

try:
    from pydantic import BaseModel, ConfigDict, Field
except ModuleNotFoundError:  # pragma: no cover - compatibility path for pure quant tests without venv
    class _FieldInfo:
        def __init__(self, default: Any = None, default_factory: Any = None) -> None:
            self.default = default
            self.default_factory = default_factory

        def value(self) -> Any:
            if self.default_factory is not None:
                return self.default_factory()
            return self.default

    def Field(default: Any = None, default_factory: Any = None, **_: Any) -> _FieldInfo:
        return _FieldInfo(default=default, default_factory=default_factory)

    def ConfigDict(**kwargs: Any) -> dict[str, Any]:
        return kwargs

    class BaseModel:
        def __init__(self, **kwargs: Any) -> None:
            annotations: dict[str, Any] = {}
            for cls in reversed(type(self).mro()):
                annotations.update(getattr(cls, "__annotations__", {}))
            for name in annotations:
                if name == "model_config":
                    continue
                if name in kwargs:
                    value = kwargs[name]
                else:
                    default = getattr(type(self), name, None)
                    value = default.value() if isinstance(default, _FieldInfo) else default
                setattr(self, name, value)

        def model_dump(self, mode: str = "python") -> dict[str, Any]:
            output = {}
            for key, value in self.__dict__.items():
                if isinstance(value, Enum):
                    output[key] = value.value if mode == "json" else value
                elif isinstance(value, datetime):
                    output[key] = value.isoformat() if mode == "json" else value
                else:
                    output[key] = value
            return output


class _StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class Side(_StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"


class Outcome(_StrEnum):
    WIN = "WIN"
    LOSS = "LOSS"
    NEUTRAL = "NEUTRAL"


class SignalStatus(_StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    SKIPPED = "SKIPPED"


class Bar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    interval: str
    timestamp_utc: datetime
    timestamp_et: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float | None = None
    source: str = "fmp"
    ingestion_time: datetime | None = None
    quality_flags: list[str] = Field(default_factory=list)


class Quote(BaseModel):
    symbol: str
    price: float
    timestamp_utc: datetime | None = None
    volume: int | None = None
    source: str = "fmp"
    raw: dict[str, Any] = Field(default_factory=dict)


class Label(BaseModel):
    label_id: str
    symbol: str
    timestamp: datetime
    side: Side
    entry_price: float
    stop_price: float
    target_1: float
    target_2: float
    target_3: float
    max_favorable_excursion: float
    max_adverse_excursion: float
    hit_target_1: bool
    hit_target_2: bool
    hit_target_3: bool
    hit_stop: bool
    time_to_target: int | None
    time_to_stop: int | None
    realized_r: float
    outcome: Outcome
    setup_type: str
    market_regime: str


class Signal(BaseModel):
    timestamp: datetime
    ticker: str
    side: Side
    entry_price: float | None
    stop_price: float | None
    target_1: float | None
    target_2: float | None
    target_3: float | None
    risk_per_share: float | None
    reward_risk_to_t1: float | None
    reward_risk_to_t2: float | None
    reward_risk_to_t3: float | None
    expected_r: float
    confidence_score: float
    signal_grade: str
    setup_type: str
    market_regime: str
    ticker_regime: str
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    historical_sample_size: int = 0
    historical_win_rate: float = 0.0
    historical_average_r: float = 0.0
    model_version: str
    training_start: datetime | None = None
    training_end: datetime | None = None
    data_source: str = "fmp"
    status: SignalStatus = SignalStatus.OPEN
    exit_price: float | None = None
    exit_reason: str | None = None
    realized_r: float | None = None


class IngestRequest(BaseModel):
    symbols: list[str] | None = None
    intervals: list[Literal["1min", "5min", "15min"]] = ["1min", "5min", "15min"]
    start: datetime
    end: datetime


class ProviderCapabilityCheckRequest(BaseModel):
    endpoint_keys: list[str] | None = None
    symbols: list[str] | None = None
    include_websocket: bool = False


class FMPQuoteIngestRequest(BaseModel):
    symbols: list[str] | None = None


class FMPBarsIngestRequest(BaseModel):
    symbols: list[str] | None = None
    intervals: list[Literal["1min", "5min", "15min"]] | None = None
    start: datetime
    end: datetime


class FMPIncrementalIntradayRequest(BaseModel):
    symbols: list[str] | None = None
    intervals: list[Literal["1min", "5min", "15min"]] | None = None
    end: datetime | None = None


class ProviderExportRequest(BaseModel):
    kind: Literal["json", "csv", "xlsx"] = "json"


class TrainRequest(BaseModel):
    model_type: str = "statistical_evidence_baseline"
    symbols: list[str] | None = None
    training_start: datetime
    training_end: datetime
    min_samples: int = 30
    activate_if_passes: bool = False
    intervals: list[Literal["1min", "5min", "15min"]] | None = None
    setup_types: list[str] | None = None
    sides: list[str] | None = None
    replay_run_ids: list[str] | None = None
    counterfactual_replay_run_ids: list[str] | None = None
    portfolio_replay_run_ids: list[str] | None = None
    replay_filter: dict[str, Any] | None = None
    outcome_source: str = "counterfactual_preferred"
    require_counterfactual: bool = False
    minimum_counterfactual_outcomes: int = 0
    maximum_portfolio_only_fraction: float = 1.0
    overlap_density_filters: list[str] | None = None
    concurrency_bucket_filters: list[str] | None = None
    sensitivity_required: bool = False
    minimum_observed_outcomes: int = 5
    minimum_cell_sample_size: int = 5
    shrinkage_strength: float = 20.0
    scoring_config: dict[str, Any] = Field(default_factory=dict)
    activation_criteria: dict[str, Any] = Field(default_factory=dict)
    validation_mode: str = "label_derived"
    allow_stale: bool = False


class BacktestRequest(BaseModel):
    symbols: list[str] | None = None
    start: datetime
    end: datetime
    model_version: str | None = None


class ReplayBacktestRequest(BaseModel):
    replay_purpose: str = "portfolio_execution"
    simulation_type: str | None = None
    symbols: list[str] | None = None
    intervals: list[Literal["1min", "5min", "15min"]] = ["1min"]
    start: datetime
    end: datetime
    session: str = "rth"
    candidate_setup_types: list[str] = Field(default_factory=list)
    sides: list[str] | str = "BOTH"
    max_hold_minutes: int = 60
    entry_mode: str = "next_bar_open"
    stop_mode: str = "candidate_context"
    target_mode: str = "candidate_targets"
    target_1_r: float = 1.0
    target_2_r: float = 1.5
    target_3_r: float = 2.5
    partial_exit_mode: str = "none"
    same_bar_stop_target_policy: str = "conservative_stop_first"
    intrabar_path_policy: str = "conservative"
    slippage_bps: float = 0.0
    spread_bps: float = 0.0
    commission_per_share: float = 0.0
    minimum_reward_risk: float = 1.0
    minimum_confidence: float | None = None
    allow_overlapping_trades: bool = False
    enforce_portfolio_constraints: bool | None = None
    enforce_symbol_overlap: bool | None = None
    max_open_trades_per_symbol: int = 1
    max_open_trades_portfolio: int = 10
    cooldown_bars_after_loss: int = 0
    cooldown_bars_after_trade: int = 0
    one_trade_per_setup_per_symbol_until_exit: bool = True
    no_trade_on_insufficient_context: bool = True
    market_regime_filter: list[str] = Field(default_factory=list)
    time_bucket_filter: list[str] = Field(default_factory=list)
    allow_stale: bool = False
    counterfactual_include_invalid_candidates: bool = False
    counterfactual_result_label: str = "candidate_quality_evidence"


class SensitivityRequest(BaseModel):
    slippage_bps_grid: list[float] | None = None
    spread_bps_grid: list[float] | None = None
    intrabar_path_policies: list[str] | None = None
    same_bar_stop_target_policies: list[str] | None = None
    minimum_robustness_score: float = 0.70
    minimum_total_trades: int = 5
    minimum_average_r: float = 0.0
    minimum_profit_factor: float = 1.0
    maximum_drawdown_r: float = -10.0


class BacktestComparisonRequest(BaseModel):
    replay_run_id: str
    label_run_id: str | None = None
    symbols: list[str] | None = None


class CounterfactualComparisonRequest(BaseModel):
    counterfactual_replay_run_id: str
    portfolio_replay_run_id: str
    symbols: list[str] | None = None
    setups: list[str] | None = None


class CalibrationAuditRequest(BaseModel):
    validation_report_id: str | None = None
    replay_run_ids: list[str] | None = None
    outcome_source: str = "counterfactual_preferred"
    score_bins: list[float] | None = None
    minimum_high_grade_samples: int = 5
    require_monotonic_score_bins: bool = False
    require_take_outperforms_watch: bool = False
    minimum_rank_correlation_score: float | None = None
    max_allowed_calibration_warnings: int | None = None


class ModelComparisonRequest(BaseModel):
    model_versions: list[str]
    validation_report_ids: list[str] | None = None
    calibration_audit_ids: list[str] | None = None
    replay_run_ids: list[str] | None = None
    comparison_window: dict[str, Any] | None = None


class ReplayWindowSetRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    symbols: list[str] | None = None
    intervals: list[Literal["1min", "5min", "15min"]] = ["1min"]
    setup_types: list[str] = Field(default_factory=list)
    start: datetime | None = None
    end: datetime | None = None
    window_mode: Literal["daily", "rolling", "anchored", "custom"] = "daily"
    window_size_days: int | None = None
    step_days: int | None = None
    train_size_days: int | None = None
    validation_size_days: int | None = None
    min_training_days: int | None = None
    embargo_minutes: int = 0
    session: str = "rth"
    windows: list[dict[str, Any]] | None = None
    replay_config: dict[str, Any] = Field(default_factory=dict)
    sensitivity_config: dict[str, Any] = Field(default_factory=dict)
    validation_config: dict[str, Any] = Field(default_factory=dict)
    model_version: str | None = None
    run_immediately: bool = False
    allow_large_window_count: bool = False
    max_windows: int = 50


class ReplayWindowRunRequest(BaseModel):
    rerun: bool = False
    run_replay: bool = True
    run_calibration: bool = False


class CalibrationDriftRequest(BaseModel):
    calibration_audit_ids: list[str] | None = None
    window_set_id: str | None = None
    window_result_ids: list[str] | None = None
    replay_run_ids: list[str] | None = None
    minimum_recent_high_grade_samples: int = 5
    rank_correlation_drop_threshold: float = 0.10
    limit: int = 20


class ModelReviewRequest(BaseModel):
    validation_report_ids: list[str] | None = None
    calibration_audit_ids: list[str] | None = None
    drift_report_ids: list[str] | None = None
    sensitivity_run_ids: list[str] | None = None
    comparison_ids: list[str] | None = None
    window_set_id: str | None = None
    calibration_required: bool = False


class ResearchCycleRequest(BaseModel):
    cycle_date: str | None = None
    cycle_type: str = "daily"
    symbols: list[str] | None = None
    intervals: list[Literal["1min", "5min", "15min"]] = ["1min"]
    start: datetime | None = None
    end: datetime | None = None
    session: str = "rth"
    data_cutoff_timestamp: datetime | None = None
    active_model_version: str | None = None
    challenger_model_version: str | None = None
    replay_run_ids: list[str] | None = None
    counterfactual_replay_run_ids: list[str] | None = None
    portfolio_replay_run_ids: list[str] | None = None
    sensitivity_run_ids: list[str] | None = None
    validation_report_ids: list[str] | None = None
    calibration_audit_ids: list[str] | None = None
    drift_report_ids: list[str] | None = None
    model_review_report_ids: list[str] | None = None
    window_set_config: dict[str, Any] | None = None
    challenger_training_config: dict[str, Any] = Field(default_factory=dict)
    train_challenger: bool = False
    validate_challenger: bool = False
    require_counterfactual: bool = False
    require_portfolio_validation: bool = False
    require_sensitivity: bool = False
    require_calibration: bool = False
    require_model_review: bool = False
    allow_stale: bool = False
    max_window_count: int = 20
    dry_run: bool = False
    refresh_data: bool = False
    export_reports: bool = False
    run_now: bool = False


class ResearchCycleRunRequest(BaseModel):
    train_challenger: bool | None = None
    validate_challenger: bool | None = None
    allow_stale: bool | None = None
    refresh_data: bool | None = None
    export_reports: bool | None = None
    window_set_config: dict[str, Any] | None = None
    challenger_training_config: dict[str, Any] | None = None


class ProposalDecisionRequest(BaseModel):
    actor: str | None = None
    reason_codes: list[str] | None = None


class ProposalActivationRequest(BaseModel):
    actor: str | None = None
    confirm_manual_activation: bool = False
    validation_mode: str | None = None
    calibration_audit_required: bool = False


class SchedulerJobRequest(BaseModel):
    job_type: Literal[
        "research_cycle_dry_run",
        "research_cycle_run",
        "data_quality_report",
        "export_research_cycle",
        "export_operations_status",
        "fmp_capability_check",
        "fmp_quote_snapshot",
        "fmp_eod_refresh",
        "fmp_intraday_refresh",
        "fmp_incremental_intraday_refresh",
    ]
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 100
    scheduled_for: datetime | None = None
    created_by: str | None = None


class SchedulerRunPendingRequest(BaseModel):
    max_jobs: int = 3


class ScoreCandidatesRequest(BaseModel):
    candidate_ids: list[str] | None = None
    candidates: list[dict[str, Any]] | None = None
    persist_audit: bool = True


class ExportRequest(BaseModel):
    kind: str
    date: str | None = None
    run_id: str | None = None


class ScannerStartRequest(BaseModel):
    symbols: list[str] | None = None
    confidence_threshold: float | None = None
