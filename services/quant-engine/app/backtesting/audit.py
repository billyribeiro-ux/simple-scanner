from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from hashlib import sha256
from typing import Any

from app.schemas.market import Bar

REPLAY_CONFIG_VERSION = "replay_config.v1"
CANDIDATE_CONFIG_VERSION = "candidate_signals.v1"
REPLAY_AUDIT_VERSION = "replay_audit.v1"

SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "database_url",
    "fmp",
)


def stable_json(payload: Any) -> str:
    return json.dumps(_scrub(_jsonable(payload)), sort_keys=True, separators=(",", ":"), allow_nan=False)


def stable_hash(payload: Any) -> str:
    return sha256(stable_json(payload).encode("utf-8")).hexdigest()


def replay_config_hash(config_payload: dict[str, Any]) -> str:
    return stable_hash({"version": REPLAY_CONFIG_VERSION, "config": config_payload})


def candidate_fingerprint(candidates: list[dict[str, Any]]) -> str:
    rows = []
    for candidate in candidates:
        rows.append(
            {
                "candidate_id": candidate.get("candidate_id"),
                "symbol": candidate.get("symbol"),
                "interval": candidate.get("interval") or "1min",
                "timestamp_utc": candidate.get("timestamp_utc") or candidate.get("timestamp"),
                "side": candidate.get("side"),
                "setup_type": candidate.get("setup_type"),
                "confidence_score": candidate.get("confidence_score") or candidate.get("signal_score"),
                "expected_r": candidate.get("expected_r"),
                "entry_context": candidate.get("entry_context") or {},
                "invalidation_context": candidate.get("invalidation_context") or {},
                "targets": {
                    "target_1": candidate.get("target_1"),
                    "target_2": candidate.get("target_2"),
                    "target_3": candidate.get("target_3"),
                    "stop_price": candidate.get("stop_price"),
                },
                "reason_codes": candidate.get("reason_codes") or [],
                "warning_codes": candidate.get("warning_codes") or [],
            }
        )
    return stable_hash({"version": CANDIDATE_CONFIG_VERSION, "candidates": sorted(rows, key=stable_json)})


def bar_fingerprint(bars: list[Bar]) -> str:
    rows = [
        {
            "symbol": bar.symbol,
            "interval": bar.interval,
            "timestamp_utc": bar.timestamp_utc.isoformat(),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "vwap": bar.vwap,
            "source": bar.source,
            "quality_flags": bar.quality_flags,
        }
        for bar in bars
    ]
    return stable_hash({"version": "bars.ohlcv.v1", "bars": sorted(rows, key=stable_json)})


def feature_fingerprint(features: list[dict[str, Any]]) -> str:
    rows = []
    for feature in features:
        rows.append(
            {
                "symbol": feature.get("symbol"),
                "interval": feature.get("interval") or "1min",
                "timestamp_utc": feature.get("timestamp_utc") or feature.get("timestamp"),
                "feature_set_version": feature.get("feature_set_version"),
                "market_regime": feature.get("market_regime"),
                "ticker_regime": feature.get("ticker_regime"),
                "payload_hash": stable_hash(feature),
            }
        )
    return stable_hash({"version": "features.fingerprint.v1", "features": sorted(rows, key=stable_json)})


def replay_input_fingerprint(
    bars: list[Bar],
    features: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    config_payload: dict[str, Any],
) -> str:
    return stable_hash(
        {
            "version": REPLAY_AUDIT_VERSION,
            "config_hash": replay_config_hash(config_payload),
            "bar_fingerprint": bar_fingerprint(bars),
            "feature_fingerprint": feature_fingerprint(features),
            "candidate_fingerprint": candidate_fingerprint(candidates),
        }
    )


def git_commit() -> str | None:
    git_path = shutil.which("git")
    if git_path is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603 - fixed git executable path from shutil.which and fixed args.
            [git_path, "rev-parse", "--short=12", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception:
        return None
    commit = result.stdout.strip()
    return commit or None


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return value if value == value and value not in (float("inf"), float("-inf")) else None
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            lower_key = str(key).lower()
            if any(part in lower_key for part in SENSITIVE_KEY_PARTS):
                output[str(key)] = "[redacted]"
            else:
                output[str(key)] = _scrub(item)
        return output
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    text = str(value).lower() if isinstance(value, str) else ""
    if any(part in text for part in ("fmp_api_key", "database_url", "password=")):
        return "[redacted]"
    return value
