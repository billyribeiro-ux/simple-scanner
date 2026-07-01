from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
from hashlib import sha256
from typing import Any

from app.utils.time import UTC


@dataclass(frozen=True)
class ReplayWindow:
    window_index: int
    window_mode: str
    train_start: datetime | None
    train_end: datetime | None
    validation_start: datetime | None
    validation_end: datetime | None
    test_start: datetime | None
    test_end: datetime | None
    replay_start: datetime
    replay_end: datetime
    embargo_minutes: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key, value in list(payload.items()):
            if isinstance(value, datetime):
                payload[key] = value.isoformat()
        payload["window_id"] = stable_window_id(payload)
        return payload


def generate_replay_windows(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    mode = str(payload.get("window_mode") or payload.get("mode") or "custom").lower()
    start = _parse_datetime(payload.get("start"))
    end = _parse_datetime(payload.get("end"))
    embargo_minutes = max(0, int(payload.get("embargo_minutes") or 0))
    warnings: list[str] = []

    if mode == "custom":
        return _custom_windows(payload, embargo_minutes)
    if start is None or end is None:
        return [], ["start_and_end_required"]
    if end <= start:
        return [], ["end_must_be_after_start"]

    if mode == "daily":
        windows = _daily_windows(start, end, embargo_minutes)
    elif mode == "rolling":
        windows = _rolling_windows(start, end, payload, embargo_minutes)
    elif mode == "anchored":
        windows = _anchored_windows(start, end, payload, embargo_minutes)
    else:
        return [], [f"unsupported_window_mode:{mode}"]

    if not windows:
        warnings.append("no_windows_generated")
    max_windows = int(payload.get("max_generated_windows") or 250)
    if len(windows) > max_windows:
        warnings.append("window_count_exceeds_default_limit")
    return [window.to_dict() for window in windows], warnings


def stable_window_id(payload: dict[str, Any]) -> str:
    parts = [
        payload.get("window_mode"),
        payload.get("window_index"),
        payload.get("train_start"),
        payload.get("train_end"),
        payload.get("validation_start"),
        payload.get("validation_end"),
        payload.get("test_start"),
        payload.get("test_end"),
        payload.get("replay_start"),
        payload.get("replay_end"),
    ]
    digest = sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:24]
    return f"replay_window_{digest}"


def _daily_windows(start: datetime, end: datetime, embargo_minutes: int) -> list[ReplayWindow]:
    windows: list[ReplayWindow] = []
    current = datetime.combine(start.date(), time.min, tzinfo=UTC)
    index = 1
    while current < end:
        next_day = current + timedelta(days=1)
        replay_start = max(current, start)
        replay_end = min(next_day, end)
        window_warnings = _window_warnings(replay_start, replay_end)
        windows.append(
            ReplayWindow(
                window_index=index,
                window_mode="daily",
                train_start=None,
                train_end=None,
                validation_start=replay_start,
                validation_end=replay_end,
                test_start=replay_start,
                test_end=replay_end,
                replay_start=replay_start,
                replay_end=replay_end,
                embargo_minutes=embargo_minutes,
                warnings=window_warnings,
            )
        )
        current = next_day
        index += 1
    return windows


def _rolling_windows(start: datetime, end: datetime, payload: dict[str, Any], embargo_minutes: int) -> list[ReplayWindow]:
    window_size_days = max(1, int(payload.get("window_size_days") or 5))
    step_days = max(1, int(payload.get("step_days") or window_size_days))
    train_size_days = max(0, int(payload.get("train_size_days") or payload.get("training_window_days") or window_size_days))
    validation_size_days = max(0, int(payload.get("validation_size_days") or 0))
    duration = timedelta(days=window_size_days)
    step = timedelta(days=step_days)
    windows: list[ReplayWindow] = []
    current = start
    index = 1
    while current < end:
        replay_end = min(current + duration, end)
        train_start = current - timedelta(days=train_size_days) if train_size_days else None
        train_end = current - timedelta(minutes=embargo_minutes) if train_size_days else None
        validation_start = current - timedelta(days=validation_size_days) if validation_size_days else current
        validation_end = current - timedelta(minutes=embargo_minutes) if validation_size_days else replay_end
        windows.append(
            ReplayWindow(
                window_index=index,
                window_mode="rolling",
                train_start=train_start,
                train_end=train_end,
                validation_start=validation_start,
                validation_end=validation_end,
                test_start=current,
                test_end=replay_end,
                replay_start=current,
                replay_end=replay_end,
                embargo_minutes=embargo_minutes,
                warnings=_window_warnings(current, replay_end),
            )
        )
        current += step
        index += 1
    return windows


def _anchored_windows(start: datetime, end: datetime, payload: dict[str, Any], embargo_minutes: int) -> list[ReplayWindow]:
    min_training_days = max(1, int(payload.get("min_training_days") or payload.get("training_window_days") or 5))
    window_size_days = max(1, int(payload.get("window_size_days") or 5))
    step_days = max(1, int(payload.get("step_days") or window_size_days))
    current = start + timedelta(days=min_training_days) + timedelta(minutes=embargo_minutes)
    windows: list[ReplayWindow] = []
    index = 1
    while current < end:
        replay_end = min(current + timedelta(days=window_size_days), end)
        train_end = current - timedelta(minutes=embargo_minutes)
        windows.append(
            ReplayWindow(
                window_index=index,
                window_mode="anchored",
                train_start=start,
                train_end=train_end,
                validation_start=train_end,
                validation_end=current,
                test_start=current,
                test_end=replay_end,
                replay_start=current,
                replay_end=replay_end,
                embargo_minutes=embargo_minutes,
                warnings=_window_warnings(current, replay_end),
            )
        )
        current += timedelta(days=step_days)
        index += 1
    return windows


def _custom_windows(payload: dict[str, Any], embargo_minutes: int) -> tuple[list[dict[str, Any]], list[str]]:
    raw_windows = list(payload.get("windows") or payload.get("custom_windows") or [])
    warnings: list[str] = []
    windows: list[ReplayWindow] = []
    for index, raw in enumerate(raw_windows, start=1):
        row = dict(raw)
        replay_start = _parse_datetime(row.get("replay_start") or row.get("start") or payload.get("start"))
        replay_end = _parse_datetime(row.get("replay_end") or row.get("end") or payload.get("end"))
        if replay_start is None or replay_end is None:
            warnings.append(f"window_{index}_start_or_end_missing")
            continue
        window_embargo = max(0, int(row.get("embargo_minutes") if row.get("embargo_minutes") is not None else embargo_minutes))
        train_end = _parse_datetime(row.get("train_end"))
        validation_start = _parse_datetime(row.get("validation_start"))
        if window_embargo and train_end and validation_start and train_end > validation_start - timedelta(minutes=window_embargo):
            warnings.append(f"window_{index}_embargo_overlap")
        windows.append(
            ReplayWindow(
                window_index=int(row.get("window_index") or index),
                window_mode="custom",
                train_start=_parse_datetime(row.get("train_start")),
                train_end=train_end,
                validation_start=validation_start,
                validation_end=_parse_datetime(row.get("validation_end")),
                test_start=_parse_datetime(row.get("test_start")) or replay_start,
                test_end=_parse_datetime(row.get("test_end")) or replay_end,
                replay_start=replay_start,
                replay_end=replay_end,
                embargo_minutes=window_embargo,
                warnings=_window_warnings(replay_start, replay_end),
            )
        )
    if not raw_windows:
        warnings.append("custom_windows_required")
    return [window.to_dict() for window in windows], warnings


def _window_warnings(start: datetime, end: datetime) -> list[str]:
    warnings: list[str] = []
    if end <= start:
        warnings.append("insufficient_data_window")
    if end - start < timedelta(minutes=5):
        warnings.append("short_replay_window")
    return warnings


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=UTC)
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
