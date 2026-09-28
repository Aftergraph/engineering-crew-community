from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping


@dataclass(frozen=True, slots=True)
class ContextItem:
    source: str
    payload: Mapping[str, Any]
    trust: str
    sha256: str

    @classmethod
    def create(cls, source: str, payload: Mapping[str, Any], *, external: bool = False, verified: bool = False) -> "ContextItem":
        normalized = json.loads(json.dumps(dict(payload), sort_keys=True, separators=(",", ":")))
        trust = "verified" if verified else ("untrusted" if external else "local")
        digest = hashlib.sha256(
            json.dumps({"source": source, "payload": normalized, "trust": trust}, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return cls(source, MappingProxyType(normalized), trust, digest)


@dataclass(frozen=True, slots=True)
class ContextCapsule:
    items: tuple[ContextItem, ...]
    workspace_id: str
    mission_id: str
    sha256: str

    @classmethod
    def create(cls, items: Iterable[ContextItem], *, workspace_id: str, mission_id: str) -> "ContextCapsule":
        rows = tuple(items)
        canonical = {
            "workspace_id": workspace_id,
            "mission_id": mission_id,
            "items": [{"source": i.source, "trust": i.trust, "sha256": i.sha256} for i in rows],
        }
        digest = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(rows, workspace_id, mission_id, digest)
