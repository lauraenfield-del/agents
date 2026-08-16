from __future__ import annotations

import json
import time
from collections import Counter
from typing import Any


class PerformanceLogger:
    """Collects per-run action metrics and returns a structured JSON report."""

    def __init__(self) -> None:
        self._run_started_at: float | None = None
        self._latencies: list[float] = []
        self._success_count = 0
        self._failure_count = 0
        self._error_types: Counter[str] = Counter()

    def start_run(self) -> None:
        self._run_started_at = time.perf_counter()
        self._latencies = []
        self._success_count = 0
        self._failure_count = 0
        self._error_types = Counter()

    def log_action(self, action: str, status: str, latency: float, error: str | None = None) -> None:
        self._latencies.append(max(0.0, float(latency)))
        if status == "success":
            self._success_count += 1
        else:
            self._failure_count += 1
            if error:
                self._error_types[error] += 1

    def end_run(self) -> dict[str, Any]:
        total_actions = self._success_count + self._failure_count
        avg_latency = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        duration = 0.0
        if self._run_started_at is not None:
            duration = max(0.0, time.perf_counter() - self._run_started_at)

        report: dict[str, Any] = {
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "avg_latency": avg_latency,
            "error_types": dict(self._error_types),
            "total_actions": total_actions,
            "run_duration": duration,
        }
        report["json"] = json.dumps(report, sort_keys=True)
        return report
