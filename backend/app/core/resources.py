from __future__ import annotations

import os
from pathlib import Path


def _memory_gib() -> float:
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return float(line.split()[1]) / (1024.0 * 1024.0)
    return 4.0


def adaptive_worker_count(
    *,
    requested: int | None = None,
    item_count: int | None = None,
    memory_gib_per_worker: float = 0.75,
    reserve_cpus: int = 1,
) -> int:
    """Choose a conservative CPU worker count from available CPU and RAM."""
    cpu_limit = max(1, (os.cpu_count() or 1) - reserve_cpus)
    memory_limit = max(1, int(_memory_gib() // max(memory_gib_per_worker, 0.25)))
    limit = min(cpu_limit, memory_limit, 32)
    if item_count is not None:
        limit = min(limit, max(1, item_count))
    if requested and requested > 0:
        limit = min(limit, requested)
    return max(1, limit)


def resource_snapshot() -> dict[str, float | int]:
    return {
        "logical_cpus": os.cpu_count() or 1,
        "memory_gib": round(_memory_gib(), 2),
        "recommended_fast_workers": adaptive_worker_count(memory_gib_per_worker=0.5),
        "recommended_quantum_threads": adaptive_worker_count(
            memory_gib_per_worker=2.5,
            reserve_cpus=2,
        ),
    }
