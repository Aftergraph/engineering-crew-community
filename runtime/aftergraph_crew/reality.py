from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_MATURITY_RANK = {
    "unavailable": 0,
    "beta": 1,
    "integration_partial": 2,
    "verified": 3,
}


class CapabilityUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    capability_id: str
    maturity: str
    owner: str
    evidence: str
    truth_note: str = ""


class CapabilityRegistry:
    def __init__(self, records: Iterable[CapabilityRecord]):
        self._records = {row.capability_id: row for row in records}

    @classmethod
    def from_file(cls, path: Path) -> "CapabilityRegistry":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        records = []
        for row in raw.get("capabilities", []):
            maturity = row["maturity"]
            if maturity not in _MATURITY_RANK:
                raise ValueError(f"unknown_maturity:{maturity}")
            records.append(
                CapabilityRecord(
                    capability_id=row["id"], maturity=maturity, owner=row["owner"],
                    evidence=row.get("evidence", ""), truth_note=row.get("truthNote", ""),
                )
            )
        return cls(records)

    def get(self, capability_id: str) -> CapabilityRecord:
        try:
            return self._records[capability_id]
        except KeyError as exc:
            raise CapabilityUnavailableError(f"unknown_capability:{capability_id}") from exc

    def require(self, capability_ids: Iterable[str], *, minimum: str = "verified") -> tuple[CapabilityRecord, ...]:
        if minimum not in _MATURITY_RANK:
            raise ValueError(f"unknown_minimum_maturity:{minimum}")
        accepted: list[CapabilityRecord] = []
        for capability_id in capability_ids:
            row = self.get(capability_id)
            if row.maturity == "unavailable" or _MATURITY_RANK[row.maturity] < _MATURITY_RANK[minimum]:
                raise CapabilityUnavailableError(
                    f"capability_not_ready:{capability_id}:actual={row.maturity}:required={minimum}"
                )
            accepted.append(row)
        return tuple(accepted)

    def blockers(self, capability_ids: Iterable[str], *, minimum: str = "verified") -> tuple[str, ...]:
        blockers: list[str] = []
        for capability_id in capability_ids:
            try:
                self.require([capability_id], minimum=minimum)
            except CapabilityUnavailableError as exc:
                blockers.append(str(exc))
        return tuple(blockers)
