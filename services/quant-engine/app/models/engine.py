from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

from app.config import get_settings
from app.schemas.market import Label, Outcome


MODEL_SCHEMA_VERSION = "model.v1"


class StatisticalEvidenceEngine:
    def summarize(self, labels: list[Label]) -> dict[str, dict[str, float | int]]:
        buckets: dict[str, list[Label]] = defaultdict(list)
        for label in labels:
            key = f"{label.symbol}|{label.setup_type}|{label.market_regime}"
            buckets[key].append(label)
        summaries: dict[str, dict[str, float | int]] = {}
        for key, bucket in buckets.items():
            returns = [label.realized_r for label in bucket]
            wins = [label for label in bucket if label.outcome == Outcome.WIN]
            losses = [abs(label.realized_r) for label in bucket if label.realized_r < 0]
            gains = [label.realized_r for label in bucket if label.realized_r > 0]
            summaries[key] = {
                "sample_size": len(bucket),
                "win_rate": len(wins) / len(bucket) if bucket else 0.0,
                "average_r": mean(returns) if returns else 0.0,
                "median_r": median(returns) if returns else 0.0,
                "profit_factor": sum(gains) / sum(losses) if sum(losses) else float(sum(gains) > 0),
                "average_mfe": mean([label.max_favorable_excursion for label in bucket]),
                "average_mae": mean([label.max_adverse_excursion for label in bucket]),
            }
        return summaries


class ModelEngine:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.evidence = StatisticalEvidenceEngine()

    def train(
        self,
        labels: list[Label],
        features: list[dict[str, object]],
        training_start: datetime,
        training_end: datetime,
        symbols: list[str],
    ) -> dict[str, Any]:
        evidence = self.evidence.summarize(labels)
        trades = len(labels)
        wins = len([label for label in labels if label.outcome == Outcome.WIN])
        average_r = mean([label.realized_r for label in labels]) if labels else 0.0
        brier_score = self._baseline_brier(labels)
        passes = trades >= 30 and average_r > 0
        model_version = f"amd-{training_end.strftime('%Y%m%d')}-{datetime.now(UTC).strftime('%H%M%S')}"
        model = {
            "model_version": model_version,
            "schema_version": MODEL_SCHEMA_VERSION,
            "training_start": training_start.isoformat(),
            "training_end": training_end.isoformat(),
            "symbols": symbols,
            "feature_set_version": "features.v1",
            "label_config": {"target_r": self.settings.target_r, "max_hold_minutes": self.settings.max_hold_minutes},
            "validation_metrics": {
                "trades": trades,
                "win_rate": wins / trades if trades else 0.0,
                "average_r": average_r,
                "brier_score": brier_score,
                "passes_activation_gate": passes,
            },
            "statistical_evidence": evidence,
            "created_at": datetime.now(UTC).isoformat(),
            "active": False,
            "notes": "Baseline V1 rules/statistical model; ML classifier hook is ready for scikit-learn upgrade.",
        }
        self._write_model(model_version, model)
        return model

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        metrics = dict(model.get("validation_metrics") or {})
        metrics["passes_activation_gate"] = bool(metrics.get("trades", 0) >= 30 and metrics.get("average_r", 0) > 0)
        return metrics

    def activate(self, model_version: str) -> dict[str, Any]:
        model = self.load(model_version)
        metrics = self.validate(model)
        if not metrics["passes_activation_gate"]:
            return {"activated": False, "reason": "validation gate failed", "metrics": metrics}
        model["active"] = True
        self._write_model(model_version, model)
        active_path = self.settings.model_artifacts_dir / "active_model.json"
        active_path.parent.mkdir(parents=True, exist_ok=True)
        active_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
        return {"activated": True, "model_version": model_version, "metrics": metrics}

    def load(self, model_version: str | None = None) -> dict[str, Any]:
        if model_version is None:
            path = self.settings.model_artifacts_dir / "active_model.json"
        else:
            path = self.settings.model_artifacts_dir / f"{model_version}.json"
        if not path.exists():
            return {
                "model_version": "untrained-baseline",
                "active": False,
                "statistical_evidence": {},
                "validation_metrics": {"trades": 0, "win_rate": 0.0, "average_r": 0.0},
            }
        return json.loads(path.read_text(encoding="utf-8"))

    def list_models(self) -> list[dict[str, Any]]:
        model_dir = self.settings.model_artifacts_dir
        if not model_dir.exists():
            return []
        models: list[dict[str, Any]] = []
        for path in sorted(model_dir.glob("amd-*.json")):
            models.append(json.loads(path.read_text(encoding="utf-8")))
        return models

    def _write_model(self, model_version: str, model: dict[str, Any]) -> None:
        model_dir = self.settings.model_artifacts_dir
        model_dir.mkdir(parents=True, exist_ok=True)
        (model_dir / f"{model_version}.json").write_text(json.dumps(model, indent=2), encoding="utf-8")

    def _baseline_brier(self, labels: list[Label]) -> float:
        if not labels:
            return 0.0
        win_rate = len([label for label in labels if label.outcome == Outcome.WIN]) / len(labels)
        return mean([(win_rate - float(label.outcome == Outcome.WIN)) ** 2 for label in labels])
