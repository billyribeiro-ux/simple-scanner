from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, text

from app.config import get_settings
from app.db.repositories import (
    EXPECTED_TABLES,
    PersistenceConfigurationError,
    RepositoryRegistry,
    _sync_postgres_url,
    reset_repository_registry,
)
from app.schemas.market import Bar, Outcome, Side, Signal
from app.utils.time import UTC

ET = ZoneInfo("America/New_York")
DEFAULT_POSTGRES_URL = "postgresql+psycopg://amd:amd@localhost:15432/adaptive_market_decoder"


def _postgres_available(database_url: str = DEFAULT_POSTGRES_URL) -> bool:
    try:
        engine = create_engine(_sync_postgres_url(database_url), future=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _clear_postgres_tables(repo: RepositoryRegistry) -> None:
    tables = sorted(EXPECTED_TABLES - {"alembic_version"})
    quoted = ", ".join(f'"{table}"' for table in tables)
    with repo.store.engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


def _bar(symbol: str, index: int, close: float, day: int = 1) -> Bar:
    timestamp_et = datetime(2026, 6, day, 9, 30, tzinfo=ET) + timedelta(minutes=index)
    return Bar(
        symbol=symbol,
        interval="1min",
        timestamp_utc=timestamp_et.astimezone(UTC),
        timestamp_et=timestamp_et,
        open=close - 0.05,
        high=close + 0.25,
        low=close - 0.20,
        close=close,
        volume=1_000 + index * 10,
        source="parity",
    )


def _feature(bar: Bar) -> dict[str, object]:
    return {
        "feature_set_version": "parity",
        "symbol": bar.symbol,
        "interval": bar.interval,
        "timestamp": bar.timestamp_utc.isoformat(),
        "timestamp_utc": bar.timestamp_utc,
        "timestamp_et": bar.timestamp_et,
        "session_date": bar.timestamp_et.date().isoformat(),
        "close": bar.close,
        "previous_close": bar.open,
        "vwap": bar.close - 0.40,
        "distance_from_vwap": 0.004,
        "relative_volume": 1.6,
        "trend_slope_5": 0.006,
        "trend_slope_20": 0.002,
        "atr_14_proxy": 1.0,
        "market_regime": "trend_long",
        "ticker_regime": "single_stock_momentum",
        "data_quality_flags": [],
    }


def _label(symbol: str, index: int, realized_r: float, outcome: Outcome) -> dict[str, object]:
    timestamp = datetime(2026, 6, 1, 13, 30, tzinfo=UTC) + timedelta(minutes=index)
    return {
        "label_id": f"label-{symbol}-{index}",
        "symbol": symbol,
        "interval": "1min",
        "timestamp": timestamp,
        "timestamp_utc": timestamp,
        "side": Side.LONG.value,
        "setup_type": "VWAP reclaim long",
        "label_config_version": "parity",
        "entry_price": 100,
        "stop_price": 99,
        "target_1": 101,
        "target_2": 101.5,
        "target_3": 102.5,
        "realized_r": realized_r,
        "outcome": outcome.value,
        "market_regime": "trend_long",
        "max_favorable_excursion": max(realized_r, 0),
        "max_adverse_excursion": min(realized_r, 0),
        "hit_target_1": realized_r >= 1,
        "hit_target_2": realized_r >= 1.5,
        "hit_target_3": realized_r >= 2.5,
        "hit_stop": realized_r < 0,
    }


def _signal(symbol: str = "AAPL") -> Signal:
    return Signal(
        timestamp=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
        ticker=symbol,
        side=Side.LONG,
        entry_price=100,
        stop_price=99,
        target_1=101,
        target_2=101.5,
        target_3=102.5,
        risk_per_share=1,
        reward_risk_to_t1=1,
        reward_risk_to_t2=1.5,
        reward_risk_to_t3=2.5,
        expected_r=0.25,
        confidence_score=0.76,
        signal_grade="A-",
        setup_type="VWAP reclaim long",
        market_regime="trend_long",
        ticker_regime="single_stock_momentum",
        reasons=["parity"],
        warnings=[],
        historical_sample_size=40,
        historical_win_rate=0.6,
        historical_average_r=0.25,
        model_version="parity-model-accepted",
    )


def _settings_for_current_env(monkeypatch, tmp_path, database_url: str | None = None):
    reset_repository_registry()
    get_settings.cache_clear()
    monkeypatch.setenv("AMD_SQLITE_PATH", str(tmp_path / "parity.sqlite3"))
    monkeypatch.delenv("AMD_ALLOW_SQLITE_FALLBACK", raising=False)
    if database_url:
        monkeypatch.setenv("DATABASE_URL", database_url)
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    return get_settings()


def _repo_for_backend(monkeypatch, tmp_path, backend: str) -> RepositoryRegistry:
    database_url = DEFAULT_POSTGRES_URL if backend == "postgresql" else None
    if backend == "postgresql" and not _postgres_available(database_url or DEFAULT_POSTGRES_URL):
        pytest.skip("local Postgres/TimescaleDB is not available for repository parity")
    settings = _settings_for_current_env(monkeypatch, tmp_path, database_url)
    repo = RepositoryRegistry(settings=settings)
    if backend == "postgresql":
        _clear_postgres_tables(repo)
    return repo


@pytest.mark.parametrize("backend", ["sqlite", "postgresql"])
def test_repository_core_contract_parity(tmp_path, monkeypatch, backend: str) -> None:
    repo = _repo_for_backend(monkeypatch, tmp_path, backend)
    info = repo.info()
    assert info["persistence_backend"] == backend
    assert info["database_reachable"] is True

    symbols = ["APPL", "SPY", "QQQ", "NVDA"]
    assert repo.symbols.upsert_many(symbols) == 4
    assert {row["symbol"] for row in repo.symbols.list_all()} == {"AAPL", "SPY", "QQQ", "NVDA"}

    bars = []
    for symbol in ["AAPL", "SPY", "QQQ", "NVDA"]:
        bars.extend(_bar(symbol, index, 100 + index * 0.1, day=1) for index in range(12))
        bars.extend(_bar(symbol, index, 102 + index * 0.1, day=2) for index in range(12))
    assert repo.bars.upsert_many(bars) == 96
    assert repo.bars.upsert_many(bars[:4]) == 4
    assert len(repo.bars.query(symbols=["AAPL"], start=bars[0].timestamp_utc, end=bars[-1].timestamp_utc)) == 24

    features = [_feature(bar) for bar in bars]
    assert repo.features.upsert_many(features) == 96
    assert len(repo.features.query(symbols=["AAPL"], intervals=["1min"])) == 24

    candidates = [
        {
            "candidate_id": f"candidate-{symbol}",
            "symbol": symbol,
            "interval": "1min",
            "timestamp_utc": bars[index].timestamp_utc,
            "side": Side.LONG.value,
            "setup_type": "VWAP reclaim long",
            "reason_codes": ["parity"],
            "warning_codes": [],
        }
        for index, symbol in enumerate(["AAPL", "SPY", "QQQ", "NVDA"])
    ]
    assert repo.candidate_signals.upsert_many(candidates) == 4
    assert len(repo.candidate_signals.list_all()) == 4

    labels = [
        _label("AAPL", 0, 1.5, Outcome.WIN),
        _label("SPY", 1, -1.0, Outcome.LOSS),
        _label("QQQ", 2, 0.5, Outcome.NEUTRAL),
        _label("NVDA", 3, 2.0, Outcome.WIN),
    ]
    assert repo.labels.upsert_many(labels) == 4
    assert len(repo.labels.query(symbols=["AAPL", "SPY"])) == 2

    model = {
        "model_version": "parity-model-accepted",
        "model_type": "statistical_evidence_baseline",
        "feature_set_version": "parity",
        "label_config_version": "parity",
        "training_start": "2026-06-01T13:30:00+00:00",
        "training_end": "2026-06-02T14:30:00+00:00",
        "activation_decision": "accepted",
        "metrics": {"total_trades": 40, "average_r": 0.25, "profit_factor": 1.6},
        "validation_metrics": {"passes_activation_gate": True},
        "created_at": datetime.now(UTC).isoformat(),
    }
    assert repo.model_runs.save(model)["model_version"] == "parity-model-accepted"
    rejected = repo.validation_reports.save(
        {
            "model_version": "parity-model-accepted",
            "summary": {},
            "windows": [],
            "activation_decision": "rejected",
            "rejection_reasons": ["controlled_rejection"],
            "created_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        },
        model_version="parity-model-accepted",
    )
    assert rejected["activation_decision"] == "rejected"
    accepted = repo.validation_reports.save(
        {
            "model_version": "parity-model-accepted",
            "summary": {"total_trades": 40, "average_r": 0.25},
            "windows": [],
            "activation_decision": "accepted",
            "rejection_reasons": [],
            "created_at": datetime.now(UTC).isoformat(),
        },
        model_version="parity-model-accepted",
    )
    active = repo.active_models.activate(model, validation_report_id=accepted["report_id"])
    assert active["model_version"] == "parity-model-accepted"

    scanner_run_id = repo.scanner_runs.start(["AAPL", "SPY"], 0.7, "parity-model-accepted")
    repo.live_signals.upsert_many([_signal("AAPL")], scanner_run_id=scanner_run_id)
    repo.scanner_runs.finish(scanner_run_id, status="stopped", stats={"latest_count": 1})
    repo.provider_requests.record(
        provider="fmp",
        endpoint="batch-quote",
        status="ok",
        row_count=2,
        metadata={"symbols": ["AAPL", "SPY"]},
    )
    export = repo.exports.record("live_signals", "csv", tmp_path / "signals.csv", row_count=1)
    review = repo.daily_reviews.save(date(2026, 6, 1), {"date": "2026-06-01", "signals_reviewed": 1})

    reopened = RepositoryRegistry(settings=get_settings())
    assert len(reopened.bars.list_all()) == 96
    assert len(reopened.features.list_all()) == 96
    assert len(reopened.candidate_signals.list_all()) == 4
    assert len(reopened.labels.list_all()) == 4
    assert reopened.model_runs.get("parity-model-accepted")["model_version"] == "parity-model-accepted"
    assert reopened.validation_reports.latest(model_version="parity-model-accepted")["activation_decision"] == "accepted"
    assert reopened.active_models.get_active()["model_version"] == "parity-model-accepted"
    assert reopened.scanner_runs.latest()["scanner_run_id"] == scanner_run_id
    assert len(reopened.live_signals.history()) == 1
    assert reopened.exports.list_all()[0]["export_id"] == export["export_id"]
    assert reopened.daily_reviews.get(date(2026, 6, 1))["review_id"] == review["review_id"]
    assert "apikey" not in str(reopened.provider_requests.list_all()).lower()


def test_backend_selection_contract(tmp_path, monkeypatch) -> None:
    settings = _settings_for_current_env(monkeypatch, tmp_path)
    sqlite_local = RepositoryRegistry(settings=settings)
    assert sqlite_local.info()["runtime_mode"] == "sqlite-local"

    sqlite_url = f"sqlite:///{tmp_path / 'configured.sqlite3'}"
    settings = _settings_for_current_env(monkeypatch, tmp_path, sqlite_url)
    sqlite_configured = RepositoryRegistry(settings=settings)
    assert sqlite_configured.info()["runtime_mode"] == "sqlite-configured"

    bad_postgres = "postgresql+psycopg://amd:amd@127.0.0.1:1/adaptive_market_decoder"
    settings = _settings_for_current_env(monkeypatch, tmp_path, bad_postgres)
    with pytest.raises(PersistenceConfigurationError):
        RepositoryRegistry(settings=settings)

    monkeypatch.setenv("AMD_ALLOW_SQLITE_FALLBACK", "true")
    get_settings.cache_clear()
    fallback = RepositoryRegistry(settings=get_settings())
    info = fallback.info()
    assert info["persistence_backend"] == "sqlite"
    assert info["runtime_mode"] == "sqlite-fallback-from-postgres"
    assert info["fallback_enabled"] is True
