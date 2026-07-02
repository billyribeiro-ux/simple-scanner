from __future__ import annotations

import sys

from app.db.repositories import get_repository_registry
from app.services.scheduler import SchedulerService


def main() -> int:
    status = SchedulerService(get_repository_registry()).status()
    print(f"status={status.get('status')}")
    print(f"persistence_backend={status.get('persistence_backend')}")
    print(f"queued_jobs={status.get('queued_jobs')}")
    print(f"running_jobs={status.get('running_jobs')}")
    print(f"completed_jobs={status.get('completed_jobs')}")
    print(f"failed_jobs={status.get('failed_jobs')}")
    print(f"cancelled_jobs={status.get('cancelled_jobs')}")
    latest = status.get("latest_job") or {}
    if latest:
        print(f"latest_job={latest.get('job_id')} job_type={latest.get('job_type')} status={latest.get('status')}")
    latest_failed = status.get("latest_failed_job") or {}
    if latest_failed:
        print(
            "latest_failed_job="
            + f"{latest_failed.get('job_id')} job_type={latest_failed.get('job_type')} "
            + f"status={latest_failed.get('status')} reason={latest_failed.get('failed_reason')}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
