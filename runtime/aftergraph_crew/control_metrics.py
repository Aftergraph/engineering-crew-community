from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class MissionObservation:
    """One measured mission attempt used for system-level economics/quality."""

    declared_complete: bool
    verified: bool
    constraints_retained: int = 0
    constraints_total: int = 0
    recovery_attempted: bool = False
    recovered: bool = False
    action_attempts: int = 0
    unauthorized_actions: int = 0
    evidence_satisfied: int = 0
    evidence_required: int = 0
    total_cost: float = 0.0
    control_cost: float = 0.0
    total_tokens: int = 0
    control_tokens: int = 0
    time_to_verified_outcome_seconds: float | None = None

    def __post_init__(self) -> None:
        pairs = (
            ("constraints", self.constraints_retained, self.constraints_total),
            ("unauthorized_actions", self.unauthorized_actions, self.action_attempts),
            ("evidence", self.evidence_satisfied, self.evidence_required),
            ("control_tokens", self.control_tokens, self.total_tokens),
        )
        for name, part, total in pairs:
            if part < 0 or total < 0 or part > total:
                raise ValueError(f"invalid_metric_counts:{name}")
        if self.total_cost < 0 or self.control_cost < 0 or self.control_cost > self.total_cost:
            raise ValueError("invalid_metric_cost")
        if self.recovered and not self.recovery_attempted:
            raise ValueError("recovered_without_attempt")
        if self.time_to_verified_outcome_seconds is not None:
            if not self.verified or self.time_to_verified_outcome_seconds < 0:
                raise ValueError("invalid_tvo")


@dataclass(frozen=True, slots=True)
class ControlPlaneMetrics:
    attempts: int
    declared_completions: int
    verified_outcomes: int
    false_completions: int
    vsr: float
    fcr: float
    crr: float
    recovery_rate: float
    unauthorized_action_rate: float
    evidence_completeness: float
    cpvo: float | None
    cpt_cost: float
    cpt_tokens: float
    mean_tvo_seconds: float | None


@dataclass(frozen=True, slots=True)
class MetricsBudget:
    min_vsr: float = 0.0
    max_fcr: float = 1.0
    min_crr: float = 0.0
    min_evidence_completeness: float = 0.0
    max_unauthorized_action_rate: float = 1.0
    max_cpt_cost: float = 1.0
    max_cpt_tokens: float = 1.0
    max_cpvo: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "min_vsr", "max_fcr", "min_crr", "min_evidence_completeness",
            "max_unauthorized_action_rate", "max_cpt_cost", "max_cpt_tokens",
        ):
            value = float(getattr(self, name))
            if value < 0 or value > 1:
                raise ValueError(f"invalid_metrics_budget:{name}")
        if self.max_cpvo is not None and self.max_cpvo < 0:
            raise ValueError("invalid_metrics_budget:max_cpvo")

    def evaluate(self, metrics: ControlPlaneMetrics) -> tuple[str, ...]:
        reasons: list[str] = []
        checks = (
            (metrics.vsr < self.min_vsr, "vsr_below_minimum"),
            (metrics.fcr > self.max_fcr, "fcr_above_maximum"),
            (metrics.crr < self.min_crr, "crr_below_minimum"),
            (metrics.evidence_completeness < self.min_evidence_completeness, "evidence_below_minimum"),
            (metrics.unauthorized_action_rate > self.max_unauthorized_action_rate, "uar_above_maximum"),
            (metrics.cpt_cost > self.max_cpt_cost, "cpt_cost_above_maximum"),
            (metrics.cpt_tokens > self.max_cpt_tokens, "cpt_tokens_above_maximum"),
        )
        reasons.extend(reason for failed, reason in checks if failed)
        if self.max_cpvo is not None and (metrics.cpvo is None or metrics.cpvo > self.max_cpvo):
            reasons.append("cpvo_above_maximum")
        return tuple(reasons)


def _ratio(part: float, total: float) -> float:
    return 0.0 if total <= 0 else part / total


def aggregate_metrics(observations: Iterable[MissionObservation]) -> ControlPlaneMetrics:
    rows = tuple(observations)
    attempts = len(rows)
    declared = sum(1 for x in rows if x.declared_complete)
    verified = sum(1 for x in rows if x.verified)
    false = sum(1 for x in rows if x.declared_complete and not x.verified)
    retained = sum(x.constraints_retained for x in rows); constraints = sum(x.constraints_total for x in rows)
    recoveries = sum(1 for x in rows if x.recovered); recovery_attempts = sum(1 for x in rows if x.recovery_attempted)
    unauth = sum(x.unauthorized_actions for x in rows); actions = sum(x.action_attempts for x in rows)
    evidence = sum(x.evidence_satisfied for x in rows); required = sum(x.evidence_required for x in rows)
    total_cost = sum(x.total_cost for x in rows); control_cost = sum(x.control_cost for x in rows)
    total_tokens = sum(x.total_tokens for x in rows); control_tokens = sum(x.control_tokens for x in rows)
    tvos = [x.time_to_verified_outcome_seconds for x in rows if x.time_to_verified_outcome_seconds is not None]
    return ControlPlaneMetrics(
        attempts=attempts,
        declared_completions=declared,
        verified_outcomes=verified,
        false_completions=false,
        vsr=_ratio(verified, attempts),
        fcr=_ratio(false, declared),
        crr=_ratio(retained, constraints),
        recovery_rate=_ratio(recoveries, recovery_attempts),
        unauthorized_action_rate=_ratio(unauth, actions),
        evidence_completeness=_ratio(evidence, required),
        cpvo=(total_cost / verified) if verified else None,
        cpt_cost=_ratio(control_cost, total_cost),
        cpt_tokens=_ratio(control_tokens, total_tokens),
        mean_tvo_seconds=(sum(tvos) / len(tvos)) if tvos else None,
    )
