from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Side(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"
    NO_TRADE = "NO_TRADE"


class Outcome(StrEnum):
    WIN = "WIN"
    LOSS = "LOSS"
    NEUTRAL = "NEUTRAL"


class SignalStatus(StrEnum):
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


class TrainRequest(BaseModel):
    symbols: list[str] | None = None
    training_start: datetime
    training_end: datetime
    min_samples: int = 30
    activate_if_passes: bool = False


class BacktestRequest(BaseModel):
    symbols: list[str] | None = None
    start: datetime
    end: datetime
    model_version: str | None = None


class ExportRequest(BaseModel):
    kind: str
    date: str | None = None
    run_id: str | None = None


class ScannerStartRequest(BaseModel):
    symbols: list[str] | None = None
    confidence_threshold: float | None = None
