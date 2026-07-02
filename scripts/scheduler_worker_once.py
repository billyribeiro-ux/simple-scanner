from __future__ import annotations

import argparse
import sys

from app.db.repositories import get_repository_registry
from app.services.scheduler import DEFAULT_LEASE_SECONDS, DEFAULT_MAX_JOBS, SchedulerService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the bounded local scheduler worker exactly once."
    )
    parser.add_argument("--max-jobs", type=int, default=DEFAULT_MAX_JOBS)
    parser.add_argument("--lease-owner", default=None)
    parser.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)
    parser.add_argument(
        "--recover-only",
        action="store_true",
        help="Recover stale leased jobs and exit without leasing new jobs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    service = SchedulerService(get_repository_registry())
    if args.recover_only:
        result = service.recover_stale_leases(limit=args.max_jobs)
        print("status=ok")
        print("worker_mode=recover_stale_once")
        print(f"jobs_recovered={result.get('jobs_recovered', 0)}")
        for job in result.get("results", []):
            print(f"job={job.get('job_id')} status={job.get('status')}")
        return 0

    result = service.run_worker_once(
        max_jobs=args.max_jobs,
        lease_owner=args.lease_owner,
        lease_seconds=args.lease_seconds,
    )
    print("status=ok")
    print(f"worker_mode={result.get('worker_mode')}")
    print(f"lease_owner={result.get('lease_owner')}")
    print(f"lease_seconds={result.get('lease_seconds')}")
    print(f"jobs_run={result.get('jobs_run', 0)}")
    stale = result.get("stale_recovery") or {}
    print(f"jobs_recovered={stale.get('jobs_recovered', 0)}")
    for job in result.get("results", []):
        print(f"job={job.get('job_id')} status={job.get('status')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
