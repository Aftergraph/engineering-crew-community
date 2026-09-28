from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class AuthorityExpansionError(ValueError):
    """Raised when a derived authority envelope attempts to add scopes."""


@dataclass(frozen=True, slots=True)
class AuthorityEnvelope:
    scopes: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "scopes", frozenset(self.scopes))

    def derive(self, requested_scopes: Iterable[str]) -> "AuthorityEnvelope":
        requested = frozenset(requested_scopes)
        expansion = requested - self.scopes
        if expansion:
            raise AuthorityExpansionError(
                "authority_expansion:" + ",".join(sorted(expansion))
            )
        return AuthorityEnvelope(requested)
