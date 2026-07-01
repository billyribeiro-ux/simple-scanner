from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from datetime import datetime
from statistics import mean, median
from typing import Any

from app.backtesting.engine import BacktestEngine
from app.config import get_settings
from app.schemas.market import Label, Outcome
from app.utils.time import UTC
from app.validation.engine import ActivationCriteria, ValidationEngine


MODEL_SCHEMA_VERSION = "model.v2.baseline_evidence"


class StatisticalEvidenceEngine:
    def summarize(self, labels: list[Label]) -> dict[str, dict[str, float | int]]:
        buckets: dict[str, list[Label]] = defaultdict(list)
        for label in labels:
            time_bucket = str(getattr(label, "time_bucket", "unknown"))
            side = label.side.value
            keys = [
                f"{label.symbol}|{label.setup_type}|{label.market_regime}|{time_bucket}|{side}",
                f"{label.symbol}|{label.setup_type}|{label.market_regime}",
                f"{label.symbol}|{label.setup_type}|{side}",
                f"{label.setup_type}|{label.market_regime}|{side}",
            ]
            for key in keys:
                buckets[key].append(label)
        return {key: self._summarize_bucket(bucket) for key, bucket in sorted(buckets.items())}

    def _summarize_bucket(self, bucket: list[Label]) -> dict[str, float | int]:
        returns = [label.realized_r for label in bucket]
        wins = [label for label in bucket if label.outcome == Outcome.WIN or label.realized_r > 0]
        losses = [abs(label.realized_r) for label in bucket if label.realized_r < 0]
        gains = [label.realized_r for label in bucket if label.realized_r > 0]
        equity = []
        running = 0.0
        for value in returns:
            running += value
            equity.append(running)
        return {
            "sample_size": len(bucket),
            "win_rate": len(wins) / len(bucket) if bucket else 0.0,
            "average_r": mean(returns) if returns else 0.0,
            "median_r": median(returns) if returns else 0.0,
            "profit_factor": sum(gains) / sum(losses) if sum(losses) else (float("inf") if gains else 0.0),
            "max_drawdown": self._max_drawdown(equity),
            "target_1_hit_rate": len([label for label in bucket if label.hit_target_1]) / len(bucket) if bucket else 0.0,
            "target_2_hit_rate": len([label for label in bucket if label.hit_target_2]) / len(bucket) if bucket else 0.0,
            "target_3_hit_rate": len([label for label in bucket if label.hit_target_3]) / len(bucket) if bucket else 0.0,
            "stop_hit_rate": len([label for label in bucket if label.hit_stop]) / len(bucket) if bucket else 0.0,
            "average_mfe": mean([label.max_favorable_excursion for label in bucket]) if bucket else 0.0,
            "average_mae": mean([label.max_adverse_excursion for label in bucket]) if bucket else 0.0,
        }

    def _max_drawdown(self, equity: list[float]) -> float:
        peak = 0.0
        max_dd = 0.0
        for value in equity:
            peak = max(peak, value)
            max_dd = min(max_dd, value - peak)
        return max_dd


class BaselineScoringModel:
    def score(self, candidate_features: dict[str, Any], evidence: dict[str, float | int]) -> dict[str, Any]:
        sample_size = int(evidence.get("sample_size") or 0)
        average_r = float(evidence.get("average_r") or 0.0)
        win_rate = float(evidence.get("win_rate") or 0.0)
        sample_confidence = min(sample_size / 100, 1.0)
        regime_bonus = 0.08 if str(candidate_features.get("market_regime")) in {"trend_long", "trend_short", "opening_drive"} else 0.0
        rs_bonus = max(float(candidate_features.get("leadership_score") or 0.0), 0.0) * 2
        volume_bonus = min(float(candidate_features.get("relative_volume") or 0.0), 3.0) * 0.03
        raw_score = 0.35 + average_r * 0.12 + max(win_rate - 0.45, 0.0) * 0.4 + sample_confidence * 0.12
        score = max(0.0, min(raw_score + regime_bonus + rs_bonus + volume_bonus, 0.99))
        return {
            "confidence_score": score,
            "expected_r": average_r * score,
            "sample_size": sample_size,
            "suppressed": sample_size < 20 or average_r <= 0,
        }


class ModelEngine:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.evidence = StatisticalEvidenceEngine()
        self.backtest = BacktestEngine()
        self.validation = ValidationEngine(ActivationCriteria(minimum_trades=30))

    def train(
        self,
        labels: list[Label],
        features: list[dict[str, object]],
        training_start: datetime,
        training_end: datetime,
        symbols: list[str],
    ) -> dict[str, Any]:
        evidence = self.evidence.summarize(labels)
        metrics = self.backtest.summarize_labels(labels)
        decision = self.validation.activation_decision(metrics, [], self.backtest.simulate_labels(labels))
        model_version = f"amd-{training_end.strftime('%Y%m%d')}-{datetime.now(UTC).strftime('%H%M%S')}"
        setup_types = sorted({label.setup_type for label in labels})
        feature_set_version = self._feature_set_version(features)
        model = {
            "model_version": model_version,
            "schema_version": MODEL_SCHEMA_VERSION,
            "model_type": "statistical_evidence_baseline",
            "feature_set_version": feature_set_version,
            "label_config_version": "labels.v2.no_leakage",
            "training_window": {
                "start": training_start.isoformat(),
                "end": training_end.isoformat(),
            },
            "validation_window": None,
            "test_window": None,
            "training_start": training_start.isoformat(),
            "training_end": training_end.isoformat(),
            "symbols": symbols,
            "setup_types": setup_types,
            "metrics": metrics,
            "validation_metrics": {
                "trades": metrics["total_trades"],
                "win_rate": metrics["win_rate"],
                "average_r": metrics["average_r"],
                "profit_factor": metrics["profit_factor"],
                "max_drawdown": metrics["max_drawdown"],
                "passes_activation_gate": decision["activation_decision"] == "accepted",
                "rejection_reasons": decision["rejection_reasons"],
            },
            "activation_decision": decision["activation_decision"],
            "rejection_reasons": decision["rejection_reasons"],
            "statistical_evidence": evidence,
            "created_at": datetime.now(UTC).isoformat(),
            "code_version": self._git_commit(),
            "active": False,
            "notes": "Baseline evidence model only; no self-learning or calibrated ML classifier claim.",
        }
        self._write_model(model_version, model)
        return model

    def validate(self, model: dict[str, Any]) -> dict[str, Any]:
        metrics = dict(model.get("metrics") or model.get("validation_metrics") or {})
        if "total_trades" not in metrics:
            metrics["total_trades"] = metrics.get("trades", 0)
        decision = self.validation.activation_decision(metrics, list(model.get("leakage_warnings") or []), [])
        metrics["passes_activation_gate"] = decision["activation_decision"] == "accepted"
        metrics["activation_decision"] = decision["activation_decision"]
        metrics["rejection_reasons"] = decision["rejection_reasons"]
        return metrics

    def activate(self, model_version: str) -> dict[str, Any]:
        model = self.load(model_version)
        metrics = self.validate(model)
        if not metrics["passes_activation_gate"]:
            return {"activated": False, "reason": "validation gate failed", "metrics": metrics}
        model["active"] = True
        model["activation_decision"] = "accepted"
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
                "model_type": "statistical_evidence_baseline",
                "statistical_evidence": {},
                "validation_metrics": {
                    "trades": 0,
                    "win_rate": 0.0,
                    "average_r": 0.0,
                    "profit_factor": 0.0,
                    "passes_activation_gate": False,
                },
                "activation_decision": "rejected",
                "rejection_reasons": ["no_active_model"],
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

    def _feature_set_version(self, features: list[dict[str, object]]) -> str:
        for feature in features:
            value = feature.get("feature_set_version")
            if value:
                return str(value)
        return "features.v2.no_leakage"

    def _git_commit(self) -> str | None:
        try:
            return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
        except Exception:
            return None
