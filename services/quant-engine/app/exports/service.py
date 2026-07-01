from __future__ import annotations

import csv
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook

from app.config import get_settings
from app.schemas.market import Signal


SIGNAL_COLUMNS = [
    "timestamp",
    "ticker",
    "side",
    "entry_price",
    "stop_price",
    "target_1",
    "target_2",
    "target_3",
    "risk_per_share",
    "reward_risk_to_t1",
    "reward_risk_to_t2",
    "reward_risk_to_t3",
    "expected_r",
    "confidence_score",
    "signal_grade",
    "setup_type",
    "market_regime",
    "ticker_regime",
    "reasons",
    "warnings",
    "historical_sample_size",
    "historical_win_rate",
    "historical_average_r",
    "model_version",
    "training_start",
    "training_end",
    "data_source",
    "status",
    "exit_price",
    "exit_reason",
    "realized_r",
]


class ExportService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.exports_dir.mkdir(parents=True, exist_ok=True)

    def export_signals_csv(self, signals: Iterable[Signal], run_date: date | None = None) -> Path:
        run_date = run_date or datetime.now(UTC).date()
        path = self.settings.exports_dir / f"live_signals_{run_date.isoformat()}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=SIGNAL_COLUMNS)
            writer.writeheader()
            for signal in signals:
                writer.writerow(self._signal_row(signal))
        return path

    def export_signals_xlsx(self, signals: Iterable[Signal], run_date: date | None = None) -> Path:
        run_date = run_date or datetime.now(UTC).date()
        path = self.settings.exports_dir / f"live_signals_{run_date.isoformat()}.xlsx"
        rows = [self._signal_row(signal) for signal in signals]
        workbook = Workbook()
        live = workbook.active
        live.title = "Live Signals"
        self._write_sheet(live, SIGNAL_COLUMNS, rows)
        for sheet_name in [
            "Closed Signals",
            "Performance Summary",
            "Ticker Breakdown",
            "Setup Breakdown",
            "Regime Breakdown",
            "Model Info",
        ]:
            sheet = workbook.create_sheet(sheet_name)
            sheet.append(["status", "message"])
            sheet.append(["scaffold", "Data will populate as signals close and backtests run."])
        workbook.save(path)
        return path

    def export_daily_review(self, payload: dict[str, object], run_date: date | None = None) -> tuple[Path, Path, Path]:
        run_date = run_date or datetime.now(UTC).date()
        json_path = self.settings.exports_dir / f"daily_review_{run_date.isoformat()}.json"
        csv_path = self.settings.exports_dir / f"daily_review_{run_date.isoformat()}.csv"
        xlsx_path = self.settings.exports_dir / f"daily_review_{run_date.isoformat()}.xlsx"
        json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["section", "value"])
            for key, value in payload.items():
                writer.writerow([key, json.dumps(value, default=str)])
        workbook = Workbook()
        for index, sheet_name in enumerate(
            [
                "Summary",
                "Signals Fired",
                "Missed Moves",
                "False Positives",
                "False Negatives",
                "Ticker Notes",
                "Regime Notes",
                "Recommendations",
            ]
        ):
            sheet = workbook.active if index == 0 else workbook.create_sheet(sheet_name)
            sheet.title = sheet_name
            sheet.append(["section", "value"])
            sheet.append([sheet_name, json.dumps(payload.get(sheet_name.lower().replace(" ", "_"), []), default=str)])
        workbook.save(xlsx_path)
        return json_path, csv_path, xlsx_path

    def _signal_row(self, signal: Signal) -> dict[str, object]:
        payload = signal.model_dump(mode="json")
        payload["side"] = signal.side.value
        payload["status"] = signal.status.value
        payload["reasons"] = " | ".join(signal.reasons)
        payload["warnings"] = " | ".join(signal.warnings)
        return {column: payload.get(column) for column in SIGNAL_COLUMNS}

    def _write_sheet(self, sheet, columns: list[str], rows: list[dict[str, object]]) -> None:
        sheet.append(columns)
        for row in rows:
            sheet.append([row.get(column) for column in columns])
