from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .reality import CapabilityRegistry


@dataclass(frozen=True, slots=True)
class RouteDecision:
    workflow: str
    roles: tuple[str, ...]
    builder_role: str | None
    verifier_role: str | None
    matched_signals: tuple[str, ...]
    topology: str
    risk_tier: str
    required_capabilities: tuple[str, ...]
    blocked_capabilities: tuple[str, ...]


class CrewRouter:
    def __init__(self, crew: dict[str, Any], routing: dict[str, Any], reality: CapabilityRegistry | None = None):
        self.crew = crew
        self.routing = routing
        self.reality = reality

    @classmethod
    def from_files(cls, crew_path: Path, routing_path: Path) -> "CrewRouter":
        routing_path = Path(routing_path)
        cap_path = routing_path.parent / "capabilities.json"
        reality = CapabilityRegistry.from_file(cap_path) if cap_path.is_file() else None
        return cls(
            json.loads(Path(crew_path).read_text(encoding="utf-8")),
            json.loads(routing_path.read_text(encoding="utf-8")),
            reality,
        )

    def route(self, request: str) -> RouteDecision:
        text = request.lower()
        best: tuple[int, int, dict[str, Any], list[str]] | None = None
        for index, rule in enumerate(self.routing["rules"]):
            matched = [signal for signal in rule["signals"] if signal in text]
            if not matched:
                continue
            score = len(matched) * 100 + int(rule.get("priority", 0))
            candidate = (score, -index, rule, matched)
            if best is None or candidate[:2] > best[:2]:
                best = candidate

        if best is None:
            rule = self.routing["default"]
            matched = []
        else:
            rule = best[2]
            matched = best[3]

        roles = list(rule["roles"])
        if rule.get("consequential"):
            for required in ("aftergraph-builder-max", "aftergraph-verifier"):
                if required not in roles:
                    roles.append(required)
        builder = "aftergraph-builder-max" if "aftergraph-builder-max" in roles else None
        verifier = "aftergraph-verifier" if "aftergraph-verifier" in roles else None
        if builder is not None and builder == verifier:
            raise ValueError("builder_verifier_collision")

        required_caps = tuple(rule.get("requiredCapabilities", ()))
        minimum = rule.get("minimumMaturity", "verified")
        blockers = self.reality.blockers(required_caps, minimum=minimum) if self.reality else ()
        return RouteDecision(
            workflow=rule["workflow"],
            roles=tuple(roles),
            builder_role=builder,
            verifier_role=verifier,
            matched_signals=tuple(matched),
            topology=rule.get("topology", "single"),
            risk_tier=rule.get("riskTier", "low"),
            required_capabilities=required_caps,
            blocked_capabilities=blockers,
        )
