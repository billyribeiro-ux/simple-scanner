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
