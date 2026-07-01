from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


SideValue = str
OutcomeValue = str


@dataclass(frozen=True)
class Bar:
    symbol: str
    interval: str
    timestamp_utc: datetime
    timestamp_et: datetime
    session_date: date
    session: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str = "synthetic"
    vwap: float | None = None
    data_quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeatureRow:
    symbol: str
    interval: str
    timestamp_utc: datetime
    timestamp_et: datetime
    session_date: date
    feature_set_version: str
    data_quality_flags: tuple[str, ...]
    values: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "symbol": self.symbol,
            "interval": self.interval,
            "timestamp": self.timestamp_utc.isoformat(),
            "timestamp_utc": self.timestamp_utc,
            "timestamp_et": self.timestamp_et,
            "session_date": self.session_date.isoformat(),
            "feature_set_version": self.feature_set_version,
            "data_quality_flags": list(self.data_quality_flags),
        }
        payload.update(self.values)
        return payload


@dataclass(frozen=True)
class CandidateSignal:
    symbol: str
    interval: str
    timestamp_utc: datetime
    timestamp_et: datetime
    session_date: date
    side: SideValue
    setup_type: str
    entry_context: dict[str, Any]
    invalidation_context: dict[str, Any]
    required_feature_names: tuple[str, ...]
    reason_codes: tuple[str, ...]
    warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class LabelRow:
    symbol: str
    interval: str
    timestamp_utc: datetime
    side: SideValue
    setup_type: str
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
    outcome: OutcomeValue
    label_config_version: str
    market_regime: str = "mixed_uncertain"
    exit_timestamp_utc: datetime | None = None
    warning_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SimulatedTrade:
    trade_id: str
    symbol: str
    interval: str
    side: SideValue
    setup_type: str
    entry_timestamp_utc: datetime
    exit_timestamp_utc: datetime
    entry_price: float
    exit_price: float
    stop_price: float
    target_1: float
    target_2: float
    target_3: float
    realized_r: float
    max_favorable_excursion: float
    max_adverse_excursion: float
    outcome: OutcomeValue
    market_regime: str
    time_bucket: str
    exit_reason: str
    duration_bars: int


@dataclass(frozen=True)
class ValidationSplit:
    train_start: datetime
    train_end: datetime
    validation_start: datetime
    validation_end: datetime
    test_start: datetime
    test_end: datetime
    embargo_minutes: int = 0


@dataclass(frozen=True)
class WalkForwardWindow:
    window_id: str
    split: ValidationSplit
    metrics: dict[str, Any] = field(default_factory=dict)
    accepted: bool = False
    rejection_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ValidationReport:
    summary: dict[str, Any]
    windows: tuple[WalkForwardWindow, ...]
    per_symbol: dict[str, dict[str, Any]]
    per_setup: dict[str, dict[str, Any]]
    per_regime: dict[str, dict[str, Any]]
    per_time_bucket: dict[str, dict[str, Any]]
    leakage_warnings: tuple[str, ...]
    activation_decision: str
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ModelRun:
    model_version: str
    model_type: str
    feature_set_version: str
    label_config_version: str
    training_window: dict[str, str]
    validation_window: dict[str, str] | None
    test_window: dict[str, str] | None
    symbols: tuple[str, ...]
    setup_types: tuple[str, ...]
    metrics: dict[str, Any]
    activation_decision: str
    rejection_reasons: tuple[str, ...]
    created_at: datetime
    code_version: str | None = None


@dataclass(frozen=True)
class SignalDecision:
    candidate: CandidateSignal
    confidence_score: float
    expected_r: float
    decision: str
    reason_codes: tuple[str, ...]
    warning_codes: tuple[str, ...] = ()
