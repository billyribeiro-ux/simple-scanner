from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any, Iterable

from app.config import Settings, get_settings
from app.data.symbols import normalize_symbol
from app.schemas.market import Bar, Label, Outcome, Signal, Side, SignalStatus
from app.utils.time import UTC


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
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
    return json.dumps(_to_jsonable(payload), sort_keys=True, separators=(",", ":"))


def _json_loads(payload: str | None) -> Any:
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


def _payload(obj: Any) -> dict[str, Any]:
    data = _to_jsonable(obj)
    if isinstance(data, dict):
        return data
    raise TypeError(f"Expected mapping-like payload, got {type(obj).__name__}")


def _date_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
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
                connection.commit()
            finally:
                if str(self.path) != ":memory:":
                    connection.close()


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
        seen_symbols: set[str] = set()
        now = _now_iso()
        for bar in bars:
            payload = _payload(bar)
            symbol = normalize_symbol(str(payload["symbol"]))
            interval = str(payload["interval"])
            timestamp_utc = _parse_datetime(payload["timestamp_utc"]).isoformat()
            timestamp_et = _maybe_datetime(payload.get("timestamp_et"))
            timestamp_et_text = timestamp_et.isoformat() if timestamp_et else None
            source = str(payload.get("source") or "unknown")
            row_id = _stable_id("bar", symbol, interval, timestamp_utc, source)
            seen_symbols.add(symbol)
            rows.append(
                (
                    row_id,
                    symbol,
                    interval,
                    timestamp_utc,
                    timestamp_et_text,
                    _date_text(timestamp_et or timestamp_utc),
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
                connection.commit()
            finally:
                if str(self.store.path) != ":memory:":
                    connection.close()
        return len(rows)

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
    ) -> list[dict[str, Any]]:
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
        connection = self.store.connect()
        try:
            rows = connection.execute("SELECT payload_json FROM candidate_signals ORDER BY timestamp_utc").fetchall()
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
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Label]:
        clauses: list[str] = []
        params: list[Any] = []
        normalized_symbols = [normalize_symbol(symbol) for symbol in symbols or []]
        if normalized_symbols:
            clauses.append(f"symbol IN ({','.join('?' for _ in normalized_symbols)})")
            params.extend(normalized_symbols)
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
                            1 if window_payload.get("accepted") else 0,
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
                        1 if payload.get("active") else 0,
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
                    (1 if active else 0, _json_dumps(model) if model else None, _now_iso(), model_version),
                )
                connection.commit()
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
                connection.execute("UPDATE model_runs SET active = 0, updated_at = ?", (_now_iso(),))
                connection.execute("UPDATE model_runs SET active = 1, payload_json = ?, updated_at = ? WHERE model_version = ?", (_json_dumps(payload), _now_iso(), model_version))
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
        row = {
            "export_id": export_id,
            "export_type": export_type,
            "format": fmt,
            "path": str(path),
            "row_count": row_count,
            "source_run_id": source_run_id,
            "created_at": created_at,
            "payload": payload or {},
        }
        with self.store._lock:
            connection = self.store.connect()
            try:
                connection.execute(
                    """
                    INSERT INTO exports(export_id, export_type, format, path, row_count, source_run_id, payload_json, created_at)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (export_id, export_type, fmt, str(path), row_count, source_run_id, _json_dumps(payload or {}), created_at),
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


class RepositoryRegistry:
    def __init__(self, db_path: Path | str | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.db_path = Path(db_path) if db_path is not None else default_sqlite_path(self.settings)
        self.store = SQLiteStore(self.db_path)
        self.symbols = SymbolRepository(self.store)
        self.bars = BarRepository(self.store, self.symbols)
        self.features = FeatureRepository(self.store)
        self.candidate_signals = CandidateSignalRepository(self.store)
        self.labels = LabelRepository(self.store)
        self.validation_reports = ValidationReportRepository(self.store)
        self.model_runs = ModelRunRepository(self.store, self.settings)
        self.active_models = ActiveModelRepository(self.store, self.model_runs)
        self.live_signals = LiveSignalRepository(self.store)
        self.scanner_runs = ScannerRunRepository(self.store)
        self.provider_requests = ProviderRequestRepository(self.store)
        self.exports = ExportRepository(self.store)
        self.daily_reviews = DailyReviewRepository(self.store)


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
