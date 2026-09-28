from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from .contracts_v6 import CanonicalContract, _sha, _utc


@dataclass(frozen=True, slots=True)
class ResourceBudget(CanonicalContract):
    """Bounded resource envelope carried by a mission contract.

    The package records limits but does not claim provider-side enforcement.
    External executors remain responsible for enforcing their own resource
    controls and emitting measured receipts.
    """

    schema = "ResourceBudget/v1"
    max_tokens: int | None = None
    max_cost: float | None = None
    max_wall_seconds: float | None = None
    max_interventions: int | None = None

    def __post_init__(self) -> None:
        for name in ("max_tokens", "max_interventions"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"negative_budget:{name}")
        for name in ("max_cost", "max_wall_seconds"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"negative_budget:{name}")


@dataclass(frozen=True, slots=True)
class MissionSpec(CanonicalContract):
    """Portable, bounded intent contract for one long-horizon mission."""

    schema = "MissionSpec/v1"
    mission_id: str
    objective: str
    subject: str
    acceptance_criteria: tuple[str, ...]
    constraints: tuple[str, ...]
    required_capabilities: frozenset[str]
    budget: ResourceBudget
    recovery_policy: str
    generation: int = 0

    def __post_init__(self) -> None:
        if not self.mission_id or not self.objective or not self.subject:
            raise ValueError("mission_spec_identity_required")
        if not self.acceptance_criteria or any(not x for x in self.acceptance_criteria):
            raise ValueError("mission_acceptance_required")
        if len(set(self.acceptance_criteria)) != len(self.acceptance_criteria):
            raise ValueError("duplicate_acceptance_criterion")
        if self.generation < 0:
            raise ValueError("invalid_generation")
        object.__setattr__(self, "acceptance_criteria", tuple(self.acceptance_criteria))
        object.__setattr__(self, "constraints", tuple(self.constraints))
        object.__setattr__(self, "required_capabilities", frozenset(self.required_capabilities))
        if not self.recovery_policy:
            raise ValueError("recovery_policy_required")


@dataclass(frozen=True, slots=True)
class ExecutionPlan(CanonicalContract):
    schema = "ExecutionPlan/v1"
    plan_id: str
    mission_digest: str
    exact_revision: str
    work_unit_ids: tuple[str, ...]
    generation: int

    def __post_init__(self) -> None:
        if not self.plan_id or not self.exact_revision or not self.work_unit_ids:
            raise ValueError("execution_plan_identity_required")
        _sha(self.mission_digest)
        if len(set(self.work_unit_ids)) != len(self.work_unit_ids):
            raise ValueError("duplicate_work_unit")
        if self.generation < 0:
            raise ValueError("invalid_generation")
        object.__setattr__(self, "work_unit_ids", tuple(self.work_unit_ids))


@dataclass(frozen=True, slots=True)
class DecisionRecord(CanonicalContract):
    schema = "DecisionRecord/v1"
    decision_id: str
    mission_id: str
    author_principal_id: str
    statement: str
    rationale: str
    alternatives: tuple[str, ...]
    observed_at: datetime

    def __post_init__(self) -> None:
        if not all((self.decision_id, self.mission_id, self.author_principal_id, self.statement, self.rationale)):
            raise ValueError("decision_record_identity_required")
        object.__setattr__(self, "alternatives", tuple(self.alternatives))
        object.__setattr__(self, "observed_at", _utc(self.observed_at))


@dataclass(frozen=True, slots=True)
class HandoffContract(CanonicalContract):
    schema = "Handoff/v1"
    mission_id: str
    generation: int
    verified_revision: str
    completed_work_units: tuple[str, ...]
    next_ready: tuple[str, ...]
    failed_gates: tuple[str, ...]
    dirty_files: tuple[str, ...]
    evidence_bundle_digest: str | None = None

    def __post_init__(self) -> None:
        if not self.mission_id or not self.verified_revision:
            raise ValueError("handoff_identity_required")
        if self.generation < 0:
            raise ValueError("invalid_generation")
        if self.evidence_bundle_digest is not None:
            _sha(self.evidence_bundle_digest)
        for name in ("completed_work_units", "next_ready", "failed_gates", "dirty_files"):
            values = tuple(getattr(self, name))
            if len(values) != len(set(values)):
                raise ValueError(f"handoff_duplicate:{name}")
            object.__setattr__(self, name, values)
