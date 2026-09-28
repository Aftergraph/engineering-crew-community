from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


def _utc(v: datetime) -> datetime:
    if v.tzinfo is None: raise ValueError('bootstrap:timezone_required')
    return v.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class HostBootstrapReceipt:
    schema: str
    host: str
    host_identity: str
    release_version: str
    artifact_sha256: str
    invocation_ok: bool
    mcp_ok: bool
    observed_at: datetime
    generation: int

    def __post_init__(self) -> None:
        if self.schema != 'HostBootstrapReceipt/v1' or not self.host or not self.host_identity:
            raise ValueError('bootstrap:identity')
        if len(self.artifact_sha256)!=64 or any(c not in '0123456789abcdef' for c in self.artifact_sha256.lower()):
            raise ValueError('bootstrap:digest')
        if self.generation < 0: raise ValueError('bootstrap:generation')
        object.__setattr__(self,'observed_at',_utc(self.observed_at))

    def validate(self, *, now: datetime, expected_host: str, expected_release: str,
                 expected_artifact: str, expected_generation: int, max_age: timedelta=timedelta(minutes=15)) -> tuple[str,...]:
        now=_utc(now); errors=[]
        if self.host != expected_host: errors.append('bootstrap:host_mismatch')
        if self.release_version != expected_release: errors.append('bootstrap:release_mismatch')
        if self.artifact_sha256 != expected_artifact: errors.append('bootstrap:artifact_mismatch')
        if self.generation != expected_generation: errors.append('bootstrap:stale_generation')
        if now < self.observed_at or now-self.observed_at > max_age: errors.append('bootstrap:stale_receipt')
        if not self.invocation_ok: errors.append('bootstrap:invocation_failed')
        if not self.mcp_ok: errors.append('bootstrap:mcp_failed')
        return tuple(errors)
