from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine, text

from app.config import get_settings
from app.data.symbols import normalize_symbol, normalize_symbols
from app.db.repositories import (
    EXPECTED_TABLES,
    _sync_postgres_url,
    get_repository_registry,
    reset_repository_registry,
)
from app.schemas.market import Bar, Quote
from app.utils.time import UTC

ET = ZoneInfo("America/New_York")
SYNTHETIC_START_ET = datetime(2026, 6, 1, 9, 30, tzinfo=ET)
TEST_FMP_SENTINEL = "test-only-fmp-key"
DEFAULT_POSTGRES_URL = "postgresql+psycopg://amd:amd@localhost:15432/adaptive_market_decoder"


def _synthetic_bars(symbol: str, interval: str, count: int = 120) -> list[Bar]:
    minutes_per_bar = {"1min": 1, "5min": 5, "15min": 15}.get(interval, 1)
    seed = (sum(ord(char) for char in symbol) % 11) * 0.15
    bars = []
    for index in range(count):
        timestamp_et = SYNTHETIC_START_ET + timedelta(minutes=index * minutes_per_bar)
        close = 100.0 + seed + index * 0.12
        bars.append(
            Bar(
                symbol=symbol,
                interval=interval,
                timestamp_utc=timestamp_et.astimezone(UTC),
                timestamp_et=timestamp_et,
                open=close - 0.04,
                high=close + 0.22,
                low=close - 0.18,
                close=close,
                volume=2_000 + index * 35,
                source="mock-fmp",
            )
        )
    return bars


class FakeFMPProvider:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def capability_matrix(self) -> list[dict[str, object]]:
        return [{"name": "mock-fmp", "transport": "REST", "v1": True}]

    async def health_check(self) -> dict[str, object]:
        return {"status": "ok", "provider": "mock-fmp"}

    async def get_quote(self, symbol: str) -> Quote:
        return (await self.get_batch_quotes([symbol]))[0]

    async def get_batch_quotes(self, symbols: list[str]) -> list[Quote]:
        quotes = []
        quote_time = (SYNTHETIC_START_ET + timedelta(minutes=121)).astimezone(UTC)
        for index, symbol in enumerate(normalize_symbols(symbols)):
            quotes.append(
                Quote(
                    symbol=symbol,
                    price=114.75 + index,
                    timestamp_utc=quote_time,
                    volume=12_000 + index * 100,
                    source="mock-fmp",
                    raw={"symbol": symbol, "mock": True},
                )
            )
        return quotes

    async def get_historical_bars(
        self,
        symbol: str,
        interval: str,
        _start: datetime,
        _end: datetime,
    ) -> list[Bar]:
        return _synthetic_bars(normalize_symbol(symbol), interval)


def _reset_scanner(routes_module) -> None:
    scanner = routes_module.scanner_state
    scanner.running = False
    scanner.started_at = None
    scanner.last_error = None
    scanner.latest_signals = []
    scanner.context_bars = {}
    scanner.minimum_context_bars = 5
    scanner.scanner_run_id = None
    scanner._task = None
    scanner._queue = None


def _assert_path_clean(path: str | Path) -> None:
    payload = Path(path).read_bytes()
    assert TEST_FMP_SENTINEL.encode() not in payload


def _sheet_names(path: str | Path) -> set[str]:
    workbook = load_workbook(path, read_only=True)
    try:
        return set(workbook.sheetnames)
    finally:
        workbook.close()


def _postgres_available(database_url: str) -> bool:
    try:
        engine = create_engine(_sync_postgres_url(database_url), future=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _clear_postgres_tables(repo) -> None:
    tables = sorted(EXPECTED_TABLES - {"alembic_version"})
    quoted = ", ".join(f'"{table}"' for table in tables)
    with repo.store.engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


def _run_persisted_api_vertical_slice(
    tmp_path,
    monkeypatch,
    backend: str,
    database_url: str | None = None,
) -> None:
    db_path = tmp_path / "api-smoke.sqlite3"
    exports_dir = tmp_path / "exports"
    model_dir = tmp_path / "models"
    monkeypatch.setenv("AMD_SQLITE_PATH", str(db_path))
    if backend == "postgresql":
        monkeypatch.setenv("DATABASE_URL", database_url or DEFAULT_POSTGRES_URL)
        monkeypatch.delenv("AMD_ALLOW_SQLITE_FALLBACK", raising=False)
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("AMD_ALLOW_SQLITE_FALLBACK", raising=False)
    monkeypatch.setenv("FMP_API_KEY", TEST_FMP_SENTINEL)
    monkeypatch.setenv("PUBLIC_DEFAULT_SYMBOLS", "AAPL,SPY,QQQ,NVDA")

    get_settings.cache_clear()
    reset_repository_registry()
    settings = get_settings()
    monkeypatch.setattr(settings, "exports_dir", exports_dir)
    monkeypatch.setattr(settings, "model_artifacts_dir", model_dir)
    monkeypatch.setattr(settings, "rest_poll_seconds", 60.0)

    from app.api import routes as routes_module
    from app.jobs import scanner as scanner_module
    from app.main import app

    monkeypatch.setattr(routes_module, "FMPMarketDataProvider", FakeFMPProvider)
    monkeypatch.setattr(scanner_module, "FMPMarketDataProvider", FakeFMPProvider)
    _reset_scanner(routes_module)
    repo = get_repository_registry()
    if backend == "postgresql":
        assert repo.info()["persistence_backend"] == "postgresql"
        _clear_postgres_tables(repo)
        assert not db_path.exists()
    else:
        assert repo.info()["persistence_backend"] == "sqlite"

    start = SYNTHETIC_START_ET.astimezone(UTC)
    end = (SYNTHETIC_START_ET + timedelta(minutes=119)).astimezone(UTC)

    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["persistence"]["persistence_backend"] == backend
        assert health["persistence"]["database_reachable"] is True
        if backend == "sqlite":
            assert health["persistence"]["path"] == str(db_path)
        else:
            assert health["persistence"]["runtime_mode"] == "postgresql"

        config = client.get("/config").json()
        assert config["fmp_api_key_configured"] is True
        assert config["persistence"]["database_url_kind"] == ("postgresql" if backend == "postgresql" else "unset")

        ingest = client.post(
            "/data/ingest",
            json={
                "symbols": ["APPL", "SPY", "QQQ", "NVDA"],
                "intervals": ["1min"],
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        ).json()
        assert ingest["status"] == "ok"
        assert "AAPL" in ingest["symbols"]
        assert "APPL" not in ingest["symbols"]
        assert ingest["bars_written"] == 480
        assert {
            "features",
            "candidates",
            "labels",
            "replay",
        } <= {row["artifact_type"] for row in ingest["dirty_ranges"]}

        bars = client.get("/data/bars").json()
        assert len(bars) == 480

        latest_quotes = client.get("/data/quotes/latest").json()
        assert {quote["symbol"] for quote in latest_quotes} == {"AAPL", "SPY", "QQQ", "NVDA"}

        features = client.post("/features/build").json()
        assert features["features"] == 480
        assert features["features_written"] == 480
        assert features["build_windows"]

        labels = client.post("/labels/build").json()
        assert labels["labels"] > 0
        assert labels["candidates"] > 0
        assert labels["build_windows"]

        train = client.post(
            "/models/train",
            json={
                "symbols": ["AAPL", "SPY", "QQQ", "NVDA"],
                "training_start": start.isoformat(),
                "training_end": end.isoformat(),
                "min_samples": 1,
                "activate_if_passes": False,
            },
        ).json()
        model_version = train["model_version"]

        activation_without_report = client.post(
            "/models/activate",
            params={"model_version": model_version},
        ).json()
        assert activation_without_report["activated"] is False
        assert activation_without_report["reason"] == "accepted_validation_report_required"

        validation = client.post("/models/validate", params={"model_version": model_version}).json()
        assert validation["model_version"] == model_version

        repo = get_repository_registry()
        repo.validation_reports.save(
            {
                "model_version": model_version,
                "summary": {"total_trades": 0},
                "windows": [],
                "activation_decision": "rejected",
                "rejection_reasons": ["controlled_rejection"],
                "created_at": (datetime.now(UTC) - timedelta(seconds=2)).isoformat(),
            },
            model_version=model_version,
        )
        activation_with_rejected_report = client.post(
            "/models/activate",
            params={"model_version": model_version},
        ).json()
        assert activation_with_rejected_report["activated"] is False
        assert activation_with_rejected_report["reason"] == "validation_gate_failed"

        repo.validation_reports.save(
            {
                "model_version": model_version,
                "summary": {"total_trades": 40, "average_r": 0.25, "profit_factor": 1.6},
                "windows": [],
                "activation_decision": "accepted",
                "rejection_reasons": [],
                "created_at": datetime.now(UTC).isoformat(),
            },
            model_version=model_version,
        )
        activated = client.post("/models/activate", params={"model_version": model_version}).json()
        assert activated["activated"] is True
        assert activated["active_model"]["model_version"] == model_version

        replacement_version = f"{model_version}-replacement"
        replacement_model = dict(train)
        replacement_model["model_version"] = replacement_version
        replacement_model["active"] = False
        repo.model_runs.save(replacement_model, artifact_path=str(model_dir / f"{replacement_version}.json"))
        repo.validation_reports.save(
            {
                "model_version": replacement_version,
                "summary": {"total_trades": 40, "average_r": 0.25, "profit_factor": 1.6},
                "windows": [],
                "activation_decision": "accepted",
                "rejection_reasons": [],
                "created_at": (datetime.now(UTC) + timedelta(seconds=1)).isoformat(),
            },
            model_version=replacement_version,
        )
        replacement = client.post("/models/activate", params={"model_version": replacement_version}).json()
        assert replacement["activated"] is True
        assert replacement["active_model"]["model_version"] == replacement_version

        models = client.get("/models").json()
        assert {model["model_version"] for model in models} >= {model_version, replacement_version}
        model_detail = client.get(f"/models/{replacement_version}").json()
        assert model_detail["model_version"] == replacement_version

        active_model_runs = [model for model in repo.model_runs.list_all() if model.get("active")]
        assert len(active_model_runs) == 1

        backtest = client.post(
            "/backtest/run",
            json={
                "symbols": ["AAPL", "SPY", "QQQ", "NVDA"],
                "start": start.isoformat(),
                "end": end.isoformat(),
                "model_version": model_version,
            },
        ).json()
        assert backtest["report_id"]
        assert backtest["simulation_type"] == "label_derived"
        assert backtest["summary"]["total_trades"] > 0
        backtest_runs = client.get("/backtest/runs").json()
        assert backtest["report_id"] in {run["report_id"] for run in backtest_runs}
        backtest_run = client.get(f"/backtest/runs/{backtest['report_id']}").json()
        assert backtest_run["report_id"] == backtest["report_id"]
        assert backtest_run["simulation_type"] == "label_derived"

        replay = client.post(
            "/backtest/replay",
            json={
                "symbols": ["AAPL", "SPY", "QQQ", "NVDA"],
                "intervals": ["1min"],
                "start": start.isoformat(),
                "end": end.isoformat(),
                "max_hold_minutes": 30,
                "minimum_reward_risk": 0.5,
                "feature_warmup_bars": 1,
            },
        ).json()
        replay_run_id = replay["replay_run_id"]
        assert replay["simulation_type"] == "candidate_market_replay"
        assert replay["config_hash"]
        assert replay["input_fingerprint"]
        assert replay["candidate_fingerprint"]
        assert replay["summary_metrics"]["total_candidates"] > 0
        assert replay["trades_written"] == replay["summary_metrics"]["total_candidates"]
        pipeline_status = client.get("/pipeline/status").json()
        assert "dirty_window_count" in pipeline_status
        replay_detail = client.get(f"/backtest/replay/{replay_run_id}").json()
        assert replay_detail["replay_run_id"] == replay_run_id
        replay_trades = client.get(
            f"/backtest/replay/{replay_run_id}/trades",
            params={"limit": 100_000},
        ).json()
        assert replay_trades["trades"]
        assert {trade["status"] for trade in replay_trades["trades"]} <= {"TAKEN", "SKIPPED"}
        replay_trade_count = len(replay_trades["trades"])
        taken_replay_trades = client.get(
            f"/backtest/replay/{replay_run_id}/trades",
            params={"status": "TAKEN"},
        ).json()
        assert all(trade["status"] == "TAKEN" for trade in taken_replay_trades["trades"])
        combined_runs = client.get("/backtest/runs").json()
        assert replay_run_id in {
            run.get("replay_run_id") or run.get("report_id")
            for run in combined_runs
        }
        replay_run = client.get(f"/backtest/runs/{replay_run_id}").json()
        assert replay_run["replay_run_id"] == replay_run_id
        missing_replay_selection = client.post(
            "/models/validate",
            params={"model_version": model_version, "validation_mode": "candidate_market_replay"},
        ).json()
        assert "replay_run_selection_required" in missing_replay_selection["rejection_reasons"]
        replay_validation = client.post(
            "/models/validate",
            params={
                "model_version": model_version,
                "validation_mode": "candidate_market_replay",
                "replay_run_id": replay_run_id,
            },
        ).json()
        assert replay_validation["replay_run_id"] == replay_run_id
        assert replay_validation["replay_run_selection"]["reason"] == "explicit_replay_run_id"
        sensitivity = client.post(
            f"/backtest/replay/{replay_run_id}/sensitivity",
            json={
                "slippage_bps_grid": [0, 1],
                "spread_bps_grid": [0, 2],
                "intrabar_path_policies": ["conservative"],
                "minimum_total_trades": 1,
                "minimum_robustness_score": 0,
            },
        ).json()
        sensitivity_run_id = sensitivity["sensitivity_run_id"]
        assert sensitivity["status"] == "ok"
        assert sensitivity["scenario_count"] == 4
        sensitivity_detail = client.get(f"/backtest/replay/sensitivity/{sensitivity_run_id}").json()
        assert sensitivity_detail["sensitivity_run_id"] == sensitivity_run_id
        sensitivity_scenarios = client.get(
            f"/backtest/replay/sensitivity/{sensitivity_run_id}/scenarios"
        ).json()
        assert len(sensitivity_scenarios["scenarios"]) == 4
        sensitivity_list = client.get(f"/backtest/replay/{replay_run_id}/sensitivity").json()
        assert sensitivity_run_id in {
            run["sensitivity_run_id"] for run in sensitivity_list["sensitivity_runs"]
        }
        comparison = client.post(
            "/backtest/compare-label-vs-replay",
            json={"replay_run_id": replay_run_id},
        ).json()
        assert comparison["status"] == "ok"
        comparison_detail = client.get(f"/backtest/comparisons/{comparison['comparison_id']}").json()
        assert comparison_detail["comparison_id"] == comparison["comparison_id"]

        scanner_start = client.post(
            "/scanner/start",
            json={"symbols": ["AAPL", "SPY"], "confidence_threshold": 0.0},
        ).json()
        assert scanner_start["scanner_run_id"]
        live_signals = []
        for _ in range(40):
            live_signals = client.get("/signals/live").json()
            if live_signals:
                break
            time.sleep(0.05)
        scanner_status = client.get("/scanner/status").json()
        scanner_stop = client.post("/scanner/stop").json()
        assert scanner_stop["running"] is False
        assert scanner_status["latest_persisted_run"]["scanner_run_id"] == scanner_start["scanner_run_id"]
        assert live_signals
        signal_history = client.get("/signals/history").json()
        assert len(signal_history) == len(live_signals)

        csv_export = client.post("/exports/signals.csv", json={"kind": "signals"}).json()
        xlsx_export = client.post("/exports/signals.xlsx", json={"kind": "signals"}).json()
        backtest_export = client.post("/exports/backtest.xlsx", json={"kind": "backtest"}).json()
        replay_summary_export = client.post(
            "/exports/replay-summary.xlsx",
            json={"kind": "replay-summary", "run_id": replay_run_id},
        ).json()
        replay_trades_csv = client.post(
            "/exports/replay-trades.csv",
            json={"kind": "replay-trades", "run_id": replay_run_id},
        ).json()
        replay_trades_xlsx = client.post(
            "/exports/replay-trades.xlsx",
            json={"kind": "replay-trades", "run_id": replay_run_id},
        ).json()
        sensitivity_summary_export = client.post(
            "/exports/sensitivity-summary.xlsx",
            json={"kind": "sensitivity-summary", "run_id": sensitivity_run_id},
        ).json()
        sensitivity_scenarios_csv = client.post(
            "/exports/sensitivity-scenarios.csv",
            json={"kind": "sensitivity-scenarios", "run_id": sensitivity_run_id},
        ).json()
        sensitivity_scenarios_xlsx = client.post(
            "/exports/sensitivity-scenarios.xlsx",
            json={"kind": "sensitivity-scenarios", "run_id": sensitivity_run_id},
        ).json()
        sensitivity_metrics_export = client.post(
            "/exports/sensitivity-metrics.json",
            json={"kind": "sensitivity-metrics", "run_id": sensitivity_run_id},
        ).json()
        review = client.post("/review/daily").json()
        persisted_review = client.get(f"/review/daily/{review['date']}").json()
        daily_export = client.post("/exports/daily-review.xlsx", json={"kind": "daily-review"}).json()
        export_status = client.get(f"/exports/{csv_export['export']['export_id']}").json()

        assert csv_export["rows"] == len(live_signals)
        assert xlsx_export["rows"] == len(live_signals)
        assert backtest_export["status"] == "ok"
        assert backtest_export["note"] == "V1 workbook scaffold"
        assert replay_summary_export["status"] == "ok"
        assert len(replay_summary_export["paths"]) == 2
        assert replay_trades_csv["rows"] == replay_trade_count
        assert replay_trades_xlsx["rows"] == replay_trade_count
        assert sensitivity_summary_export["status"] == "ok"
        assert sensitivity_summary_export["export"]["file_sha256"]
        assert sensitivity_scenarios_csv["rows"] == 4
        assert sensitivity_scenarios_xlsx["rows"] == 4
        assert sensitivity_metrics_export["rows"] == 4
        assert {"Live Signals", "Model Info"} <= _sheet_names(xlsx_export["path"])
        assert {"Live Signals", "Model Info"} <= _sheet_names(backtest_export["path"])
        assert {
            "Summary",
            "Trades",
            "Skipped Candidates",
            "Per Symbol",
            "Per Setup",
            "Config",
            "Warnings",
        } <= _sheet_names(replay_summary_export["paths"][0])
        assert {"Trades"} <= _sheet_names(replay_trades_xlsx["path"])
        assert {
            "Summary",
            "Scenario Metrics",
            "Worst Case",
            "Median Case",
            "Best Case",
            "Fragility Flags",
            "Gate Results",
            "Config",
            "Warnings",
        } <= _sheet_names(sensitivity_summary_export["path"])
        assert {"Scenario Metrics"} <= _sheet_names(sensitivity_scenarios_xlsx["path"])
        assert review["signals_fired"] + review["signals_skipped"] == len(live_signals)
        assert persisted_review["status"] == "local-file"
        assert len(daily_export["paths"]) == 3
        assert {"Summary", "Signals Fired", "Recommendations"} <= _sheet_names(daily_export["paths"][2])
        assert export_status["status"] == "local-file"

    reset_repository_registry()
    reopened = get_repository_registry()
    if backend == "sqlite":
        assert reopened.info()["path"] == str(db_path)
    else:
        assert reopened.info()["persistence_backend"] == "postgresql"
        assert not db_path.exists()
    assert len(reopened.bars.list_all()) == 480
    assert len(reopened.features.list_all()) == 480
    assert len(reopened.labels.list_all()) > 0
    assert reopened.replays.get(replay_run_id)["simulation_type"] == "candidate_market_replay"
    assert len(reopened.replays.list_trades(replay_run_id, limit=100_000)) == replay_trade_count
    assert reopened.replay_sensitivity.get(sensitivity_run_id)["replay_run_id"] == replay_run_id
    assert reopened.backtest_comparisons.get(comparison["comparison_id"])["replay_run_id"] == replay_run_id
    assert reopened.active_models.get_active()["model_version"] == replacement_version
    assert reopened.scanner_runs.latest()["scanner_run_id"] == scanner_start["scanner_run_id"]
    assert len(reopened.live_signals.list_latest()) == len(live_signals)
    assert len(reopened.exports.list_all()) >= 14
    assert reopened.daily_reviews.get(datetime.now(UTC).date()) is not None
    assert TEST_FMP_SENTINEL not in str(reopened.provider_requests.list_all())

    clean_paths = [
        csv_export["path"],
        xlsx_export["path"],
        backtest_export["path"],
        replay_trades_csv["path"],
        replay_trades_xlsx["path"],
        sensitivity_summary_export["path"],
        sensitivity_scenarios_csv["path"],
        sensitivity_scenarios_xlsx["path"],
        sensitivity_metrics_export["path"],
        *replay_summary_export["paths"],
        *daily_export["paths"],
        model_dir / "active_model.json",
    ]
    if backend == "sqlite":
        clean_paths.append(db_path)
    for path in clean_paths:
        _assert_path_clean(path)


def test_persisted_api_vertical_slice_sqlite(tmp_path, monkeypatch) -> None:
    _run_persisted_api_vertical_slice(tmp_path, monkeypatch, backend="sqlite")


def test_persisted_api_vertical_slice_postgres(tmp_path, monkeypatch) -> None:
    database_url = DEFAULT_POSTGRES_URL
    if not _postgres_available(database_url):
        pytest.skip("local Postgres/TimescaleDB is not available for persisted API smoke")
    _run_persisted_api_vertical_slice(
        tmp_path,
        monkeypatch,
        backend="postgresql",
        database_url=database_url,
    )
