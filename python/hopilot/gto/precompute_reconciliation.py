from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


# Deterministic reconciliation for split transaction persistence.
# This module only derives job/session accounting from persisted scenario-link
# outcomes and does not modify raw matrix or simulation data.
@dataclass
class PrecomputeJobReconciliationResult:
    job_session_id: int
    requested_scenarios: int
    completed_scenarios: int
    failed_scenarios: int
    pending_scenarios: int
    running_scenarios: int
    canceled: bool
    final_run_state: str
    corrected: bool


def summarize_link_statuses(links: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {
        "COMPLETED": 0,
        "FAILED": 0,
        "PENDING": 0,
        "RUNNING": 0,
        "CANCELED": 0,
    }
    for link in links:
        status = getattr(link, "status", None)
        if status in counts:
            counts[status] += 1
        elif status is not None:
            counts.setdefault(status, 0)
            counts[status] += 1
    return counts


def determine_final_state(
    *,
    canceled: bool,
    requested_scenarios: int,
    completed: int,
    failed: int,
    pending: int,
    running: int,
) -> str:
    if canceled:
        return "CANCELED"
    if running > 0:
        return "RUNNING"
    if completed + failed == requested_scenarios:
        return "COMPLETED" if failed == 0 else "FAILED"
    if pending > 0:
        return "FAILED"
    return "FAILED"


def reconcile_job_tracking(
    job_session: Any,
    links: Iterable[Any],
    *,
    canceled: bool = False,
) -> PrecomputeJobReconciliationResult:
    if job_session is None:
        raise ValueError("job_session is required")

    counts = summarize_link_statuses(links)
    completed = counts.get("COMPLETED", 0)
    failed = counts.get("FAILED", 0)
    pending = counts.get("PENDING", 0)
    running = counts.get("RUNNING", 0)
    requested = int(getattr(job_session, "requested_scenarios", 0))

    final_state = determine_final_state(
        canceled=canceled,
        requested_scenarios=requested,
        completed=completed,
        failed=failed,
        pending=pending,
        running=running,
    )

    corrected = (
        int(getattr(job_session, "completed_scenarios", 0)) != completed
        or int(getattr(job_session, "failed_scenarios", 0)) != failed
    )

    return PrecomputeJobReconciliationResult(
        job_session_id=int(getattr(job_session, "id", 0)),
        requested_scenarios=requested,
        completed_scenarios=completed,
        failed_scenarios=failed,
        pending_scenarios=pending,
        running_scenarios=running,
        canceled=canceled,
        final_run_state=final_state,
        corrected=corrected,
    )
