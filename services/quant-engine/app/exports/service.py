from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from app.utils.time import UTC

try:
    from openpyxl import Workbook
except ModuleNotFoundError:  # pragma: no cover - compatibility path for no-venv smoke tests
    Workbook = None  # type: ignore[assignment]

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

REPLAY_TRADE_COLUMNS = [
    "trade_id",
    "replay_run_id",
    "candidate_id",
    "symbol",
    "interval",
    "side",
    "setup_type",
    "signal_timestamp_utc",
    "entry_timestamp_utc",
    "exit_timestamp_utc",
    "entry_price",
    "stop_price",
    "target_1",
    "target_2",
    "target_3",
    "exit_price",
    "exit_reason",
    "realized_r",
    "mfe_r",
    "mae_r",
    "bars_held",
    "minutes_held",
    "same_bar_ambiguous",
    "ambiguity_policy",
    "slippage_bps",
    "spread_bps",
    "commission",
    "market_regime",
    "time_bucket",
    "signal_score",
    "expected_r",
    "status",
    "skip_reason",
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
        if Workbook is None:
            self._write_minimal_xlsx(
                path,
                {
                    "Live Signals": [SIGNAL_COLUMNS, *[[row.get(column) for column in SIGNAL_COLUMNS] for row in rows]],
                    "Closed Signals": [["status", "message"], ["scaffold", "Data will populate as signals close and backtests run."]],
                    "Performance Summary": [["status", "message"], ["scaffold", "Data will populate as signals close and backtests run."]],
                    "Ticker Breakdown": [["status", "message"], ["scaffold", "Data will populate as signals close and backtests run."]],
                    "Setup Breakdown": [["status", "message"], ["scaffold", "Data will populate as signals close and backtests run."]],
                    "Regime Breakdown": [["status", "message"], ["scaffold", "Data will populate as signals close and backtests run."]],
                    "Model Info": [["status", "message"], ["scaffold", "Data will populate as signals close and backtests run."]],
                },
            )
            return path
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
        if Workbook is None:
            self._write_minimal_xlsx(
                xlsx_path,
                {
                    sheet_name: [
                        ["section", "value"],
                        [sheet_name, json.dumps(payload.get(sheet_name.lower().replace(" ", "_"), []), default=str)],
                    ]
                    for sheet_name in [
                        "Summary",
                        "Signals Fired",
                        "Missed Moves",
                        "False Positives",
                        "False Negatives",
                        "Ticker Notes",
                        "Regime Notes",
                        "Recommendations",
                    ]
                },
            )
            return json_path, csv_path, xlsx_path
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

    def export_replay_trades_csv(self, replay_run_id: str, trades: Iterable[dict[str, object]]) -> Path:
        path = self.settings.exports_dir / f"replay_trades_{replay_run_id}.csv"
        rows = [self._replay_trade_row(trade) for trade in trades]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=REPLAY_TRADE_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def export_replay_trades_xlsx(self, replay_run_id: str, trades: Iterable[dict[str, object]]) -> Path:
        path = self.settings.exports_dir / f"replay_trades_{replay_run_id}.xlsx"
        rows = [self._replay_trade_row(trade) for trade in trades]
        if Workbook is None:
            self._write_minimal_xlsx(
                path,
                {"Trades": [REPLAY_TRADE_COLUMNS, *[[row.get(column) for column in REPLAY_TRADE_COLUMNS] for row in rows]]},
            )
            return path
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Trades"
        self._write_sheet(sheet, REPLAY_TRADE_COLUMNS, rows)
        workbook.save(path)
        return path

    def export_replay_summary_xlsx(self, replay_run: dict[str, object], trades: Iterable[dict[str, object]]) -> Path:
        replay_run_id = str(replay_run["replay_run_id"])
        path = self.settings.exports_dir / f"replay_summary_{replay_run_id}.xlsx"
        trade_rows = [self._replay_trade_row(trade) for trade in trades]
        skipped_rows = [row for row in trade_rows if row.get("status") == "SKIPPED"]
        metrics = dict(replay_run.get("summary_metrics") or {})
        sheets = self._replay_workbook_sheets(replay_run, metrics, trade_rows, skipped_rows)
        if Workbook is None:
            self._write_minimal_xlsx(path, sheets)
            return path
        workbook = Workbook()
        for index, (sheet_name, rows) in enumerate(sheets.items()):
            sheet = workbook.active if index == 0 else workbook.create_sheet(sheet_name)
            sheet.title = sheet_name
            for row in rows:
                sheet.append(row)
        workbook.save(path)
        return path

    def export_replay_metrics_json(self, replay_run: dict[str, object]) -> Path:
        replay_run_id = str(replay_run["replay_run_id"])
        path = self.settings.exports_dir / f"replay_metrics_{replay_run_id}.json"
        payload = {
            "replay_run_id": replay_run_id,
            "simulation_type": replay_run.get("simulation_type"),
            "created_at": replay_run.get("created_at"),
            "filters": replay_run.get("config") or {},
            "summary_metrics": replay_run.get("summary_metrics") or {},
        }
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return path

    def _signal_row(self, signal: Signal) -> dict[str, object]:
        payload = signal.model_dump(mode="json")
        payload["side"] = signal.side.value
        payload["status"] = signal.status.value
        payload["reasons"] = " | ".join(signal.reasons)
        payload["warnings"] = " | ".join(signal.warnings)
        return {column: payload.get(column) for column in SIGNAL_COLUMNS}

    def _replay_trade_row(self, trade: dict[str, object]) -> dict[str, object]:
        return {column: trade.get(column) for column in REPLAY_TRADE_COLUMNS}

    def _replay_workbook_sheets(
        self,
        replay_run: dict[str, object],
        metrics: dict[str, object],
        trade_rows: list[dict[str, object]],
        skipped_rows: list[dict[str, object]],
    ) -> dict[str, list[list[object]]]:
        drawdown_payload = metrics.get("drawdown_series")
        drawdown_values = drawdown_payload if isinstance(drawdown_payload, list) else []
        config_payload = replay_run.get("config")
        config = config_payload if isinstance(config_payload, dict) else {}
        warnings_payload = replay_run.get("warnings")
        warnings = warnings_payload if isinstance(warnings_payload, list) else []
        return {
            "Summary": [["metric", "value"], *[[key, json.dumps(value, default=str)] for key, value in metrics.items() if not isinstance(value, (dict, list))]],
            "Trades": [REPLAY_TRADE_COLUMNS, *[[row.get(column) for column in REPLAY_TRADE_COLUMNS] for row in trade_rows if row.get("status") == "TAKEN"]],
            "Skipped Candidates": [REPLAY_TRADE_COLUMNS, *[[row.get(column) for column in REPLAY_TRADE_COLUMNS] for row in skipped_rows]],
            "Per Symbol": self._metric_sheet(metrics.get("per_symbol_metrics")),
            "Per Setup": self._metric_sheet(metrics.get("per_setup_metrics")),
            "Per Regime": self._metric_sheet(metrics.get("per_regime_metrics")),
            "Per Time Bucket": self._metric_sheet(metrics.get("per_time_bucket_metrics")),
            "Daily R": self._series_sheet(metrics.get("daily_r_series")),
            "Drawdown": [["index", "drawdown_r"], *[[index, value] for index, value in enumerate(drawdown_values, start=1)]],
            "Config": [["key", "value"], *[[key, json.dumps(value, default=str)] for key, value in config.items()]],
            "Warnings": [["warning"], *[[warning] for warning in warnings]],
        }

    def _metric_sheet(self, payload: object) -> list[list[object]]:
        rows: list[list[object]] = [["group", "metric", "value"]]
        if isinstance(payload, dict):
            for group, metrics in payload.items():
                if isinstance(metrics, dict):
                    rows.extend([[group, key, value] for key, value in metrics.items()])
        return rows

    def _series_sheet(self, payload: object) -> list[list[object]]:
        rows: list[list[object]] = [["key", "value"]]
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    value = item.get("r") if "r" in item else item.get("value")
                    rows.append([item.get("date") or item.get("key"), value])
                else:
                    rows.append([len(rows), item])
        return rows

    def _write_sheet(self, sheet, columns: list[str], rows: list[dict[str, object]]) -> None:
        sheet.append(columns)
        for row in rows:
            sheet.append([row.get(column) for column in columns])

    def _write_minimal_xlsx(self, path: Path, sheets: dict[str, list[list[object]]]) -> None:
        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            archive.writestr(
                "[Content_Types].xml",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
"""
                + "".join(
                    f'  <Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
                    for index in range(1, len(sheets) + 1)
                )
                + "</Types>",
            )
            archive.writestr(
                "_rels/.rels",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
            )
            archive.writestr(
                "xl/workbook.xml",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
"""
                + "".join(
                    f'    <sheet name="{escape(name[:31])}" sheetId="{index}" r:id="rId{index}"/>\n'
                    for index, name in enumerate(sheets, start=1)
                )
                + "  </sheets>\n</workbook>",
            )
            archive.writestr(
                "xl/_rels/workbook.xml.rels",
                """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
"""
                + "".join(
                    f'  <Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>\n'
                    for index in range(1, len(sheets) + 1)
                )
                + "</Relationships>",
            )
            for index, rows in enumerate(sheets.values(), start=1):
                archive.writestr(f"xl/worksheets/sheet{index}.xml", self._sheet_xml(rows))

    def _sheet_xml(self, rows: list[list[object]]) -> str:
        xml_rows = []
        for row_index, row in enumerate(rows, start=1):
            cells = []
            for column_index, value in enumerate(row, start=1):
                cell_ref = f"{self._column_name(column_index)}{row_index}"
                text = "" if value is None else str(value)
                cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(text)}</t></is></c>')
            xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(xml_rows)}</sheetData>'
            "</worksheet>"
        )

    def _column_name(self, index: int) -> str:
        name = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            name = chr(65 + remainder) + name
        return name
