from __future__ import annotations

import json
import os
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.data.symbols import normalize_symbols
from app.db.repositories import RepositoryRegistry
from app.services.research import ResearchCycleService, ResearchStatusService
from app.services.workflows import DataQualityService, ExportWorkflowService
from app.utils.time import UTC

SCHEDULER_JOB_TYPES = {
    "research_cycle_dry_run",
    "research_cycle_run",
    "data_quality_report",
    "export_research_cycle",
    "export_operations_status",
}
SCHEDULER_TERMINAL_STATUSES = {"COMPLETED", "FAILED", "CANCELLED", "BLOCKED"}
DEFAULT_MAX_JOBS = 3
MAX_JOBS_PER_RUN = 10


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _redact(payload: Any) -> Any:
    secret_values = {
        value
        for value in (os.environ.get("FMP_API_KEY"), os.environ.get("DATABASE_URL"))
        if value
    }
    if isinstance(payload, dict):
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            lowered = str(key).lower()
            if any(part in lowered for part in ("api_key", "secret", "password", "token", "database_url", "credential")):
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = _redact(value)
        return redacted
    if isinstance(payload, list):
        return [_redact(item) for item in payload]
    if isinstance(payload, str) and payload in secret_values:
        return "[REDACTED]"
    return payload


def _refresh_data_requested(payload: Any) -> bool:
    if isinstance(payload, dict):
        return any(
            (key == "refresh_data" and bool(value)) or _refresh_data_requested(value)
            for key, value in payload.items()
        )
    if isinstance(payload, list):
        return any(_refresh_data_requested(item) for item in payload)
    return False


class SchedulerService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos

    def create_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        job_type = str(payload.get("job_type") or "")
        if job_type not in SCHEDULER_JOB_TYPES:
            return {"status": "error", "reason": "unsupported_scheduler_job_type", "job_type": job_type}
        safe_payload = _redact(payload.get("payload") or {})
        job = self.repos.scheduler_jobs.save(
            {
                "job_type": job_type,
                "status": "QUEUED",
                "priority": int(payload.get("priority") or 100),
                "scheduled_for": payload.get("scheduled_for"),
                "payload": safe_payload,
                "result": {},
                "warnings": [],
                "research_cycle_id": safe_payload.get("research_cycle_id")
                if isinstance(safe_payload, dict)
                else None,
                "created_by": payload.get("created_by"),
            }
        )
        self.repos.scheduler_jobs.append_event(
            job["job_id"],
            "JOB_CREATED",
            "Scheduler job queued for explicit operator-run preparation.",
            {"job_type": job_type},
        )
        return job

    def list_jobs(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        return {
            "jobs": self.repos.scheduler_jobs.list(
                status=status,
                job_type=job_type,
                limit=limit,
                offset=offset,
            ),
            "limit": limit,
            "offset": offset,
        }

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self.repos.scheduler_jobs.get(job_id) or {"status": "not_found", "job_id": job_id}

    def events(self, job_id: str, *, limit: int = 500, offset: int = 0) -> dict[str, Any]:
        return {
            "job_id": job_id,
            "events": self.repos.scheduler_jobs.list_events(job_id, limit=limit, offset=offset),
            "limit": limit,
            "offset": offset,
        }

    def cancel(self, job_id: str) -> dict[str, Any]:
        job = self.repos.scheduler_jobs.get(job_id)
        if job is None:
            return {"status": "not_found", "job_id": job_id}
        if job.get("status") != "QUEUED":
            self._event(job_id, "JOB_CANCEL_BLOCKED", "Only queued scheduler jobs can be cancelled.", {"status": job.get("status")})
            return job | {"status": "blocked", "reason": "only_queued_jobs_can_be_cancelled"}
        cancelled = self.repos.scheduler_jobs.save(
            job
            | {
                "status": "CANCELLED",
                "completed_at": _now(),
                "updated_at": _now(),
                "result": {"cancelled": True},
                "warnings": list(job.get("warnings") or []),
            }
        )
        self._event(job_id, "JOB_CANCELLED", "Queued scheduler job cancelled by operator.")
        return cancelled

    def run_job(self, job_id: str) -> dict[str, Any]:
        job = self.repos.scheduler_jobs.get(job_id)
        if job is None:
            return {"status": "not_found", "job_id": job_id}
        if job.get("status") != "QUEUED":
            self._event(job_id, "JOB_RUN_BLOCKED", "Only queued scheduler jobs can be run.", {"status": job.get("status")})
            return job | {"status": "blocked", "reason": "only_queued_jobs_can_run"}
        running = self.repos.scheduler_jobs.save(job | {"status": "RUNNING", "started_at": _now(), "updated_at": _now()})
        self._event(job_id, "JOB_STARTED", "Scheduler job started synchronously by operator.")
        try:
            result = _redact(self._execute(running))
            final_status = self._final_status(result)
            warnings = sorted(
                set(
                    list(running.get("warnings") or [])
                    + [str(item) for item in (result.get("warnings") or []) if item]
                    + ["Scheduler job completed without model activation."]
                )
            )
            completed = self.repos.scheduler_jobs.save(
                running
                | {
                    "status": final_status,
                    "completed_at": _now(),
                    "updated_at": _now(),
                    "failed_reason": self._failed_reason(result, final_status),
                    "result": result,
                    "warnings": warnings,
                    "research_cycle_id": result.get("research_cycle_id") or running.get("research_cycle_id"),
                }
            )
            self._event(
                job_id,
                f"JOB_{final_status}",
                f"Scheduler job finished with status {final_status}.",
                {"job_type": running.get("job_type"), "research_cycle_id": completed.get("research_cycle_id")},
            )
            return completed
        except Exception as exc:  # pragma: no cover - defensive failure path
            failed = self.repos.scheduler_jobs.save(
                running
                | {
                    "status": "FAILED",
                    "completed_at": _now(),
                    "updated_at": _now(),
                    "failed_reason": str(exc),
                    "result": {"status": "error", "reason": str(exc)},
                    "warnings": list(running.get("warnings") or []),
                }
            )
            self._event(job_id, "JOB_FAILED", "Scheduler job failed and recorded a non-secret reason.", {"reason": str(exc)})
            return failed

    def run_pending(self, *, max_jobs: int = DEFAULT_MAX_JOBS) -> dict[str, Any]:
        bounded_max = max(1, min(int(max_jobs or DEFAULT_MAX_JOBS), MAX_JOBS_PER_RUN))
        pending = self.repos.scheduler_jobs.list_pending(max_jobs=bounded_max)
        results = [self.run_job(str(job["job_id"])) for job in pending]
        return {
            "status": "ok",
            "max_jobs": bounded_max,
            "jobs_run": len(results),
            "results": results,
            "scheduler_status": self.status(),
        }

    def status(self) -> dict[str, Any]:
        summary = self.repos.scheduler_jobs.status_summary()
        summary["latest_events"] = self.repos.scheduler_jobs.latest_events(limit=25)
        summary["persistence_backend"] = self.repos.info().get("persistence_backend")
        return summary

    def _execute(self, job: dict[str, Any]) -> dict[str, Any]:
        payload = dict(job.get("payload") or {})
        if _refresh_data_requested(payload) and not os.environ.get("FMP_API_KEY"):
            return {
                "status": "blocked",
                "reason": "fmp_api_key_required_for_refresh_data",
                "warnings": ["refresh_data requested but FMP_API_KEY is missing."],
            }
        job_type = str(job.get("job_type"))
        if job_type == "research_cycle_dry_run":
            return self._research_cycle_dry_run(payload)
        if job_type == "research_cycle_run":
            return self._research_cycle_run(payload)
        if job_type == "data_quality_report":
            return self._data_quality_report(payload)
        if job_type == "export_research_cycle":
            return self._export_research_cycle(payload)
        if job_type == "export_operations_status":
            return self._export_operations_status()
        return {"status": "error", "reason": "unsupported_scheduler_job_type", "job_type": job_type}

    def _research_cycle_dry_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        service = ResearchCycleService(self.repos)
        cycle_id = payload.get("research_cycle_id")
        created = None
        if not cycle_id:
            created = service.create(self._cycle_payload(payload))
            cycle_id = created.get("research_cycle_id")
        if not cycle_id:
            return {"status": "failed", "reason": "research_cycle_id_required"}
        dry_run = service.dry_run(str(cycle_id))
        return {
            **dry_run,
            "research_cycle_id": str(cycle_id),
            "created_cycle": created,
            "model_activation_unchanged": True,
        }

    def _research_cycle_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        service = ResearchCycleService(self.repos)
        cycle_id = payload.get("research_cycle_id")
        created = None
        if not cycle_id:
            created = service.create(self._cycle_payload(payload))
            cycle_id = created.get("research_cycle_id")
        if not cycle_id:
            return {"status": "failed", "reason": "research_cycle_id_required"}
        run_payload = dict(payload.get("run") or payload.get("run_payload") or {})
        if "allow_stale" in payload and "allow_stale" not in run_payload:
            run_payload["allow_stale"] = payload["allow_stale"]
        if "refresh_data" in payload and "refresh_data" not in run_payload:
            run_payload["refresh_data"] = payload["refresh_data"]
        result = service.run(str(cycle_id), run_payload)
        return {
            **result,
            "research_cycle_id": str(cycle_id),
            "created_cycle": created,
            "model_activation_unchanged": True,
        }

    def _data_quality_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        report = DataQualityService(self.repos).report(
            symbols=normalize_symbols(payload.get("symbols") or []) or None,
            intervals=[str(item) for item in payload.get("intervals") or []] or None,
            start=_parse_datetime(payload.get("start")),
            end=_parse_datetime(payload.get("end")),
            session=str(payload.get("session") or "rth"),
        )
        return {"status": "ok", "report": report, "warnings": report.get("warnings") or []}

    def _export_research_cycle(self, payload: dict[str, Any]) -> dict[str, Any]:
        cycle_id = payload.get("research_cycle_id")
        if not cycle_id:
            return {"status": "failed", "reason": "research_cycle_id_required"}
        kind = str(payload.get("kind") or "xlsx")
        return ExportWorkflowService(self.repos).export_research_cycle(str(cycle_id), kind=kind)

    def _export_operations_status(self) -> dict[str, Any]:
        status = {
            "research_status": ResearchStatusService(self.repos).status(),
            "scheduler_status": self.repos.scheduler_jobs.status_summary(),
            "exported_at": _now(),
            "no_broker_execution": True,
            "model_activation_unchanged": True,
        }
        path = self._write_json_export(status)
        record = self.repos.exports.record(
            "operator_status",
            "json",
            path,
            1,
            "operations",
            {"diagnostic_only": True, "model_activation_unchanged": True},
        )
        return {"status": "ok", "path": str(path), "rows": 1, "export": record}

    def _cycle_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        cycle = dict(payload.get("research_cycle") or payload.get("cycle") or payload)
        for key in ("job_type", "priority", "scheduled_for", "created_by", "run", "run_payload"):
            cycle.pop(key, None)
        cycle["run_now"] = False
        return cycle

    def _write_json_export(self, payload: dict[str, Any]) -> Path:
        settings = get_settings()
        settings.exports_dir.mkdir(parents=True, exist_ok=True)
        digest = sha256(json.dumps(_redact(payload), sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
        path = settings.exports_dir / f"operator_status_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{digest}.json"
        path.write_text(json.dumps(_redact(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
        return path

    def _final_status(self, result: dict[str, Any]) -> str:
        if result.get("status") in {"blocked", "BLOCKED"} or result.get("blocked") is True:
            return "BLOCKED"
        if result.get("status") in {"failed", "error", "not_found"} or result.get("reason"):
            return "FAILED"
        return "COMPLETED"

    def _failed_reason(self, result: dict[str, Any], final_status: str) -> str | None:
        if final_status not in {"FAILED", "BLOCKED"}:
            return None
        return str(result.get("reason") or result.get("failed_reason") or result.get("block_reason") or final_status.lower())

    def _event(
        self,
        job_id: str,
        event_type: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.repos.scheduler_jobs.append_event(job_id, event_type, message, _redact(metadata or {}))
