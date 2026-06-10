from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any
from uuid import UUID, uuid4


@dataclass
class AuditTrailTracker:
    """Append-only in-memory audit trail used by the PoC and API responses.

    Production deployment should persist the same records in PostgreSQL.
    """

    project_id: UUID
    pipeline_id: UUID = field(default_factory=uuid4)
    records: list[dict[str, Any]] = field(default_factory=list)

    def log(self, step_name: str, metadata: dict[str, Any]) -> None:
        self.records.append(
            {
                "pipeline_id": str(self.pipeline_id),
                "project_id": str(self.project_id),
                "step_name": step_name,
                "timestamp_unix": time(),
                "metadata": metadata,
            }
        )

    def export(self) -> list[dict[str, Any]]:
        return list(self.records)
