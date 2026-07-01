from datetime import datetime

from app.exports.service import ExportService
from app.schemas.market import Side, Signal
from app.utils.time import UTC


def test_signal_export_csv_and_xlsx(tmp_path, monkeypatch) -> None:
    service = ExportService()
    monkeypatch.setattr(service.settings, "exports_dir", tmp_path)
    signal = Signal(
        timestamp=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
        ticker="AAPL",
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
        expected_r=0.2,
        confidence_score=0.75,
        signal_grade="B+",
        setup_type="VWAP reclaim long",
        market_regime="trend_long",
        ticker_regime="single_stock_momentum",
        reasons=["test"],
        warnings=[],
        historical_sample_size=50,
        historical_win_rate=0.6,
        historical_average_r=0.3,
        model_version="test",
    )
    csv_path = service.export_signals_csv([signal])
    xlsx_path = service.export_signals_xlsx([signal])
    assert csv_path.exists()
    assert xlsx_path.exists()
