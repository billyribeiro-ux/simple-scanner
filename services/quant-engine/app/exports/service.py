from __future__ import annotations

import csv
import json
from datetime import date, datetime
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from app.utils.time import UTC
from pathlib import Path
from typing import Iterable

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
