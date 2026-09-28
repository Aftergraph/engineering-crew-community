from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ContextCandidate:
    item_id: str
    estimated_tokens: int
    required_tags: frozenset[str]
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.item_id or self.estimated_tokens < 0:
            raise ValueError("context_candidate_invalid")
        object.__setattr__(self, "required_tags", frozenset(self.required_tags))


@dataclass(frozen=True, slots=True)
class ContextPlan:
    selected: tuple[str, ...]
    omitted: tuple[str, ...]
    tokens: int
    budget: int


class ContextBudgetPlanner:
    """Progressive-disclosure planner for skill/context metadata.

    Token counts are supplied by the caller. The planner does not pretend a
    character heuristic is an exact tokenizer.
    """

    def plan(self, candidates: Iterable[ContextCandidate], *, active_tags: Iterable[str], token_budget: int) -> ContextPlan:
        if token_budget < 0:
            raise ValueError("context_budget_invalid")
        tags = set(active_tags)
        rows = tuple(candidates)
        eligible = [x for x in rows if not x.required_tags or x.required_tags <= tags]
        eligible.sort(key=lambda x: (-x.priority, x.estimated_tokens, x.item_id))
        selected: list[str] = []
        used = 0
        for row in eligible:
            if used + row.estimated_tokens <= token_budget:
                selected.append(row.item_id)
                used += row.estimated_tokens
        omitted = tuple(sorted(x.item_id for x in rows if x.item_id not in selected))
        return ContextPlan(tuple(selected), omitted, used, token_budget)
