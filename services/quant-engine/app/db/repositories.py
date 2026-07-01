from __future__ import annotations

import builtins
import json
import math
import os
import re
import sqlite3
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Any
from zipfile import ZipFile

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine, make_url
except ModuleNotFoundError:  # pragma: no cover - no-venv pure quant compatibility
    create_engine = None
    text = None
    Engine = Any  # type: ignore[misc,assignment]
    make_url = None

from app.config import Settings, get_settings
from app.data.symbols import normalize_symbol
from app.schemas.market import Bar, Label, Outcome, Side, Signal, SignalStatus
from app.utils.time import UTC

EXPECTED_TABLES = {
    "active_models",
    "alembic_version",
    "bars",
    "backtest_comparisons",
    "candidate_signals",
    "candidate_score_audits",
    "closed_signals",
    "daily_reviews",
    "exports",
    "features",
    "labels",
    "live_signals",
    "model_artifacts",
    "model_calibration_audits",
    "model_calibration_bins",
    "model_comparisons",
    "model_evidence_cells",
    "model_runs",
    "pipeline_build_windows",
    "provider_requests",
    "replay_runs",
    "replay_sensitivity_runs",
    "replay_sensitivity_scenarios",
    "scanner_runs",
    "simulated_trades",
    "symbols",
    "validation_reports",
    "validation_windows",
}
EXPECTED_ALEMBIC_REVISION = "0006_phase9_calibration"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if hasattr(value, "model_dump"):
        return _to_jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(item) for item in value]
    return value


def _json_dumps(payload: Any) -> str:
    return json.dumps(_to_jsonable(payload), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _json_loads(payload: str | None) -> Any:
    if isinstance(payload, (dict, list)):
        return payload
    if not payload:
        return {}
    return json.loads(payload)


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _maybe_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    return _parse_datetime(value)


def _stable_id(prefix: str, *parts: Any) -> str:
    digest = sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:32]
    return f"{prefix}_{digest}"


def _file_sha256(path: Path | str) -> str | None:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        return None
    digest = sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _xlsx_sheet_names(path: Path | str) -> list[str]:
    file_path = Path(path)
    if file_path.suffix.lower() != ".xlsx" or not file_path.exists():
        return []
    try:
        with ZipFile(file_path) as archive:
            workbook_xml = archive.read("xl/workbook.xml").decode("utf-8", errors="ignore")
    except Exception:
        return []
    return re.findall(r'<sheet[^>]+name="([^"]+)"', workbook_xml)


def _payload(obj: Any) -> dict[str, Any]:
    data = _to_jsonable(obj)
    if isinstance(data, dict):
        return data
    raise TypeError(f"Expected mapping-like payload, got {type(obj).__name__}")


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _coerce_bar(payload: dict[str, Any]) -> Bar:
    data = dict(payload)
    for key in ("timestamp_utc", "timestamp_et", "ingestion_time"):
        if data.get(key) is not None:
            data[key] = _parse_datetime(data[key])
    return Bar(**data)


def _coerce_label(payload: dict[str, Any]) -> Label:
    data = dict(payload)
    timestamp = data.get("timestamp") or data.get("timestamp_utc")
    data["timestamp"] = _parse_datetime(timestamp)
    data["side"] = data["side"] if isinstance(data.get("side"), Side) else Side(str(data["side"]))
    data["outcome"] = data["outcome"] if isinstance(data.get("outcome"), Outcome) else Outcome(str(data["outcome"]))
    return Label(
        label_id=str(data["label_id"]),
        symbol=str(data["symbol"]),
        timestamp=data["timestamp"],
        side=data["side"],
        entry_price=float(data["entry_price"]),
        stop_price=float(data["stop_price"]),
        target_1=float(data["target_1"]),
        target_2=float(data["target_2"]),
        target_3=float(data["target_3"]),
        max_favorable_excursion=float(data.get("max_favorable_excursion", 0.0)),
        max_adverse_excursion=float(data.get("max_adverse_excursion", 0.0)),
        hit_target_1=bool(data.get("hit_target_1")),
        hit_target_2=bool(data.get("hit_target_2")),
        hit_target_3=bool(data.get("hit_target_3")),
        hit_stop=bool(data.get("hit_stop")),
        time_to_target=data.get("time_to_target"),
        time_to_stop=data.get("time_to_stop"),
        realized_r=float(data.get("realized_r", 0.0)),
        outcome=data["outcome"],
        setup_type=str(data.get("setup_type", "unknown")),
        market_regime=str(data.get("market_regime", "mixed_uncertain")),
    )


def _coerce_signal(payload: dict[str, Any]) -> Signal:
    data = dict(payload)
    for key in ("timestamp", "training_start", "training_end"):
        if data.get(key) is not None:
            data[key] = _parse_datetime(data[key])
    data["side"] = data["side"] if isinstance(data.get("side"), Side) else Side(str(data["side"]))
    if data.get("status") is not None and not isinstance(data.get("status"), SignalStatus):
        data["status"] = SignalStatus(str(data["status"]))
    return Signal(**data)


class PersistenceConfigurationError(RuntimeError):
    def __init__(self, message: str, safe_info: dict[str, Any]) -> None:
        super().__init__(message)
        self.safe_info = safe_info


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _sync_postgres_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def _database_descriptor(database_url: str) -> dict[str, Any]:
    if make_url is None:
        return {"database_driver": "unknown"}
    try:
        parsed = make_url(_sync_postgres_url(database_url))
    except Exception:
        return {"database_driver": "unknown"}
    return {
        "database_driver": parsed.drivername,
        "database_host": parsed.host,
        "database_port": parsed.port,
        "database_name": parsed.database,
    }


def _convert_qmark_sql(sql: str) -> tuple[str, list[str]]:
    names: list[str] = []
    parts = sql.split("?")
    if len(parts) == 1:
        return sql, names
    converted = [parts[0]]
    for index, part in enumerate(parts[1:]):
        name = f"p{index}"
        names.append(name)
        converted.append(f":{name}")
        converted.append(part)
    return "".join(converted), names


def _bind_params(names: list[str], params: Any) -> dict[str, Any]:
    if isinstance(params, dict):
        return params
    values = list(params or [])
    return {name: values[index] for index, name in enumerate(names)}


class _Row(dict[str, Any]):
    pass


class _Result:
    def __init__(self, result: Any) -> None:
        self.result = result

    def fetchall(self) -> list[_Row]:
        return [_Row(dict(row._mapping)) for row in self.result.fetchall()]

    def fetchone(self) -> _Row | None:
        row = self.result.fetchone()
        return _Row(dict(row._mapping)) if row is not None else None


class SQLiteStore:
    """Small durable local store used by the API path when Postgres is not configured."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path) if str(path) != ":memory:" else Path(":memory:")
        self._memory_connection: sqlite3.Connection | None = None
        self._lock = RLock()
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        if str(self.path) == ":memory:":
            if self._memory_connection is None:
                self._memory_connection = sqlite3.connect(":memory:")
                self._memory_connection.row_factory = sqlite3.Row
                self._memory_connection.execute("PRAGMA foreign_keys = ON")
            return self._memory_connection
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        with self._lock:
            connection = self.connect()
            try:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS symbols (
                        symbol TEXT PRIMARY KEY,
                        name TEXT,
                        exchange TEXT,
                        asset_type TEXT DEFAULT 'equity',
                        active INTEGER DEFAULT 1,
                        provider TEXT DEFAULT 'fmp',
                        metadata_json TEXT DEFAULT '{}',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS bars (
                        id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        interval TEXT NOT NULL,
                        timestamp_utc TEXT NOT NULL,
                        timestamp_et TEXT,
                        session_date TEXT,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        volume INTEGER NOT NULL,
                        vwap REAL,
                        source TEXT NOT NULL,
                        quality_flags_json TEXT DEFAULT '[]',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(symbol, interval, timestamp_utc, source)
                    );

                    CREATE INDEX IF NOT EXISTS ix_bars_lookup
                        ON bars(symbol, interval, timestamp_utc);

                    CREATE TABLE IF NOT EXISTS features (
                        id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        interval TEXT NOT NULL,
                        timestamp_utc TEXT NOT NULL,
                        session_date TEXT,
                        feature_set_version TEXT NOT NULL,
                        market_regime TEXT,
                        ticker_regime TEXT,
                        data_quality_flags_json TEXT DEFAULT '[]',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(symbol, interval, timestamp_utc, feature_set_version)
                    );

                    CREATE INDEX IF NOT EXISTS ix_features_lookup
                        ON features(symbol, interval, timestamp_utc);

                    CREATE TABLE IF NOT EXISTS candidate_signals (
                        candidate_id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        interval TEXT NOT NULL,
                        timestamp_utc TEXT NOT NULL,
                        side TEXT NOT NULL,
                        setup_type TEXT NOT NULL,
                        reason_codes_json TEXT DEFAULT '[]',
                        warning_codes_json TEXT DEFAULT '[]',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(symbol, interval, timestamp_utc, side, setup_type)
                    );

                    CREATE TABLE IF NOT EXISTS labels (
                        label_id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        interval TEXT NOT NULL DEFAULT '1min',
                        timestamp_utc TEXT NOT NULL,
                        side TEXT NOT NULL,
                        setup_type TEXT NOT NULL,
                        label_config_version TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        stop_price REAL NOT NULL,
                        target_1 REAL NOT NULL,
                        target_2 REAL NOT NULL,
                        target_3 REAL NOT NULL,
                        realized_r REAL NOT NULL,
                        outcome TEXT NOT NULL,
                        market_regime TEXT,
                        exit_timestamp_utc TEXT,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(symbol, interval, timestamp_utc, side, setup_type, label_config_version)
                    );

                    CREATE INDEX IF NOT EXISTS ix_labels_lookup
                        ON labels(symbol, timestamp_utc, setup_type);

                    CREATE TABLE IF NOT EXISTS validation_reports (
                        report_id TEXT PRIMARY KEY,
                        model_version TEXT,
                        purpose TEXT NOT NULL DEFAULT 'validation',
                        activation_decision TEXT NOT NULL,
                        rejection_reasons_json TEXT DEFAULT '[]',
                        summary_json TEXT DEFAULT '{}',
                        per_symbol_json TEXT DEFAULT '{}',
                        per_setup_json TEXT DEFAULT '{}',
                        per_regime_json TEXT DEFAULT '{}',
                        leakage_warnings_json TEXT DEFAULT '[]',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS validation_windows (
                        window_id TEXT PRIMARY KEY,
                        report_id TEXT NOT NULL,
                        window_name TEXT NOT NULL,
                        train_start TEXT,
                        train_end TEXT,
                        validation_start TEXT,
                        validation_end TEXT,
                        test_start TEXT,
                        test_end TEXT,
                        accepted INTEGER NOT NULL DEFAULT 0,
                        metrics_json TEXT DEFAULT '{}',
                        rejection_reasons_json TEXT DEFAULT '[]',
                        payload_json TEXT NOT NULL,
                        FOREIGN KEY(report_id) REFERENCES validation_reports(report_id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS model_runs (
                        model_version TEXT PRIMARY KEY,
                        model_type TEXT NOT NULL,
                        feature_set_version TEXT,
                        label_config_version TEXT,
                        training_start TEXT,
                        training_end TEXT,
                        activation_decision TEXT NOT NULL,
                        active INTEGER NOT NULL DEFAULT 0,
                        metrics_json TEXT DEFAULT '{}',
                        validation_metrics_json TEXT DEFAULT '{}',
                        payload_json TEXT NOT NULL,
                        artifact_path TEXT,
                        code_version TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS model_artifacts (
                        artifact_id TEXT PRIMARY KEY,
                        model_version TEXT NOT NULL,
                        artifact_type TEXT NOT NULL,
                        path TEXT NOT NULL,
                        sha256 TEXT,
                        payload_json TEXT DEFAULT '{}',
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(model_version) REFERENCES model_runs(model_version) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS model_evidence_cells (
                        id TEXT PRIMARY KEY,
                        model_version TEXT NOT NULL,
                        cell_key TEXT NOT NULL,
                        dimensions_json TEXT DEFAULT '{}',
                        hierarchy_level TEXT NOT NULL,
                        parent_cell_key TEXT,
                        metrics_json TEXT DEFAULT '{}',
                        sample_size INTEGER NOT NULL DEFAULT 0,
                        observed_outcome_count INTEGER NOT NULL DEFAULT 0,
                        average_r REAL NOT NULL DEFAULT 0,
                        median_r REAL NOT NULL DEFAULT 0,
                        profit_factor REAL NOT NULL DEFAULT 0,
                        max_drawdown_r REAL NOT NULL DEFAULT 0,
                        robustness_score REAL,
                        fragility_flags_json TEXT DEFAULT '[]',
                        evidence_quality_grade TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        UNIQUE(model_version, cell_key)
                    );

                    CREATE INDEX IF NOT EXISTS ix_model_evidence_cells_model_level
                        ON model_evidence_cells(model_version, hierarchy_level);

                    CREATE TABLE IF NOT EXISTS candidate_score_audits (
                        id TEXT PRIMARY KEY,
                        score_id TEXT NOT NULL UNIQUE,
                        model_version TEXT NOT NULL,
                        candidate_id TEXT,
                        symbol TEXT NOT NULL,
                        interval TEXT NOT NULL,
                        timestamp_utc TEXT NOT NULL,
                        side TEXT NOT NULL,
                        setup_type TEXT NOT NULL,
                        signal_quality_score REAL NOT NULL DEFAULT 0,
                        grade TEXT NOT NULL,
                        action TEXT NOT NULL,
                        expected_r_estimate REAL NOT NULL DEFAULT 0,
                        score_components_json TEXT DEFAULT '{}',
                        suppression_reasons_json TEXT DEFAULT '[]',
                        evidence_cell_keys_used_json TEXT DEFAULT '[]',
                        warnings_json TEXT DEFAULT '[]',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS ix_score_audits_model_created
                        ON candidate_score_audits(model_version, created_at);

                    CREATE INDEX IF NOT EXISTS ix_score_audits_symbol_ts
                        ON candidate_score_audits(symbol, timestamp_utc);

                    CREATE TABLE IF NOT EXISTS model_calibration_audits (
                        id TEXT PRIMARY KEY,
                        calibration_audit_id TEXT NOT NULL UNIQUE,
                        model_version TEXT NOT NULL,
                        validation_report_id TEXT,
                        replay_run_ids_json TEXT DEFAULT '[]',
                        outcome_source TEXT NOT NULL,
                        score_bins_json TEXT DEFAULT '[]',
                        grade_bins_json TEXT DEFAULT '[]',
                        action_bins_json TEXT DEFAULT '[]',
                        rank_correlation_score REAL NOT NULL DEFAULT 0,
                        monotonicity_pass INTEGER NOT NULL DEFAULT 0,
                        separation_metrics_json TEXT DEFAULT '{}',
                        stability_metrics_json TEXT DEFAULT '{}',
                        warnings_json TEXT DEFAULT '[]',
                        rejection_reasons_json TEXT DEFAULT '[]',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS ix_calibration_audits_model_created
                        ON model_calibration_audits(model_version, created_at);

                    CREATE TABLE IF NOT EXISTS model_calibration_bins (
                        id TEXT PRIMARY KEY,
                        calibration_audit_id TEXT NOT NULL,
                        bin_type TEXT NOT NULL,
                        bin_key TEXT NOT NULL,
                        sample_size INTEGER NOT NULL DEFAULT 0,
                        observed_average_r REAL NOT NULL DEFAULT 0,
                        observed_win_rate REAL NOT NULL DEFAULT 0,
                        profit_factor REAL NOT NULL DEFAULT 0,
                        max_drawdown_r REAL NOT NULL DEFAULT 0,
                        metrics_json TEXT DEFAULT '{}',
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS ix_calibration_bins_audit_type
                        ON model_calibration_bins(calibration_audit_id, bin_type);

                    CREATE TABLE IF NOT EXISTS model_comparisons (
                        comparison_id TEXT PRIMARY KEY,
                        comparison_type TEXT NOT NULL,
                        model_versions_json TEXT DEFAULT '[]',
                        validation_report_ids_json TEXT DEFAULT '[]',
                        calibration_audit_ids_json TEXT DEFAULT '[]',
                        replay_run_ids_json TEXT DEFAULT '[]',
                        summary_json TEXT DEFAULT '{}',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS ix_model_comparisons_created
                        ON model_comparisons(created_at);

                    CREATE TABLE IF NOT EXISTS active_models (
                        active_model_id TEXT PRIMARY KEY,
                        model_version TEXT NOT NULL,
                        model_type TEXT NOT NULL,
                        strategy_scope TEXT NOT NULL DEFAULT 'default',
                        activated_at TEXT NOT NULL,
                        validation_report_id TEXT,
                        payload_json TEXT NOT NULL,
                        UNIQUE(model_type, strategy_scope)
                    );

                    CREATE TABLE IF NOT EXISTS live_signals (
                        signal_id TEXT PRIMARY KEY,
                        scanner_run_id TEXT,
                        timestamp_utc TEXT NOT NULL,
                        ticker TEXT NOT NULL,
                        side TEXT NOT NULL,
                        setup_type TEXT NOT NULL,
                        confidence_score REAL NOT NULL,
                        expected_r REAL NOT NULL,
                        model_version TEXT NOT NULL,
                        status TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS ix_live_signals_latest
                        ON live_signals(timestamp_utc DESC, ticker);

                    CREATE TABLE IF NOT EXISTS closed_signals (
                        signal_id TEXT PRIMARY KEY,
                        closed_at TEXT NOT NULL,
                        exit_price REAL,
                        exit_reason TEXT,
                        realized_r REAL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS scanner_runs (
                        scanner_run_id TEXT PRIMARY KEY,
                        started_at TEXT NOT NULL,
                        stopped_at TEXT,
                        status TEXT NOT NULL,
                        symbols_json TEXT DEFAULT '[]',
                        confidence_threshold REAL,
                        model_version TEXT,
                        latest_error TEXT,
                        stats_json TEXT DEFAULT '{}',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS provider_requests (
                        request_id TEXT PRIMARY KEY,
                        provider TEXT NOT NULL,
                        endpoint TEXT NOT NULL,
                        method TEXT NOT NULL DEFAULT 'GET',
                        symbol TEXT,
                        interval TEXT,
                        started_at TEXT NOT NULL,
                        finished_at TEXT,
                        status TEXT NOT NULL,
                        response_status INTEGER,
                        row_count INTEGER,
                        cache_hit INTEGER DEFAULT 0,
                        error_message TEXT,
                        metadata_json TEXT DEFAULT '{}'
                    );

                    CREATE TABLE IF NOT EXISTS exports (
                        export_id TEXT PRIMARY KEY,
                        export_type TEXT NOT NULL,
                        format TEXT NOT NULL,
                        path TEXT NOT NULL,
                        row_count INTEGER NOT NULL DEFAULT 0,
                        source_run_id TEXT,
                        payload_json TEXT DEFAULT '{}',
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS replay_runs (
                        replay_run_id TEXT PRIMARY KEY,
                        simulation_type TEXT NOT NULL,
                        backend TEXT NOT NULL,
                        start TEXT,
                        end TEXT,
                        symbols_json TEXT DEFAULT '[]',
                        intervals_json TEXT DEFAULT '[]',
                        config_json TEXT DEFAULT '{}',
                        config_hash TEXT,
                        input_fingerprint TEXT,
                        candidate_fingerprint TEXT,
                        replay_config_version TEXT,
                        feature_set_version TEXT,
                        candidate_config_version TEXT,
                        label_config_version TEXT,
                        stale_window_status_json TEXT DEFAULT '{}',
                        summary_metrics_json TEXT DEFAULT '{}',
                        per_symbol_metrics_json TEXT DEFAULT '{}',
                        per_setup_metrics_json TEXT DEFAULT '{}',
                        per_regime_metrics_json TEXT DEFAULT '{}',
                        per_time_bucket_metrics_json TEXT DEFAULT '{}',
                        skip_breakdown_json TEXT DEFAULT '{}',
                        warnings_json TEXT DEFAULT '[]',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS ix_replay_runs_created_type
                        ON replay_runs(created_at, simulation_type);

                    CREATE INDEX IF NOT EXISTS ix_replay_runs_simulation_type
                        ON replay_runs(simulation_type);

                    CREATE INDEX IF NOT EXISTS ix_replay_runs_config_hash
                        ON replay_runs(config_hash);

                    CREATE TABLE IF NOT EXISTS replay_sensitivity_runs (
                        sensitivity_run_id TEXT PRIMARY KEY,
                        replay_run_id TEXT NOT NULL,
                        config_json TEXT DEFAULT '{}',
                        summary_json TEXT DEFAULT '{}',
                        gate_results_json TEXT DEFAULT '{}',
                        fragility_flags_json TEXT DEFAULT '[]',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS ix_sensitivity_runs_replay_created
                        ON replay_sensitivity_runs(replay_run_id, created_at);

                    CREATE TABLE IF NOT EXISTS replay_sensitivity_scenarios (
                        scenario_id TEXT PRIMARY KEY,
                        sensitivity_run_id TEXT NOT NULL,
                        replay_run_id TEXT NOT NULL,
                        slippage_bps REAL NOT NULL,
                        spread_bps REAL NOT NULL,
                        intrabar_path_policy TEXT NOT NULL,
                        same_bar_stop_target_policy TEXT NOT NULL,
                        summary_metrics_json TEXT DEFAULT '{}',
                        gate_results_json TEXT DEFAULT '{}',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS ix_sensitivity_scenarios_run_cost
                        ON replay_sensitivity_scenarios(sensitivity_run_id, slippage_bps, spread_bps);

                    CREATE TABLE IF NOT EXISTS backtest_comparisons (
                        comparison_id TEXT PRIMARY KEY,
                        label_run_id TEXT,
                        replay_run_id TEXT NOT NULL,
                        comparison_type TEXT NOT NULL,
                        summary_json TEXT DEFAULT '{}',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS ix_backtest_comparisons_replay_created
                        ON backtest_comparisons(replay_run_id, created_at);

                    CREATE TABLE IF NOT EXISTS simulated_trades (
                        trade_id TEXT PRIMARY KEY,
                        replay_run_id TEXT NOT NULL,
                        candidate_id TEXT,
                        symbol TEXT NOT NULL,
                        interval TEXT NOT NULL,
                        side TEXT NOT NULL,
                        setup_type TEXT NOT NULL,
                        signal_timestamp_utc TEXT NOT NULL,
                        entry_timestamp_utc TEXT,
                        exit_timestamp_utc TEXT,
                        entry_price REAL,
                        stop_price REAL,
                        target_1 REAL,
                        target_2 REAL,
                        target_3 REAL,
                        exit_price REAL,
                        exit_reason TEXT,
                        realized_r REAL NOT NULL DEFAULT 0,
                        mfe_r REAL NOT NULL DEFAULT 0,
                        mae_r REAL NOT NULL DEFAULT 0,
                        bars_held INTEGER NOT NULL DEFAULT 0,
                        minutes_held REAL NOT NULL DEFAULT 0,
                        same_bar_ambiguous INTEGER NOT NULL DEFAULT 0,
                        ambiguity_policy TEXT,
                        slippage_bps REAL NOT NULL DEFAULT 0,
                        spread_bps REAL NOT NULL DEFAULT 0,
                        commission REAL NOT NULL DEFAULT 0,
                        market_regime TEXT,
                        time_bucket TEXT,
                        signal_score REAL,
                        expected_r REAL,
                        status TEXT NOT NULL,
                        skip_reason TEXT,
                        metadata_json TEXT DEFAULT '{}',
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS ix_simulated_trades_run_symbol_setup_side
                        ON simulated_trades(replay_run_id, symbol, setup_type, side);

                    CREATE INDEX IF NOT EXISTS ix_simulated_trades_run_status
                        ON simulated_trades(replay_run_id, status);

                    CREATE INDEX IF NOT EXISTS ix_simulated_trades_signal_ts
                        ON simulated_trades(signal_timestamp_utc);

                    CREATE INDEX IF NOT EXISTS ix_candidate_signals_replay_lookup
                        ON candidate_signals(symbol, interval, timestamp_utc, setup_type, side);

                    CREATE INDEX IF NOT EXISTS ix_live_signals_symbol_ts_status_model
                        ON live_signals(ticker, timestamp_utc, status, model_version);

                    CREATE TABLE IF NOT EXISTS pipeline_build_windows (
                        build_window_id TEXT PRIMARY KEY,
                        artifact_type TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        interval TEXT NOT NULL,
                        session_date TEXT,
                        start TEXT,
                        end TEXT,
                        version TEXT NOT NULL,
                        dirty INTEGER NOT NULL DEFAULT 1,
                        stale_reason TEXT,
                        payload_json TEXT DEFAULT '{}',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(artifact_type, symbol, interval, session_date, version)
                    );

                    CREATE INDEX IF NOT EXISTS ix_pipeline_windows_lookup
                        ON pipeline_build_windows(artifact_type, symbol, interval, session_date, dirty);

                    CREATE TABLE IF NOT EXISTS daily_reviews (
                        review_id TEXT PRIMARY KEY,
                        review_date TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(review_date)
                    );
                    """
                )
                for statement in (
                    "ALTER TABLE replay_runs ADD COLUMN config_hash TEXT",
                    "ALTER TABLE replay_runs ADD COLUMN input_fingerprint TEXT",
                    "ALTER TABLE replay_runs ADD COLUMN candidate_fingerprint TEXT",
                    "ALTER TABLE replay_runs ADD COLUMN replay_config_version TEXT",
                    "ALTER TABLE replay_runs ADD COLUMN feature_set_version TEXT",
                    "ALTER TABLE replay_runs ADD COLUMN candidate_config_version TEXT",
                    "ALTER TABLE replay_runs ADD COLUMN label_config_version TEXT",
                    "ALTER TABLE replay_runs ADD COLUMN stale_window_status_json TEXT DEFAULT '{}'",
                ):
                    try:
                        connection.execute(statement)
                    except sqlite3.OperationalError as exc:
                        if "duplicate column name" not in str(exc).lower():
                            raise
                connection.commit()
            finally:
                if str(self.path) != ":memory:":
                    connection.close()

    def ping(self) -> bool:
        connection = self.connect()
        try:
            connection.execute("SELECT 1").fetchone()
            return True
        finally:
            if str(self.path) != ":memory:":
                connection.close()


class PostgresConnection:
    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def execute(self, sql: str, params: Any = None) -> _Result:
        converted, names = _convert_qmark_sql(sql)
        bound = _bind_params(names, params) if names else (params or {})
        if text is None:  # pragma: no cover - guarded by PostgresStore
            raise RuntimeError("SQLAlchemy is not installed")
        return _Result(self.connection.execute(text(converted), bound))

    def executemany(self, sql: str, rows: Iterable[Any]) -> _Result | None:
        row_values = list(rows)
        if not row_values:
            return None
        converted, names = _convert_qmark_sql(sql)
        bound_rows = [_bind_params(names, row) for row in row_values]
        if text is None:  # pragma: no cover - guarded by PostgresStore
            raise RuntimeError("SQLAlchemy is not installed")
        return _Result(self.connection.execute(text(converted), bound_rows))

    def commit(self) -> None:
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


class PostgresStore:
    def __init__(self, database_url: str) -> None:
        if create_engine is None:
            raise PersistenceConfigurationError(
                "SQLAlchemy is required for PostgreSQL persistence",
                {
                    "persistence_backend": "postgresql",
                    "backend": "postgresql",
                    "runtime_mode": "postgresql-unavailable",
                    "runtime": "postgresql-unavailable",
                    "database_configured": True,
                    "database_url_configured": True,
                    "database_url_kind": "postgresql",
                    "database_reachable": False,
                    "fallback_enabled": _env_flag("AMD_ALLOW_SQLITE_FALLBACK"),
                    "fallback_reason": "sqlalchemy_missing",
                },
            )
        self.database_url = _sync_postgres_url(database_url)
        self.descriptor = _database_descriptor(self.database_url)
        self._lock = RLock()
        self.path = Path(":postgresql:")
        self.engine: Engine = create_engine(self.database_url, future=True)
        self.verify_schema()

    def connect(self) -> PostgresConnection:
        return PostgresConnection(self.engine.connect())

    def ping(self) -> bool:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True

    def verify_schema(self) -> None:
        try:
            with self.engine.connect() as connection:
                tables = {
                    str(row[0])
                    for row in connection.execute(
                        text("select tablename from pg_tables where schemaname = 'public'")
                    ).fetchall()
                }
                version = (
                    connection.execute(text("select version_num from alembic_version")).scalar_one_or_none()
                    if "alembic_version" in tables
                    else None
                )
        except Exception as exc:
            raise PersistenceConfigurationError(
                "PostgreSQL persistence is configured but not reachable",
                self.failure_info("postgres_unreachable"),
            ) from exc
        missing = sorted(EXPECTED_TABLES - tables)
        if missing or version != EXPECTED_ALEMBIC_REVISION:
            raise PersistenceConfigurationError(
                "PostgreSQL persistence is configured but migrations are incomplete",
                self.failure_info("migration_required", missing_tables=missing, alembic_version=version),
            )

    def failure_info(self, reason: str, **extra: Any) -> dict[str, Any]:
        return {
            "persistence_backend": "postgresql",
            "backend": "postgresql",
            "runtime_mode": "postgresql-error",
            "runtime": "postgresql-error",
            "database_configured": True,
            "database_url_configured": True,
            "database_url_kind": "postgresql",
            "database_reachable": False,
            "fallback_enabled": _env_flag("AMD_ALLOW_SQLITE_FALLBACK"),
            "fallback_reason": reason,
            **self.descriptor,
            **extra,
        }


class SymbolRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def upsert_many(self, symbols: Iterable[str | dict[str, Any]]) -> int:
        rows = []
        now = _now_iso()
        for item in symbols:
            if isinstance(item, dict):
                symbol = normalize_symbol(str(item.get("symbol", "")))
                metadata = item
            else:
                symbol = normalize_symbol(str(item))
                metadata = {"symbol": symbol}
            if not symbol:
                continue
            rows.append((symbol, metadata.get("name"), metadata.get("exchange"), metadata.get("asset_type", "equity"), metadata.get("provider", "fmp"), _json_dumps(metadata), now, now))
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.executemany(
                    """
                    INSERT INTO symbols(symbol, name, exchange, asset_type, provider, metadata_json, created_at, updated_at)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        name=excluded.name,
                        exchange=excluded.exchange,
                        asset_type=excluded.asset_type,
                        provider=excluded.provider,
                        metadata_json=excluded.metadata_json,
                        updated_at=excluded.updated_at
                    """,
                    rows,
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return len(rows)

    def list_all(self) -> list[dict[str, Any]]:
        connection = self.store.connect()
        try:
            rows = connection.execute("SELECT * FROM symbols ORDER BY symbol").fetchall()
            return [dict(row) | {"metadata": _json_loads(row["metadata_json"])} for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class BarRepository:
    def __init__(self, store: SQLiteStore, symbols: SymbolRepository) -> None:
        self.store = store
        self.symbols = symbols

    def upsert_many(self, bars: Iterable[Bar | dict[str, Any]]) -> int:
        rows = []
        dirty_windows: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
        seen_symbols: set[str] = set()
        now = _now_iso()
        for bar in bars:
            payload = _payload(bar)
            symbol = normalize_symbol(str(payload["symbol"]))
            interval = str(payload["interval"])
            timestamp_utc = _parse_datetime(payload["timestamp_utc"]).isoformat()
            timestamp_et = _maybe_datetime(payload.get("timestamp_et"))
            timestamp_et_text = timestamp_et.isoformat() if timestamp_et else None
            session_date = _date_text(timestamp_et or timestamp_utc) or timestamp_utc[:10]
            source = str(payload.get("source") or "unknown")
            row_id = _stable_id("bar", symbol, interval, timestamp_utc, source)
            seen_symbols.add(symbol)
            for artifact_type, version in (
                ("features", "features.v2.no_leakage"),
                ("candidates", "candidate_signals.v1"),
                ("labels", "labels.v2.no_leakage"),
                ("replay", "candidate_market_replay"),
            ):
                key = (artifact_type, symbol, interval, session_date, version)
                current = dirty_windows.setdefault(key, {"start": timestamp_utc, "end": timestamp_utc})
                current["start"] = min(current["start"], timestamp_utc)
                current["end"] = max(current["end"], timestamp_utc)
            rows.append(
                (
                    row_id,
                    symbol,
                    interval,
                    timestamp_utc,
                    timestamp_et_text,
                    session_date,
                    float(payload["open"]),
                    float(payload["high"]),
                    float(payload["low"]),
                    float(payload["close"]),
                    int(payload["volume"]),
                    payload.get("vwap"),
                    source,
                    _json_dumps(payload.get("quality_flags") or []),
                    _json_dumps(payload | {"symbol": symbol, "timestamp_utc": timestamp_utc, "timestamp_et": timestamp_et_text}),
                    now,
                    now,
                )
            )
        if seen_symbols:
            self.symbols.upsert_many(sorted(seen_symbols))
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.executemany(
                    """
                    INSERT INTO bars(
                        id, symbol, interval, timestamp_utc, timestamp_et, session_date, open, high, low, close,
                        volume, vwap, source, quality_flags_json, payload_json, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, interval, timestamp_utc, source) DO UPDATE SET
                        open=excluded.open,
                        high=excluded.high,
                        low=excluded.low,
                        close=excluded.close,
                        volume=excluded.volume,
                        vwap=excluded.vwap,
                        quality_flags_json=excluded.quality_flags_json,
                        payload_json=excluded.payload_json,
                        updated_at=excluded.updated_at
                    """,
                    rows,
                )
                self._record_dirty_windows(connection, dirty_windows, now)
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return len(rows)

    def _record_dirty_windows(self, connection: Any, dirty_windows: dict[tuple[str, str, str, str, str], dict[str, str]], now: str) -> None:
        for (artifact_type, symbol, interval, session_date, version), window in dirty_windows.items():
            build_window_id = _stable_id("build_window", artifact_type, symbol, interval, session_date, version)
            connection.execute(
                """
                INSERT INTO pipeline_build_windows(
                    build_window_id, artifact_type, symbol, interval, session_date, start, "end",
                    version, dirty, stale_reason, payload_json, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_type, symbol, interval, session_date, version) DO UPDATE SET
                    start=excluded.start,
                    "end"=excluded."end",
                    dirty=excluded.dirty,
                    stale_reason=excluded.stale_reason,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (
                    build_window_id,
                    artifact_type,
                    symbol,
                    interval,
                    session_date,
                    window["start"],
                    window["end"],
                    version,
                    True,
                    "bars_upserted",
                    _json_dumps({"source": "bar_upsert"}),
                    now,
                    now,
                ),
            )

    def list_all(self) -> list[Bar]:
        return self.query()

    def query(
        self,
        symbols: Iterable[str] | None = None,
        intervals: Iterable[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Bar]:
        clauses: list[str] = []
        params: list[Any] = []
        normalized_symbols = [normalize_symbol(symbol) for symbol in symbols or []]
        if normalized_symbols:
            clauses.append(f"symbol IN ({','.join('?' for _ in normalized_symbols)})")
            params.extend(normalized_symbols)
        interval_values = [str(interval) for interval in intervals or []]
        if interval_values:
            clauses.append(f"interval IN ({','.join('?' for _ in interval_values)})")
            params.extend(interval_values)
        if start is not None:
            clauses.append("timestamp_utc >= ?")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("timestamp_utc <= ?")
            params.append(end.isoformat())
        sql = "SELECT payload_json FROM bars"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY symbol, interval, timestamp_utc"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        connection = self.store.connect()
        try:
            rows = connection.execute(sql, params).fetchall()
            return [_coerce_bar(_json_loads(row["payload_json"])) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class FeatureRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def upsert_many(self, features: Iterable[dict[str, Any]]) -> int:
        rows = []
        now = _now_iso()
        for feature in features:
            payload = _payload(feature)
            symbol = normalize_symbol(str(payload["symbol"]))
            interval = str(payload.get("interval") or "1min")
            timestamp = _parse_datetime(payload.get("timestamp_utc") or payload.get("timestamp")).isoformat()
            feature_set_version = str(payload.get("feature_set_version") or "features.v2.no_leakage")
            rows.append(
                (
                    _stable_id("feature", symbol, interval, timestamp, feature_set_version),
                    symbol,
                    interval,
                    timestamp,
                    _date_text(payload.get("session_date") or timestamp),
                    feature_set_version,
                    payload.get("market_regime"),
                    payload.get("ticker_regime"),
                    _json_dumps(payload.get("data_quality_flags") or []),
                    _json_dumps(payload | {"symbol": symbol, "timestamp_utc": timestamp, "interval": interval}),
                    now,
                    now,
                )
            )
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.executemany(
                    """
                    INSERT INTO features(
                        id, symbol, interval, timestamp_utc, session_date, feature_set_version, market_regime,
                        ticker_regime, data_quality_flags_json, payload_json, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, interval, timestamp_utc, feature_set_version) DO UPDATE SET
                        market_regime=excluded.market_regime,
                        ticker_regime=excluded.ticker_regime,
                        data_quality_flags_json=excluded.data_quality_flags_json,
                        payload_json=excluded.payload_json,
                        updated_at=excluded.updated_at
                    """,
                    rows,
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return len(rows)

    def list_all(self) -> list[dict[str, Any]]:
        return self.query()

    def query(
        self,
        symbols: Iterable[str] | None = None,
        intervals: Iterable[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> builtins.list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        normalized_symbols = [normalize_symbol(symbol) for symbol in symbols or []]
        if normalized_symbols:
            clauses.append(f"symbol IN ({','.join('?' for _ in normalized_symbols)})")
            params.extend(normalized_symbols)
        interval_values = [str(interval) for interval in intervals or []]
        if interval_values:
            clauses.append(f"interval IN ({','.join('?' for _ in interval_values)})")
            params.extend(interval_values)
        if start is not None:
            clauses.append("timestamp_utc >= ?")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("timestamp_utc <= ?")
            params.append(end.isoformat())
        sql = "SELECT payload_json FROM features"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY symbol, interval, timestamp_utc"
        connection = self.store.connect()
        try:
            rows = connection.execute(sql, params).fetchall()
            return [_json_loads(row["payload_json"]) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class CandidateSignalRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def upsert_many(self, candidates: Iterable[Any]) -> int:
        rows = []
        now = _now_iso()
        for candidate in candidates:
            payload = _payload(candidate)
            symbol = normalize_symbol(str(payload["symbol"]))
            interval = str(payload.get("interval") or "1min")
            timestamp = _parse_datetime(payload["timestamp_utc"]).isoformat()
            side = str(payload["side"])
            setup_type = str(payload["setup_type"])
            candidate_id = str(payload.get("candidate_id") or _stable_id("candidate", symbol, interval, timestamp, side, setup_type))
            rows.append(
                (
                    candidate_id,
                    symbol,
                    interval,
                    timestamp,
                    side,
                    setup_type,
                    _json_dumps(payload.get("reason_codes") or []),
                    _json_dumps(payload.get("warning_codes") or []),
                    _json_dumps(payload | {"candidate_id": candidate_id, "symbol": symbol, "timestamp_utc": timestamp}),
                    now,
                    now,
                )
            )
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.executemany(
                    """
                    INSERT INTO candidate_signals(
                        candidate_id, symbol, interval, timestamp_utc, side, setup_type, reason_codes_json,
                        warning_codes_json, payload_json, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, interval, timestamp_utc, side, setup_type) DO UPDATE SET
                        reason_codes_json=excluded.reason_codes_json,
                        warning_codes_json=excluded.warning_codes_json,
                        payload_json=excluded.payload_json,
                        updated_at=excluded.updated_at
                    """,
                    rows,
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return len(rows)

    def list_all(self) -> list[dict[str, Any]]:
        return self.query()

    def query(
        self,
        symbols: Iterable[str] | None = None,
        intervals: Iterable[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        sides: Iterable[str] | None = None,
        setup_types: Iterable[str] | None = None,
    ) -> builtins.list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        normalized_symbols = [normalize_symbol(symbol) for symbol in symbols or []]
        if normalized_symbols:
            clauses.append(f"symbol IN ({','.join('?' for _ in normalized_symbols)})")
            params.extend(normalized_symbols)
        interval_values = [str(interval) for interval in intervals or []]
        if interval_values:
            clauses.append(f"interval IN ({','.join('?' for _ in interval_values)})")
            params.extend(interval_values)
        side_values = [str(side) for side in sides or []]
        if side_values:
            clauses.append(f"side IN ({','.join('?' for _ in side_values)})")
            params.extend(side_values)
        setup_values = [str(setup) for setup in setup_types or []]
        if setup_values:
            clauses.append(f"setup_type IN ({','.join('?' for _ in setup_values)})")
            params.extend(setup_values)
        if start is not None:
            clauses.append("timestamp_utc >= ?")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("timestamp_utc <= ?")
            params.append(end.isoformat())
        sql = "SELECT payload_json FROM candidate_signals"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY timestamp_utc, symbol, setup_type"
        connection = self.store.connect()
        try:
            rows = connection.execute(sql, params).fetchall()
            return [_json_loads(row["payload_json"]) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class LabelRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def upsert_many(self, labels: Iterable[Any]) -> int:
        rows = []
        now = _now_iso()
        for label in labels:
            payload = _payload(label)
            symbol = normalize_symbol(str(payload["symbol"]))
            interval = str(payload.get("interval") or "1min")
            timestamp = _parse_datetime(payload.get("timestamp") or payload.get("timestamp_utc")).isoformat()
            side = str(payload["side"])
            setup_type = str(payload.get("setup_type") or "unknown")
            label_config_version = str(payload.get("label_config_version") or "labels.v2.no_leakage")
            label_id = str(payload.get("label_id") or _stable_id("label", symbol, interval, timestamp, side, setup_type, label_config_version))
            schema_payload = payload | {
                "label_id": label_id,
                "symbol": symbol,
                "interval": interval,
                "timestamp": timestamp,
                "timestamp_utc": timestamp,
                "side": side,
                "label_config_version": label_config_version,
            }
            rows.append(
                (
                    label_id,
                    symbol,
                    interval,
                    timestamp,
                    side,
                    setup_type,
                    label_config_version,
                    float(payload["entry_price"]),
                    float(payload["stop_price"]),
                    float(payload["target_1"]),
                    float(payload["target_2"]),
                    float(payload["target_3"]),
                    float(payload.get("realized_r", 0.0)),
                    str(payload.get("outcome", "NEUTRAL")),
                    payload.get("market_regime"),
                    _maybe_datetime(payload.get("exit_timestamp_utc")).isoformat() if payload.get("exit_timestamp_utc") else None,
                    _json_dumps(schema_payload),
                    now,
                    now,
                )
            )
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.executemany(
                    """
                    INSERT INTO labels(
                        label_id, symbol, interval, timestamp_utc, side, setup_type, label_config_version,
                        entry_price, stop_price, target_1, target_2, target_3, realized_r, outcome,
                        market_regime, exit_timestamp_utc, payload_json, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(symbol, interval, timestamp_utc, side, setup_type, label_config_version) DO UPDATE SET
                        entry_price=excluded.entry_price,
                        stop_price=excluded.stop_price,
                        target_1=excluded.target_1,
                        target_2=excluded.target_2,
                        target_3=excluded.target_3,
                        realized_r=excluded.realized_r,
                        outcome=excluded.outcome,
                        market_regime=excluded.market_regime,
                        exit_timestamp_utc=excluded.exit_timestamp_utc,
                        payload_json=excluded.payload_json,
                        updated_at=excluded.updated_at
                    """,
                    rows,
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return len(rows)

    def list_all(self) -> list[Label]:
        return self.query()

    def query(
        self,
        symbols: Iterable[str] | None = None,
        intervals: Iterable[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Label]:
        clauses: list[str] = []
        params: list[Any] = []
        normalized_symbols = [normalize_symbol(symbol) for symbol in symbols or []]
        if normalized_symbols:
            clauses.append(f"symbol IN ({','.join('?' for _ in normalized_symbols)})")
            params.extend(normalized_symbols)
        interval_values = [str(interval) for interval in intervals or []]
        if interval_values:
            clauses.append(f"interval IN ({','.join('?' for _ in interval_values)})")
            params.extend(interval_values)
        if start is not None:
            clauses.append("timestamp_utc >= ?")
            params.append(start.isoformat())
        if end is not None:
            clauses.append("timestamp_utc <= ?")
            params.append(end.isoformat())
        sql = "SELECT payload_json FROM labels"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY symbol, timestamp_utc"
        connection = self.store.connect()
        try:
            rows = connection.execute(sql, params).fetchall()
            return [_coerce_label(_json_loads(row["payload_json"])) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class ValidationReportRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save(self, report: Any, model_version: str | None = None, purpose: str = "validation") -> dict[str, Any]:
        payload = _payload(report)
        created_at = str(payload.get("created_at") or _now_iso())
        report_id = str(payload.get("report_id") or _stable_id("report", purpose, model_version or "", created_at))
        summary = payload.get("summary") or payload.get("metrics") or {}
        windows = payload.get("windows") or []
        activation_decision = str(payload.get("activation_decision") or "rejected")
        rejection_reasons = payload.get("rejection_reasons") or []
        row_payload = payload | {"report_id": report_id, "model_version": model_version, "purpose": purpose, "created_at": created_at}
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO validation_reports(
                        report_id, model_version, purpose, activation_decision, rejection_reasons_json,
                        summary_json, per_symbol_json, per_setup_json, per_regime_json, leakage_warnings_json,
                        payload_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(report_id) DO UPDATE SET
                        activation_decision=excluded.activation_decision,
                        rejection_reasons_json=excluded.rejection_reasons_json,
                        summary_json=excluded.summary_json,
                        payload_json=excluded.payload_json
                    """,
                    (
                        report_id,
                        model_version,
                        purpose,
                        activation_decision,
                        _json_dumps(rejection_reasons),
                        _json_dumps(summary),
                        _json_dumps(payload.get("per_symbol") or {}),
                        _json_dumps(payload.get("per_setup") or {}),
                        _json_dumps(payload.get("per_regime") or {}),
                        _json_dumps(payload.get("leakage_warnings") or []),
                        _json_dumps(row_payload),
                        created_at,
                    ),
                )
                connection.execute("DELETE FROM validation_windows WHERE report_id = ?", (report_id,))
                for index, window in enumerate(windows, start=1):
                    window_payload = _payload(window)
                    split = window_payload.get("split") or {}
                    window_id = str(window_payload.get("window_id") or _stable_id("window", report_id, index))
                    connection.execute(
                        """
                        INSERT INTO validation_windows(
                            window_id, report_id, window_name, train_start, train_end, validation_start,
                            validation_end, test_start, test_end, accepted, metrics_json, rejection_reasons_json,
                            payload_json
                        )
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            window_id,
                            report_id,
                            str(window_payload.get("window_id") or f"window-{index}"),
                            split.get("train_start"),
                            split.get("train_end"),
                            split.get("validation_start"),
                            split.get("validation_end"),
                            split.get("test_start"),
                            split.get("test_end"),
                            bool(window_payload.get("accepted")),
                            _json_dumps(window_payload.get("metrics") or {}),
                            _json_dumps(window_payload.get("rejection_reasons") or []),
                            _json_dumps(window_payload | {"window_id": window_id, "report_id": report_id}),
                        ),
                    )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return row_payload

    def latest(self, model_version: str | None = None, purpose: str | None = None) -> dict[str, Any] | None:
        clauses: list[str] = []
        params: list[Any] = []
        if model_version is not None:
            clauses.append("model_version = ?")
            params.append(model_version)
        if purpose is not None:
            clauses.append("purpose = ?")
            params.append(purpose)
        sql = "SELECT payload_json FROM validation_reports"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC LIMIT 1"
        connection = self.store.connect()
        try:
            row = connection.execute(sql, params).fetchone()
            return _json_loads(row["payload_json"]) if row else None
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def list_all(self, purpose: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT payload_json FROM validation_reports"
        params: list[Any] = []
        if purpose is not None:
            sql += " WHERE purpose = ?"
            params.append(purpose)
        sql += " ORDER BY created_at DESC"
        connection = self.store.connect()
        try:
            return [_json_loads(row["payload_json"]) for row in connection.execute(sql, params).fetchall()]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class ModelRunRepository:
    def __init__(self, store: SQLiteStore, settings: Settings | None = None) -> None:
        self.store = store
        self.settings = settings or get_settings()

    def save(self, model: dict[str, Any], artifact_path: str | None = None) -> dict[str, Any]:
        payload = _payload(model)
        model_version = str(payload["model_version"])
        now = _now_iso()
        created_at = str(payload.get("created_at") or now)
        artifact_path = artifact_path or str(self.settings.model_artifacts_dir / f"{model_version}.json")
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO model_runs(
                        model_version, model_type, feature_set_version, label_config_version, training_start,
                        training_end, activation_decision, active, metrics_json, validation_metrics_json,
                        payload_json, artifact_path, code_version, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(model_version) DO UPDATE SET
                        activation_decision=excluded.activation_decision,
                        active=excluded.active,
                        metrics_json=excluded.metrics_json,
                        validation_metrics_json=excluded.validation_metrics_json,
                        payload_json=excluded.payload_json,
                        artifact_path=excluded.artifact_path,
                        updated_at=excluded.updated_at
                    """,
                    (
                        model_version,
                        str(payload.get("model_type") or "unknown"),
                        payload.get("feature_set_version"),
                        payload.get("label_config_version"),
                        payload.get("training_start"),
                        payload.get("training_end"),
                        str(payload.get("activation_decision") or "rejected"),
                        bool(payload.get("active")),
                        _json_dumps(payload.get("metrics") or {}),
                        _json_dumps(payload.get("validation_metrics") or {}),
                        _json_dumps(payload),
                        artifact_path,
                        payload.get("code_version"),
                        created_at,
                        now,
                    ),
                )
                artifact_id = _stable_id("artifact", model_version, "model_json", artifact_path)
                connection.execute(
                    """
                    INSERT INTO model_artifacts(artifact_id, model_version, artifact_type, path, payload_json, created_at)
                    VALUES(?, ?, ?, ?, ?, ?)
                    ON CONFLICT(artifact_id) DO UPDATE SET
                        payload_json=excluded.payload_json
                    """,
                    (
                        artifact_id,
                        model_version,
                        "model_json",
                        artifact_path,
                        _json_dumps({"schema_version": payload.get("schema_version")}),
                        now,
                    ),
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return payload

    def record_artifact(self, model_version: str, artifact_type: str, path: str, metadata: dict[str, Any] | None = None) -> None:
        artifact_id = _stable_id("artifact", model_version, artifact_type, path)
        payload = metadata or {}
        connection = self.store.connect()
        try:
            connection.execute(
                """
                INSERT INTO model_artifacts(artifact_id, model_version, artifact_type, path, payload_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                    payload_json=excluded.payload_json
                """,
                (artifact_id, model_version, artifact_type, path, _json_dumps(payload), _now_iso()),
            )
            connection.commit()
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def get(self, model_version: str) -> dict[str, Any] | None:
        connection = self.store.connect()
        try:
            row = connection.execute("SELECT payload_json FROM model_runs WHERE model_version = ?", (model_version,)).fetchone()
            return _json_loads(row["payload_json"]) if row else None
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def list_all(self) -> list[dict[str, Any]]:
        connection = self.store.connect()
        try:
            rows = connection.execute("SELECT payload_json FROM model_runs ORDER BY created_at DESC").fetchall()
            return [_json_loads(row["payload_json"]) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def set_active(self, model_version: str, active: bool) -> None:
        model = self.get(model_version)
        if model:
            model["active"] = active
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    "UPDATE model_runs SET active = ?, payload_json = ?, updated_at = ? WHERE model_version = ?",
                    (bool(active), _json_dumps(model) if model else None, _now_iso(), model_version),
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()


class ModelEvidenceCellRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save_many(self, model_version: str, cells: Iterable[dict[str, Any]]) -> int:
        rows = []
        for cell in cells:
            payload = _payload(cell)
            cell_key = str(payload["cell_key"])
            created_at = str(payload.get("created_at") or _now_iso())
            metrics = dict(payload.get("metrics") or {})
            rows.append(
                (
                    str(payload.get("id") or _stable_id("evidence_cell", model_version, cell_key)),
                    model_version,
                    cell_key,
                    _json_dumps(payload.get("dimensions") or {}),
                    str(payload.get("hierarchy_level") or "unknown"),
                    payload.get("parent_cell_key"),
                    _json_dumps(metrics),
                    int(payload.get("sample_size") or metrics.get("sample_size") or 0),
                    int(payload.get("observed_outcome_count") or metrics.get("observed_outcome_count") or 0),
                    float(payload.get("average_r") or metrics.get("average_r") or 0.0),
                    float(payload.get("median_r") or metrics.get("median_r") or 0.0),
                    float(payload.get("profit_factor") or metrics.get("profit_factor") or 0.0),
                    float(payload.get("max_drawdown_r") or metrics.get("max_drawdown_r") or 0.0),
                    payload.get("robustness_score") if payload.get("robustness_score") is not None else metrics.get("sensitivity_robustness_score"),
                    _json_dumps(payload.get("fragility_flags") or metrics.get("fragility_flags") or []),
                    str(payload.get("evidence_quality_grade") or metrics.get("evidence_quality_grade") or "UNKNOWN"),
                    created_at,
                )
            )
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute("DELETE FROM model_evidence_cells WHERE model_version = ?", (model_version,))
                connection.executemany(
                    """
                    INSERT INTO model_evidence_cells(
                        id, model_version, cell_key, dimensions_json, hierarchy_level, parent_cell_key,
                        metrics_json, sample_size, observed_outcome_count, average_r, median_r, profit_factor,
                        max_drawdown_r, robustness_score, fragility_flags_json, evidence_quality_grade, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(model_version, cell_key) DO UPDATE SET
                        dimensions_json=excluded.dimensions_json,
                        hierarchy_level=excluded.hierarchy_level,
                        parent_cell_key=excluded.parent_cell_key,
                        metrics_json=excluded.metrics_json,
                        sample_size=excluded.sample_size,
                        observed_outcome_count=excluded.observed_outcome_count,
                        average_r=excluded.average_r,
                        median_r=excluded.median_r,
                        profit_factor=excluded.profit_factor,
                        max_drawdown_r=excluded.max_drawdown_r,
                        robustness_score=excluded.robustness_score,
                        fragility_flags_json=excluded.fragility_flags_json,
                        evidence_quality_grade=excluded.evidence_quality_grade
                    """,
                    rows,
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return len(rows)

    def list(self, model_version: str, limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        connection = self.store.connect()
        try:
            rows = connection.execute(
                """
                SELECT * FROM model_evidence_cells
                WHERE model_version = ?
                ORDER BY hierarchy_level, observed_outcome_count DESC, average_r DESC, cell_key
                LIMIT ? OFFSET ?
                """,
                (model_version, limit, offset),
            ).fetchall()
            return [self._row(row) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def count(self, model_version: str) -> int:
        connection = self.store.connect()
        try:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM model_evidence_cells WHERE model_version = ?",
                (model_version,),
            ).fetchone()
            return int(row["count"] if row else 0)
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def summary(self, model_version: str) -> dict[str, Any]:
        cells = self.list(model_version, limit=100_000)
        return {
            "model_version": model_version,
            "cell_count": len(cells),
            "observed_outcome_count": sum(int(cell.get("observed_outcome_count") or 0) for cell in cells),
            "grades": dict(Counter(str(cell.get("evidence_quality_grade") or "UNKNOWN") for cell in cells)),
            "hierarchy_levels": dict(Counter(str(cell.get("hierarchy_level") or "unknown") for cell in cells)),
        }

    def _row(self, row: Any) -> dict[str, Any]:
        data = dict(row)
        data["dimensions"] = _json_loads(data.pop("dimensions_json"))
        data["metrics"] = _json_loads(data.pop("metrics_json"))
        data["fragility_flags"] = _json_loads(data.pop("fragility_flags_json"))
        return data


class CandidateScoreAuditRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save(self, audit: dict[str, Any]) -> dict[str, Any]:
        payload = _payload(audit)
        created_at = str(payload.get("created_at") or _now_iso())
        score_id = str(payload.get("score_id") or _stable_id("score", payload.get("model_version"), created_at))
        row_id = str(payload.get("id") or _stable_id("score_audit", score_id))
        row_payload = payload | {"id": row_id, "score_id": score_id, "created_at": created_at}
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO candidate_score_audits(
                        id, score_id, model_version, candidate_id, symbol, interval, timestamp_utc, side,
                        setup_type, signal_quality_score, grade, action, expected_r_estimate,
                        score_components_json, suppression_reasons_json, evidence_cell_keys_used_json,
                        warnings_json, payload_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(score_id) DO UPDATE SET
                        signal_quality_score=excluded.signal_quality_score,
                        grade=excluded.grade,
                        action=excluded.action,
                        expected_r_estimate=excluded.expected_r_estimate,
                        score_components_json=excluded.score_components_json,
                        suppression_reasons_json=excluded.suppression_reasons_json,
                        evidence_cell_keys_used_json=excluded.evidence_cell_keys_used_json,
                        warnings_json=excluded.warnings_json,
                        payload_json=excluded.payload_json
                    """,
                    (
                        row_id,
                        score_id,
                        str(row_payload["model_version"]),
                        row_payload.get("candidate_id"),
                        normalize_symbol(str(row_payload["symbol"])),
                        str(row_payload.get("interval") or "1min"),
                        _maybe_datetime(row_payload.get("timestamp_utc")).isoformat() if row_payload.get("timestamp_utc") else _now_iso(),
                        str(row_payload.get("side") or "NO_TRADE"),
                        str(row_payload.get("setup_type") or "unknown"),
                        float(row_payload.get("signal_quality_score") or 0.0),
                        str(row_payload.get("grade") or "NO_TRADE"),
                        str(row_payload.get("action") or "SUPPRESS"),
                        float(row_payload.get("expected_r_estimate") or 0.0),
                        _json_dumps(row_payload.get("score_components") or {}),
                        _json_dumps(row_payload.get("suppression_reasons") or []),
                        _json_dumps(row_payload.get("evidence_cell_keys_used") or []),
                        _json_dumps(row_payload.get("warnings") or row_payload.get("warning_codes") or []),
                        _json_dumps(row_payload),
                        created_at,
                    ),
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return row_payload

    def list(
        self,
        model_version: str,
        limit: int = 500,
        offset: int = 0,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["model_version = ?"]
        params: list[Any] = [model_version]
        if symbol:
            clauses.append("symbol = ?")
            params.append(normalize_symbol(symbol))
        sql = "SELECT * FROM candidate_score_audits WHERE " + " AND ".join(clauses)  # noqa: S608 - fixed clauses with bound parameters.
        sql += " ORDER BY created_at DESC, score_id LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        connection = self.store.connect()
        try:
            rows = connection.execute(sql, params).fetchall()
            return [self._row(row) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def _row(self, row: Any) -> dict[str, Any]:
        data = dict(row)
        data["score_components"] = _json_loads(data.pop("score_components_json"))
        data["suppression_reasons"] = _json_loads(data.pop("suppression_reasons_json"))
        data["evidence_cell_keys_used"] = _json_loads(data.pop("evidence_cell_keys_used_json"))
        data["warnings"] = _json_loads(data.pop("warnings_json"))
        data["payload"] = _json_loads(data.pop("payload_json"))
        return data


class CalibrationAuditRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save(self, audit: dict[str, Any]) -> dict[str, Any]:
        payload = _payload(audit)
        created_at = str(payload.get("created_at") or _now_iso())
        audit_id = str(payload.get("calibration_audit_id") or _stable_id("calibration", payload.get("model_version"), created_at))
        row_id = str(payload.get("id") or _stable_id("calibration_audit", audit_id))
        score_bins = list(payload.get("score_bins") or [])
        grade_bins = list(payload.get("grade_bins") or [])
        action_bins = list(payload.get("action_bins") or [])
        bins = [
            *(dict(item) | {"bin_type": "score"} for item in score_bins),
            *(dict(item) | {"bin_type": "grade"} for item in grade_bins),
            *(dict(item) | {"bin_type": "action"} for item in action_bins),
        ]
        row_payload = payload | {"id": row_id, "calibration_audit_id": audit_id, "created_at": created_at}
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO model_calibration_audits(
                        id, calibration_audit_id, model_version, validation_report_id, replay_run_ids_json,
                        outcome_source, score_bins_json, grade_bins_json, action_bins_json,
                        rank_correlation_score, monotonicity_pass, separation_metrics_json,
                        stability_metrics_json, warnings_json, rejection_reasons_json, payload_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(calibration_audit_id) DO UPDATE SET
                        score_bins_json=excluded.score_bins_json,
                        grade_bins_json=excluded.grade_bins_json,
                        action_bins_json=excluded.action_bins_json,
                        rank_correlation_score=excluded.rank_correlation_score,
                        monotonicity_pass=excluded.monotonicity_pass,
                        separation_metrics_json=excluded.separation_metrics_json,
                        stability_metrics_json=excluded.stability_metrics_json,
                        warnings_json=excluded.warnings_json,
                        rejection_reasons_json=excluded.rejection_reasons_json,
                        payload_json=excluded.payload_json
                    """,
                    (
                        row_id,
                        audit_id,
                        str(row_payload["model_version"]),
                        row_payload.get("validation_report_id"),
                        _json_dumps(row_payload.get("replay_run_ids") or []),
                        str(row_payload.get("outcome_source") or "counterfactual_preferred"),
                        _json_dumps(score_bins),
                        _json_dumps(grade_bins),
                        _json_dumps(action_bins),
                        float(row_payload.get("rank_correlation_score") or 0.0),
                        bool(row_payload.get("monotonicity_pass")),
                        _json_dumps(row_payload.get("separation_metrics") or {}),
                        _json_dumps(row_payload.get("stability_metrics") or {}),
                        _json_dumps(row_payload.get("calibration_warnings") or row_payload.get("warnings") or []),
                        _json_dumps(row_payload.get("rejection_reasons") or []),
                        _json_dumps(row_payload),
                        created_at,
                    ),
                )
                connection.execute("DELETE FROM model_calibration_bins WHERE calibration_audit_id = ?", (audit_id,))
                connection.executemany(
                    """
                    INSERT INTO model_calibration_bins(
                        id, calibration_audit_id, bin_type, bin_key, sample_size, observed_average_r,
                        observed_win_rate, profit_factor, max_drawdown_r, metrics_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            _stable_id("calibration_bin", audit_id, bin_item.get("bin_type"), bin_item.get("bin_key") or bin_item.get("label")),
                            audit_id,
                            str(bin_item.get("bin_type") or "score"),
                            str(bin_item.get("bin_key") or bin_item.get("label") or "unknown"),
                            int(bin_item.get("sample_size") or 0),
                            float(bin_item.get("observed_average_r") or bin_item.get("average_r") or 0.0),
                            float(bin_item.get("observed_win_rate") or bin_item.get("win_rate") or 0.0),
                            float(bin_item.get("profit_factor") or 0.0),
                            float(bin_item.get("max_drawdown_r") or 0.0),
                            _json_dumps(bin_item),
                            created_at,
                        )
                        for bin_item in bins
                    ],
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return row_payload | {"bins_written": len(bins)}

    def get(self, calibration_audit_id: str) -> dict[str, Any] | None:
        connection = self.store.connect()
        try:
            row = connection.execute(
                "SELECT payload_json FROM model_calibration_audits WHERE calibration_audit_id = ?",
                (calibration_audit_id,),
            ).fetchone()
            return _json_loads(row["payload_json"]) if row else None
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def latest(self, model_version: str) -> dict[str, Any] | None:
        items = self.list(model_version, limit=1)
        return items[0] if items else None

    def list(self, model_version: str, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        connection = self.store.connect()
        try:
            rows = connection.execute(
                """
                SELECT payload_json FROM model_calibration_audits
                WHERE model_version = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (model_version, limit, offset),
            ).fetchall()
            return [_json_loads(row["payload_json"]) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def list_bins(
        self,
        calibration_audit_id: str,
        limit: int = 500,
        offset: int = 0,
        bin_type: str | None = None,
    ) -> builtins.list[dict[str, Any]]:
        clauses = ["calibration_audit_id = ?"]
        params: list[Any] = [calibration_audit_id]
        if bin_type:
            clauses.append("bin_type = ?")
            params.append(bin_type)
        sql = "SELECT * FROM model_calibration_bins WHERE " + " AND ".join(clauses)  # noqa: S608 - fixed clauses.
        sql += " ORDER BY bin_type, bin_key LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        connection = self.store.connect()
        try:
            output = []
            for row in connection.execute(sql, params).fetchall():
                data = dict(row)
                data["metrics"] = _json_loads(data.pop("metrics_json"))
                output.append(data)
            return output
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class ModelComparisonRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save(self, comparison: dict[str, Any]) -> dict[str, Any]:
        payload = _payload(comparison)
        created_at = str(payload.get("created_at") or _now_iso())
        comparison_id = str(payload.get("comparison_id") or _stable_id("model_comparison", payload.get("comparison_type") or "model_comparison", created_at))
        row_payload = payload | {"comparison_id": comparison_id, "created_at": created_at}
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO model_comparisons(
                        comparison_id, comparison_type, model_versions_json, validation_report_ids_json,
                        calibration_audit_ids_json, replay_run_ids_json, summary_json, payload_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(comparison_id) DO UPDATE SET
                        summary_json=excluded.summary_json,
                        payload_json=excluded.payload_json
                    """,
                    (
                        comparison_id,
                        str(row_payload.get("comparison_type") or "model_comparison"),
                        _json_dumps(row_payload.get("model_versions") or []),
                        _json_dumps(row_payload.get("validation_report_ids") or []),
                        _json_dumps(row_payload.get("calibration_audit_ids") or []),
                        _json_dumps(row_payload.get("replay_run_ids") or []),
                        _json_dumps(row_payload.get("summary") or {}),
                        _json_dumps(row_payload),
                        created_at,
                    ),
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return row_payload

    def get(self, comparison_id: str) -> dict[str, Any] | None:
        connection = self.store.connect()
        try:
            row = connection.execute(
                "SELECT payload_json FROM model_comparisons WHERE comparison_id = ?",
                (comparison_id,),
            ).fetchone()
            return _json_loads(row["payload_json"]) if row else None
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def list_all(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        connection = self.store.connect()
        try:
            rows = connection.execute(
                "SELECT payload_json FROM model_comparisons ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return [_json_loads(row["payload_json"]) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class ActiveModelRepository:
    def __init__(self, store: SQLiteStore, model_runs: ModelRunRepository) -> None:
        self.store = store
        self.model_runs = model_runs

    def activate(
        self,
        model: dict[str, Any],
        validation_report_id: str | None = None,
        strategy_scope: str = "default",
    ) -> dict[str, Any]:
        payload = _payload(model) | {"active": True}
        model_version = str(payload["model_version"])
        model_type = str(payload.get("model_type") or "unknown")
        active_model_id = _stable_id("active", model_type, strategy_scope)
        activated_at = _now_iso()
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO active_models(
                        active_model_id, model_version, model_type, strategy_scope, activated_at,
                        validation_report_id, payload_json
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(model_type, strategy_scope) DO UPDATE SET
                        model_version=excluded.model_version,
                        activated_at=excluded.activated_at,
                        validation_report_id=excluded.validation_report_id,
                        payload_json=excluded.payload_json
                    """,
                    (active_model_id, model_version, model_type, strategy_scope, activated_at, validation_report_id, _json_dumps(payload)),
                )
                rows = connection.execute("SELECT model_version, payload_json FROM model_runs").fetchall()
                for row in rows:
                    row_version = str(row["model_version"])
                    row_active = row_version == model_version
                    row_payload = payload if row_active else _json_loads(row["payload_json"])
                    if isinstance(row_payload, dict):
                        row_payload = row_payload | {"active": row_active}
                    connection.execute(
                        "UPDATE model_runs SET active = ?, payload_json = ?, updated_at = ? WHERE model_version = ?",
                        (row_active, _json_dumps(row_payload), _now_iso(), row_version),
                    )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return payload | {"activated_at": activated_at, "validation_report_id": validation_report_id}

    def get_active(self, model_type: str = "statistical_evidence_baseline", strategy_scope: str = "default") -> dict[str, Any] | None:
        connection = self.store.connect()
        try:
            row = connection.execute(
                "SELECT payload_json FROM active_models WHERE model_type = ? AND strategy_scope = ?",
                (model_type, strategy_scope),
            ).fetchone()
            return _json_loads(row["payload_json"]) if row else None
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class LiveSignalRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def upsert_many(self, signals: Iterable[Signal | dict[str, Any]], scanner_run_id: str | None = None) -> int:
        rows = []
        now = _now_iso()
        for signal in signals:
            payload = _payload(signal)
            timestamp = _parse_datetime(payload["timestamp"]).isoformat()
            ticker = normalize_symbol(str(payload.get("ticker") or payload.get("symbol")))
            side = str(payload["side"])
            setup_type = str(payload["setup_type"])
            model_version = str(payload.get("model_version") or "untrained-baseline")
            signal_id = str(payload.get("signal_id") or _stable_id("signal", timestamp, ticker, side, setup_type, model_version))
            rows.append(
                (
                    signal_id,
                    scanner_run_id,
                    timestamp,
                    ticker,
                    side,
                    setup_type,
                    float(payload.get("confidence_score") or 0.0),
                    float(payload.get("expected_r") or 0.0),
                    model_version,
                    str(payload.get("status") or "OPEN"),
                    _json_dumps(payload | {"signal_id": signal_id, "timestamp": timestamp, "ticker": ticker}),
                    now,
                    now,
                )
            )
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.executemany(
                    """
                    INSERT INTO live_signals(
                        signal_id, scanner_run_id, timestamp_utc, ticker, side, setup_type,
                        confidence_score, expected_r, model_version, status, payload_json, created_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(signal_id) DO UPDATE SET
                        scanner_run_id=excluded.scanner_run_id,
                        confidence_score=excluded.confidence_score,
                        expected_r=excluded.expected_r,
                        status=excluded.status,
                        payload_json=excluded.payload_json,
                        updated_at=excluded.updated_at
                    """,
                    rows,
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return len(rows)

    def list_latest(self, limit: int = 250) -> list[Signal]:
        connection = self.store.connect()
        try:
            rows = connection.execute(
                "SELECT payload_json FROM live_signals ORDER BY timestamp_utc DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [_coerce_signal(_json_loads(row["payload_json"])) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def history(self, limit: int = 1000) -> list[Signal]:
        return self.list_latest(limit=limit)


class ScannerRunRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def start(self, symbols: list[str], confidence_threshold: float | None, model_version: str | None) -> str:
        started_at = _now_iso()
        run_id = _stable_id("scanner_run", started_at, ",".join(symbols), model_version or "")
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO scanner_runs(
                        scanner_run_id, started_at, status, symbols_json, confidence_threshold,
                        model_version, stats_json, created_at, updated_at
                    )
                    VALUES(?, ?, 'running', ?, ?, ?, '{}', ?, ?)
                    """,
                    (run_id, started_at, _json_dumps(symbols), confidence_threshold, model_version, started_at, started_at),
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return run_id

    def finish(self, scanner_run_id: str, status: str = "stopped", latest_error: str | None = None, stats: dict[str, Any] | None = None) -> None:
        now = _now_iso()
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    UPDATE scanner_runs
                    SET stopped_at = ?, status = ?, latest_error = ?, stats_json = ?, updated_at = ?
                    WHERE scanner_run_id = ?
                    """,
                    (now, status, latest_error, _json_dumps(stats or {}), now, scanner_run_id),
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()

    def latest(self) -> dict[str, Any] | None:
        connection = self.store.connect()
        try:
            row = connection.execute("SELECT * FROM scanner_runs ORDER BY started_at DESC LIMIT 1").fetchone()
            if row is None:
                return None
            data = dict(row)
            data["symbols"] = _json_loads(data.pop("symbols_json"))
            data["stats"] = _json_loads(data.pop("stats_json"))
            return data
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class ProviderRequestRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def record(
        self,
        provider: str,
        endpoint: str,
        status: str,
        symbol: str | None = None,
        interval: str | None = None,
        row_count: int | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        now = _now_iso()
        request_id = _stable_id("provider_request", provider, endpoint, symbol or "", interval or "", now)
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO provider_requests(
                        request_id, provider, endpoint, symbol, interval, started_at, finished_at, status,
                        row_count, error_message, metadata_json
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        request_id,
                        provider,
                        endpoint,
                        normalize_symbol(symbol) if symbol else None,
                        interval,
                        now,
                        now,
                        status,
                        row_count,
                        error_message,
                        _json_dumps(metadata or {}),
                    ),
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return request_id

    def list_all(self) -> list[dict[str, Any]]:
        connection = self.store.connect()
        try:
            rows = connection.execute("SELECT * FROM provider_requests ORDER BY started_at DESC").fetchall()
            output = []
            for row in rows:
                data = dict(row)
                data["metadata"] = _json_loads(data.pop("metadata_json"))
                output.append(data)
            return output
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class ReplayRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save(self, replay_run: Any, trades: Iterable[Any]) -> dict[str, Any]:
        payload = _payload(replay_run)
        replay_run_id = str(payload["replay_run_id"])
        metrics = payload.get("summary_metrics") or payload.get("metrics") or {}
        config = payload.get("config") or {}
        created_at = str(payload.get("created_at") or _now_iso())
        backend = "postgresql" if str(self.store.path) == ":postgresql:" else "sqlite"
        run_payload = payload | {
            "replay_run_id": replay_run_id,
            "simulation_type": str(payload.get("simulation_type") or "candidate_market_replay"),
            "backend": backend,
            "summary_metrics": metrics,
            "created_at": created_at,
        }
        trade_payloads = [_payload(trade) for trade in trades]
        now = _now_iso()
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO replay_runs(
                        replay_run_id, simulation_type, backend, start, "end", symbols_json, intervals_json,
                        config_json, config_hash, input_fingerprint, candidate_fingerprint,
                        replay_config_version, feature_set_version, candidate_config_version,
                        label_config_version, stale_window_status_json,
                        summary_metrics_json, per_symbol_metrics_json, per_setup_metrics_json,
                        per_regime_metrics_json, per_time_bucket_metrics_json, skip_breakdown_json,
                        warnings_json, payload_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(replay_run_id) DO UPDATE SET
                        config_hash=excluded.config_hash,
                        input_fingerprint=excluded.input_fingerprint,
                        candidate_fingerprint=excluded.candidate_fingerprint,
                        replay_config_version=excluded.replay_config_version,
                        feature_set_version=excluded.feature_set_version,
                        candidate_config_version=excluded.candidate_config_version,
                        label_config_version=excluded.label_config_version,
                        stale_window_status_json=excluded.stale_window_status_json,
                        summary_metrics_json=excluded.summary_metrics_json,
                        per_symbol_metrics_json=excluded.per_symbol_metrics_json,
                        per_setup_metrics_json=excluded.per_setup_metrics_json,
                        per_regime_metrics_json=excluded.per_regime_metrics_json,
                        per_time_bucket_metrics_json=excluded.per_time_bucket_metrics_json,
                        skip_breakdown_json=excluded.skip_breakdown_json,
                        warnings_json=excluded.warnings_json,
                        payload_json=excluded.payload_json
                    """,
                    (
                        replay_run_id,
                        run_payload["simulation_type"],
                        backend,
                        run_payload.get("start"),
                        run_payload.get("end"),
                        _json_dumps(run_payload.get("symbols") or []),
                        _json_dumps(run_payload.get("intervals") or []),
                        _json_dumps(config),
                        run_payload.get("config_hash"),
                        run_payload.get("input_fingerprint"),
                        run_payload.get("candidate_fingerprint"),
                        run_payload.get("replay_config_version"),
                        run_payload.get("feature_set_version"),
                        run_payload.get("candidate_config_version"),
                        run_payload.get("label_config_version"),
                        _json_dumps(run_payload.get("stale_window_status") or {}),
                        _json_dumps(metrics),
                        _json_dumps(metrics.get("per_symbol_metrics") or {}),
                        _json_dumps(metrics.get("per_setup_metrics") or {}),
                        _json_dumps(metrics.get("per_regime_metrics") or {}),
                        _json_dumps(metrics.get("per_time_bucket_metrics") or {}),
                        _json_dumps(metrics.get("skip_breakdown") or {}),
                        _json_dumps(run_payload.get("warnings") or []),
                        _json_dumps(run_payload),
                        created_at,
                    ),
                )
                connection.execute("DELETE FROM simulated_trades WHERE replay_run_id = ?", (replay_run_id,))
                connection.executemany(
                    """
                    INSERT INTO simulated_trades(
                        trade_id, replay_run_id, candidate_id, symbol, interval, side, setup_type,
                        signal_timestamp_utc, entry_timestamp_utc, exit_timestamp_utc, entry_price, stop_price,
                        target_1, target_2, target_3, exit_price, exit_reason, realized_r, mfe_r, mae_r,
                        bars_held, minutes_held, same_bar_ambiguous, ambiguity_policy, slippage_bps,
                        spread_bps, commission, market_regime, time_bucket, signal_score, expected_r,
                        status, skip_reason, metadata_json, payload_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(trade_id) DO UPDATE SET
                        exit_timestamp_utc=excluded.exit_timestamp_utc,
                        exit_price=excluded.exit_price,
                        exit_reason=excluded.exit_reason,
                        realized_r=excluded.realized_r,
                        mfe_r=excluded.mfe_r,
                        mae_r=excluded.mae_r,
                        status=excluded.status,
                        skip_reason=excluded.skip_reason,
                        metadata_json=excluded.metadata_json,
                        payload_json=excluded.payload_json
                    """,
                    [
                        (
                            str(trade["trade_id"]),
                            replay_run_id,
                            trade.get("candidate_id"),
                            normalize_symbol(str(trade["symbol"])),
                            str(trade.get("interval") or "1min"),
                            str(trade["side"]),
                            str(trade["setup_type"]),
                            _maybe_datetime(trade.get("signal_timestamp_utc")).isoformat() if trade.get("signal_timestamp_utc") else None,
                            _maybe_datetime(trade.get("entry_timestamp_utc")).isoformat() if trade.get("entry_timestamp_utc") else None,
                            _maybe_datetime(trade.get("exit_timestamp_utc")).isoformat() if trade.get("exit_timestamp_utc") else None,
                            trade.get("entry_price"),
                            trade.get("stop_price"),
                            trade.get("target_1"),
                            trade.get("target_2"),
                            trade.get("target_3"),
                            trade.get("exit_price"),
                            trade.get("exit_reason"),
                            float(trade.get("realized_r") or 0.0),
                            float(trade.get("mfe_r") or 0.0),
                            float(trade.get("mae_r") or 0.0),
                            int(trade.get("bars_held") or 0),
                            float(trade.get("minutes_held") or 0.0),
                            bool(trade.get("same_bar_ambiguous")),
                            trade.get("ambiguity_policy"),
                            float(trade.get("slippage_bps") or 0.0),
                            float(trade.get("spread_bps") or 0.0),
                            float(trade.get("commission") or 0.0),
                            trade.get("market_regime"),
                            trade.get("time_bucket"),
                            trade.get("signal_score"),
                            trade.get("expected_r"),
                            str(trade.get("status") or "TAKEN"),
                            trade.get("skip_reason"),
                            _json_dumps(trade.get("metadata") or {}),
                            _json_dumps(trade | {"replay_run_id": replay_run_id}),
                            now,
                        )
                        for trade in trade_payloads
                    ],
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return run_payload | {"trades_written": len(trade_payloads)}

    def get(self, replay_run_id: str) -> dict[str, Any] | None:
        connection = self.store.connect()
        try:
            row = connection.execute("SELECT payload_json FROM replay_runs WHERE replay_run_id = ?", (replay_run_id,)).fetchone()
            return _json_loads(row["payload_json"]) if row else None
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def list_runs(self) -> list[dict[str, Any]]:
        connection = self.store.connect()
        try:
            rows = connection.execute("SELECT payload_json FROM replay_runs ORDER BY created_at DESC").fetchall()
            return [_json_loads(row["payload_json"]) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def select(self, replay_filter: dict[str, Any]) -> dict[str, Any] | None:
        matches = [run for run in self.list_runs() if self._matches_filter(run, replay_filter)]
        if not matches:
            return None
        return sorted(
            matches,
            key=lambda run: (str(run.get("created_at") or ""), str(run.get("replay_run_id") or "")),
            reverse=True,
        )[0]

    def filter(self, replay_filter: dict[str, Any]) -> list[dict[str, Any]]:
        return sorted(
            [run for run in self.list_runs() if self._matches_filter(run, replay_filter)],
            key=lambda run: (str(run.get("created_at") or ""), str(run.get("replay_run_id") or "")),
        )

    def _matches_filter(self, replay_run: dict[str, Any], replay_filter: dict[str, Any]) -> bool:
        if replay_filter.get("simulation_type") and str(replay_run.get("simulation_type")) != str(replay_filter["simulation_type"]):
            return False
        if replay_filter.get("replay_purpose"):
            config = dict(replay_run.get("config") or {})
            if str(config.get("replay_purpose") or replay_run.get("replay_purpose") or "") != str(replay_filter["replay_purpose"]):
                return False
        symbols = [normalize_symbol(str(symbol)) for symbol in replay_filter.get("symbols") or []]
        if symbols and set(symbols) - {normalize_symbol(str(symbol)) for symbol in replay_run.get("symbols") or []}:
            return False
        intervals = [str(interval) for interval in replay_filter.get("intervals") or []]
        if intervals and set(intervals) - {str(interval) for interval in replay_run.get("intervals") or []}:
            return False
        if replay_filter.get("start") and str(replay_run.get("start")) != str(replay_filter["start"]):
            return False
        if replay_filter.get("end") and str(replay_run.get("end")) != str(replay_filter["end"]):
            return False
        if replay_filter.get("model_version") and str(replay_run.get("model_version")) != str(replay_filter["model_version"]):
            return False
        if replay_filter.get("feature_set_version") and str(replay_run.get("feature_set_version")) != str(replay_filter["feature_set_version"]):
            return False
        if replay_filter.get("replay_config_hash") and str(replay_run.get("config_hash")) != str(replay_filter["replay_config_hash"]):
            return False
        if replay_filter.get("minimum_created_at") and str(replay_run.get("created_at") or "") < str(replay_filter["minimum_created_at"]):
            return False
        if replay_filter.get("maximum_created_at") and str(replay_run.get("created_at") or "") > str(replay_filter["maximum_created_at"]):
            return False
        return True

    def list_trades(
        self,
        replay_run_id: str,
        limit: int = 500,
        offset: int = 0,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT payload_json FROM simulated_trades WHERE replay_run_id = ?"
        params: list[Any] = [replay_run_id]
        if status is not None:
            sql += " AND status = ?"
            params.append(status)
        sql += " ORDER BY signal_timestamp_utc, symbol, setup_type LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        connection = self.store.connect()
        try:
            rows = connection.execute(sql, params).fetchall()
            return [_json_loads(row["payload_json"]) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class ReplaySensitivityRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save(self, sensitivity_run: dict[str, Any]) -> dict[str, Any]:
        payload = _payload(sensitivity_run)
        scenarios = [_payload(scenario) for scenario in payload.get("scenarios") or []]
        sensitivity_run_id = str(payload["sensitivity_run_id"])
        replay_run_id = str(payload["replay_run_id"])
        created_at = str(payload.get("created_at") or _now_iso())
        summary = {
            "scenario_count": payload.get("scenario_count"),
            "passed_scenario_count": payload.get("passed_scenario_count"),
            "failed_scenario_count": payload.get("failed_scenario_count"),
            "robustness_score": payload.get("robustness_score"),
            "pass_fail": payload.get("pass_fail"),
            "worst_case": payload.get("worst_case"),
            "median_case": payload.get("median_case"),
            "best_case": payload.get("best_case"),
        }
        row_payload = payload | {"created_at": created_at}
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO replay_sensitivity_runs(
                        sensitivity_run_id, replay_run_id, config_json, summary_json,
                        gate_results_json, fragility_flags_json, payload_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sensitivity_run_id) DO UPDATE SET
                        config_json=excluded.config_json,
                        summary_json=excluded.summary_json,
                        gate_results_json=excluded.gate_results_json,
                        fragility_flags_json=excluded.fragility_flags_json,
                        payload_json=excluded.payload_json
                    """,
                    (
                        sensitivity_run_id,
                        replay_run_id,
                        _json_dumps(row_payload.get("config") or {}),
                        _json_dumps(summary),
                        _json_dumps(row_payload.get("gate_results") or {}),
                        _json_dumps(row_payload.get("fragility_flags") or []),
                        _json_dumps(row_payload),
                        created_at,
                    ),
                )
                connection.execute(
                    "DELETE FROM replay_sensitivity_scenarios WHERE sensitivity_run_id = ?",
                    (sensitivity_run_id,),
                )
                connection.executemany(
                    """
                    INSERT INTO replay_sensitivity_scenarios(
                        scenario_id, sensitivity_run_id, replay_run_id, slippage_bps, spread_bps,
                        intrabar_path_policy, same_bar_stop_target_policy, summary_metrics_json,
                        gate_results_json, payload_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(scenario_id) DO UPDATE SET
                        summary_metrics_json=excluded.summary_metrics_json,
                        gate_results_json=excluded.gate_results_json,
                        payload_json=excluded.payload_json
                    """,
                    [
                        (
                            str(scenario["scenario_id"]),
                            sensitivity_run_id,
                            replay_run_id,
                            float(scenario.get("slippage_bps") or 0.0),
                            float(scenario.get("spread_bps") or 0.0),
                            str(scenario.get("intrabar_path_policy") or "conservative"),
                            str(scenario.get("same_bar_stop_target_policy") or "conservative_stop_first"),
                            _json_dumps(scenario.get("summary_metrics") or {}),
                            _json_dumps(scenario.get("gate_results") or {}),
                            _json_dumps(scenario | {"sensitivity_run_id": sensitivity_run_id, "replay_run_id": replay_run_id}),
                            created_at,
                        )
                        for scenario in scenarios
                    ],
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return row_payload | {"scenarios_written": len(scenarios)}

    def get(self, sensitivity_run_id: str) -> dict[str, Any] | None:
        connection = self.store.connect()
        try:
            row = connection.execute(
                "SELECT payload_json FROM replay_sensitivity_runs WHERE sensitivity_run_id = ?",
                (sensitivity_run_id,),
            ).fetchone()
            return _json_loads(row["payload_json"]) if row else None
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def list_for_replay(self, replay_run_id: str) -> list[dict[str, Any]]:
        connection = self.store.connect()
        try:
            rows = connection.execute(
                "SELECT payload_json FROM replay_sensitivity_runs WHERE replay_run_id = ? ORDER BY created_at DESC",
                (replay_run_id,),
            ).fetchall()
            return [_json_loads(row["payload_json"]) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def list_scenarios(self, sensitivity_run_id: str) -> list[dict[str, Any]]:
        connection = self.store.connect()
        try:
            rows = connection.execute(
                """
                SELECT payload_json FROM replay_sensitivity_scenarios
                WHERE sensitivity_run_id = ?
                ORDER BY slippage_bps, spread_bps, intrabar_path_policy, same_bar_stop_target_policy
                """,
                (sensitivity_run_id,),
            ).fetchall()
            return [_json_loads(row["payload_json"]) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class BacktestComparisonRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save(self, comparison: dict[str, Any]) -> dict[str, Any]:
        payload = _payload(comparison)
        created_at = str(payload.get("created_at") or _now_iso())
        comparison_id = str(
            payload.get("comparison_id")
            or _stable_id("comparison", payload.get("comparison_type") or "label_vs_replay", payload.get("replay_run_id"), created_at)
        )
        row_payload = payload | {"comparison_id": comparison_id, "created_at": created_at}
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO backtest_comparisons(
                        comparison_id, label_run_id, replay_run_id, comparison_type,
                        summary_json, payload_json, created_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(comparison_id) DO UPDATE SET
                        summary_json=excluded.summary_json,
                        payload_json=excluded.payload_json
                    """,
                    (
                        comparison_id,
                        row_payload.get("label_run_id"),
                        str(row_payload["replay_run_id"]),
                        str(row_payload.get("comparison_type") or "label_vs_replay"),
                        _json_dumps(row_payload.get("summary") or {}),
                        _json_dumps(row_payload),
                        created_at,
                    ),
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return row_payload

    def get(self, comparison_id: str) -> dict[str, Any] | None:
        connection = self.store.connect()
        try:
            row = connection.execute(
                "SELECT payload_json FROM backtest_comparisons WHERE comparison_id = ?",
                (comparison_id,),
            ).fetchone()
            return _json_loads(row["payload_json"]) if row else None
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def list_for_replay(self, replay_run_id: str) -> list[dict[str, Any]]:
        connection = self.store.connect()
        try:
            rows = connection.execute(
                """
                SELECT payload_json FROM backtest_comparisons
                WHERE replay_run_id = ?
                ORDER BY created_at DESC
                """,
                (replay_run_id,),
            ).fetchall()
            return [_json_loads(row["payload_json"]) for row in rows]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class PipelineBuildWindowRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def list_dirty(
        self,
        artifact_type: str | None = None,
        symbols: Iterable[str] | None = None,
        intervals: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        clauses = ["dirty = ?"]
        params: list[Any] = [True]
        if artifact_type is not None:
            clauses.append("artifact_type = ?")
            params.append(artifact_type)
        normalized_symbols = [normalize_symbol(symbol) for symbol in symbols or []]
        if normalized_symbols:
            clauses.append(f"symbol IN ({','.join('?' for _ in normalized_symbols)})")
            params.extend(normalized_symbols)
        interval_values = [str(interval) for interval in intervals or []]
        if interval_values:
            clauses.append(f"interval IN ({','.join('?' for _ in interval_values)})")
            params.extend(interval_values)
        sql = "SELECT * FROM pipeline_build_windows WHERE " + " AND ".join(clauses)  # noqa: S608 - fixed clauses with bound parameters.
        sql += " ORDER BY artifact_type, symbol, interval, session_date"
        connection = self.store.connect()
        try:
            return [self._row(row) for row in connection.execute(sql, params).fetchall()]
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()

    def status(
        self,
        symbols: Iterable[str] | None = None,
        intervals: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        dirty = self.list_dirty(symbols=symbols, intervals=intervals)
        by_artifact: dict[str, int] = {}
        for row in dirty:
            artifact_type = str(row.get("artifact_type") or "unknown")
            by_artifact[artifact_type] = by_artifact.get(artifact_type, 0) + 1
        return {
            "status": "stale" if dirty else "clean",
            "dirty_window_count": len(dirty),
            "dirty_by_artifact": by_artifact,
            "dirty_windows": dirty,
        }

    def mark_built(
        self,
        artifact_type: str,
        symbols: Iterable[str],
        intervals: Iterable[str],
        start: datetime | None,
        end: datetime | None,
        version: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        now = _now_iso()
        rows = []
        selected_symbols = [normalize_symbol(symbol) for symbol in symbols]
        selected_intervals = [str(interval) for interval in intervals]
        session_date = _date_text(start or end)
        with self.store._lock:
            connection = self.store.connect()
            try:
                for symbol in selected_symbols:
                    for interval in selected_intervals:
                        build_window_id = _stable_id("build_window", artifact_type, symbol, interval, session_date, version)
                        payload = {
                            "artifact_type": artifact_type,
                            "symbol": symbol,
                            "interval": interval,
                            "session_date": session_date,
                            "start": start.isoformat() if start else None,
                            "end": end.isoformat() if end else None,
                            "version": version,
                            "dirty": False,
                            "metadata": metadata or {},
                        }
                        connection.execute(
                            """
                            INSERT INTO pipeline_build_windows(
                                build_window_id, artifact_type, symbol, interval, session_date, start, "end",
                                version, dirty, stale_reason, payload_json, created_at, updated_at
                            )
                            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(artifact_type, symbol, interval, session_date, version) DO UPDATE SET
                                start=excluded.start,
                                "end"=excluded."end",
                                dirty=excluded.dirty,
                                stale_reason=excluded.stale_reason,
                                payload_json=excluded.payload_json,
                                updated_at=excluded.updated_at
                            """,
                            (
                                build_window_id,
                                artifact_type,
                                symbol,
                                interval,
                                session_date,
                                start.isoformat() if start else None,
                                end.isoformat() if end else None,
                                version,
                                False,
                                None,
                                _json_dumps(payload),
                                now,
                                now,
                            ),
                        )
                        rows.append(payload | {"build_window_id": build_window_id})
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return rows

    def _row(self, row: Any) -> dict[str, Any]:
        data = dict(row)
        data["dirty"] = bool(data.get("dirty"))
        data["payload"] = _json_loads(data.pop("payload_json"))
        return data


class ExportRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def record(
        self,
        export_type: str,
        fmt: str,
        path: Path | str,
        row_count: int = 0,
        source_run_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        created_at = _now_iso()
        export_id = _stable_id("export", export_type, fmt, path, created_at)
        audit_payload = dict(payload or {})
        file_hash = _file_sha256(path)
        workbook_sheets = _xlsx_sheet_names(path)
        audit_payload.update(
            {
                "file_sha256": file_hash,
                "workbook_sheets": workbook_sheets,
                "row_count": row_count,
                "source_run_id": source_run_id,
                "export_type": export_type,
                "format": fmt,
                "created_at": created_at,
            }
        )
        row = {
            "export_id": export_id,
            "export_type": export_type,
            "format": fmt,
            "path": str(path),
            "row_count": row_count,
            "source_run_id": source_run_id,
            "created_at": created_at,
            "payload": audit_payload,
            "file_sha256": file_hash,
            "workbook_sheets": workbook_sheets,
        }
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO exports(export_id, export_type, format, path, row_count, source_run_id, payload_json, created_at)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (export_id, export_type, fmt, str(path), row_count, source_run_id, _json_dumps(audit_payload), created_at),
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return row

    def list_all(self) -> list[dict[str, Any]]:
        connection = self.store.connect()
        try:
            rows = connection.execute("SELECT * FROM exports ORDER BY created_at DESC").fetchall()
            output = []
            for row in rows:
                data = dict(row)
                data["payload"] = _json_loads(data.pop("payload_json"))
                if isinstance(data["payload"], dict):
                    data["file_sha256"] = data["payload"].get("file_sha256")
                    data["workbook_sheets"] = data["payload"].get("workbook_sheets") or []
                output.append(data)
            return output
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


class DailyReviewRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def save(self, review_date: date, payload: dict[str, Any]) -> dict[str, Any]:
        now = _now_iso()
        review_id = _stable_id("daily_review", review_date.isoformat())
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO daily_reviews(review_id, review_date, payload_json, created_at, updated_at)
                    VALUES(?, ?, ?, ?, ?)
                    ON CONFLICT(review_date) DO UPDATE SET
                        payload_json=excluded.payload_json,
                        updated_at=excluded.updated_at
                    """,
                    (review_id, review_date.isoformat(), _json_dumps(payload), now, now),
                )
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return {"review_id": review_id, "review_date": review_date.isoformat(), "payload": payload}

    def get(self, review_date: date) -> dict[str, Any] | None:
        connection = self.store.connect()
        try:
            row = connection.execute("SELECT * FROM daily_reviews WHERE review_date = ?", (review_date.isoformat(),)).fetchone()
            if row is None:
                return None
            data = dict(row)
            data["payload"] = _json_loads(data.pop("payload_json"))
            return data
        finally:
            if str(self.store.path) != ":memory:":
                connection.close()


def database_url_kind(settings: Settings | None = None) -> str:
    configured = getattr(settings or get_settings(), "database_url", "") or ""
    if not configured:
        return "unset"
    if configured.startswith("sqlite:///"):
        return "sqlite"
    if configured.startswith("postgres://") or configured.startswith("postgresql://") or configured.startswith("postgresql+"):
        return "postgresql"
    return configured.split(":", maxsplit=1)[0] or "unknown"


def _sqlite_info(
    runtime_mode: str,
    reason: str,
    path: Path,
    database_configured: bool,
    fallback_enabled: bool = False,
    fallback_reason: str | None = None,
    database_url_kind_value: str | None = None,
) -> dict[str, Any]:
    return {
        "persistence_backend": "sqlite",
        "backend": "sqlite",
        "runtime_mode": runtime_mode,
        "runtime": runtime_mode,
        "reason": reason,
        "database_configured": database_configured,
        "database_url_configured": database_configured,
        "database_url_kind": database_url_kind_value or ("sqlite" if database_configured else "unset"),
        "database_reachable": True,
        "fallback_enabled": fallback_enabled,
        "fallback_reason": fallback_reason,
        "path": str(path),
    }


class RepositoryRegistry:
    def __init__(self, db_path: Path | str | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.database_url_kind = database_url_kind(self.settings)
        self.fallback_enabled = _env_flag("AMD_ALLOW_SQLITE_FALLBACK")
        self.db_path = Path(db_path) if db_path is not None else default_sqlite_path(self.settings)
        self.backend = "sqlite"
        self.runtime: dict[str, Any]
        if self.database_url_kind == "postgresql":
            try:
                self.store = PostgresStore(self.settings.database_url)
                self.backend = "postgresql"
                self.runtime = {
                    "persistence_backend": "postgresql",
                    "backend": "postgresql",
                    "runtime_mode": "postgresql",
                    "runtime": "postgresql",
                    "reason": "postgresql_database_url_configured",
                    "database_configured": True,
                    "database_url_configured": True,
                    "database_url_kind": "postgresql",
                    "database_reachable": True,
                    "fallback_enabled": self.fallback_enabled,
                    "fallback_reason": None,
                    **self.store.descriptor,
                }
            except PersistenceConfigurationError as exc:
                if not self.fallback_enabled:
                    raise
                self.store = SQLiteStore(self.db_path)
                self.runtime = _sqlite_info(
                    "sqlite-fallback-from-postgres",
                    "postgresql_initialization_failed_explicit_fallback_enabled",
                    self.db_path,
                    database_configured=True,
                    fallback_enabled=True,
                    fallback_reason=str(exc.safe_info.get("fallback_reason") or "postgres_initialization_failed"),
                    database_url_kind_value="postgresql",
                )
        else:
            self.store = SQLiteStore(self.db_path)
            self.runtime = _sqlite_info(
                "sqlite-configured" if self.database_url_kind == "sqlite" else "sqlite-local",
                "sqlite_database_url_configured" if self.database_url_kind == "sqlite" else "database_url_not_configured",
                self.db_path,
                database_configured=self.database_url_kind == "sqlite",
                fallback_enabled=self.fallback_enabled,
                database_url_kind_value=self.database_url_kind,
            )
        self.symbols = SymbolRepository(self.store)
        self.bars = BarRepository(self.store, self.symbols)
        self.features = FeatureRepository(self.store)
        self.candidate_signals = CandidateSignalRepository(self.store)
        self.labels = LabelRepository(self.store)
        self.validation_reports = ValidationReportRepository(self.store)
        self.model_runs = ModelRunRepository(self.store, self.settings)
        self.model_evidence_cells = ModelEvidenceCellRepository(self.store)
        self.candidate_score_audits = CandidateScoreAuditRepository(self.store)
        self.model_calibration_audits = CalibrationAuditRepository(self.store)
        self.model_comparisons = ModelComparisonRepository(self.store)
        self.active_models = ActiveModelRepository(self.store, self.model_runs)
        self.live_signals = LiveSignalRepository(self.store)
        self.scanner_runs = ScannerRunRepository(self.store)
        self.provider_requests = ProviderRequestRepository(self.store)
        self.replays = ReplayRepository(self.store)
        self.replay_sensitivity = ReplaySensitivityRepository(self.store)
        self.backtest_comparisons = BacktestComparisonRepository(self.store)
        self.pipeline_windows = PipelineBuildWindowRepository(self.store)
        self.exports = ExportRepository(self.store)
        self.daily_reviews = DailyReviewRepository(self.store)

    def info(self) -> dict[str, Any]:
        info = dict(self.runtime)
        try:
            info["database_reachable"] = bool(self.store.ping())
        except Exception:
            info["database_reachable"] = False
        return info


def persistence_backend_info(
    settings: Settings | None = None,
    db_path: Path | str | None = None,
) -> dict[str, Any]:
    try:
        return RepositoryRegistry(db_path=db_path, settings=settings).info()
    except PersistenceConfigurationError as exc:
        return dict(exc.safe_info)


def default_sqlite_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    configured = getattr(settings, "database_url", "") or ""
    if configured.startswith("sqlite:///"):
        return Path(configured.removeprefix("sqlite:///"))
    import os

    if os.environ.get("AMD_SQLITE_PATH"):
        return Path(os.environ["AMD_SQLITE_PATH"])
    return settings.data_dir / "local_repo.sqlite3"


@lru_cache(maxsize=4)
def get_repository_registry(db_path: str | None = None) -> RepositoryRegistry:
    return RepositoryRegistry(Path(db_path) if db_path else None)


def reset_repository_registry() -> None:
    get_repository_registry.cache_clear()


QuantRepositoryRegistry = RepositoryRegistry
