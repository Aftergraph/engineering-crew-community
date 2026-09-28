from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReleaseStage(str, Enum):
    BUILT = "built"
    VERIFIED = "verified"
    CANARY = "canary"
    STABLE = "stable"
    REVOKED = "revoked"


_ALLOWED = {
    ReleaseStage.BUILT: {ReleaseStage.VERIFIED, ReleaseStage.REVOKED},
    ReleaseStage.VERIFIED: {ReleaseStage.CANARY, ReleaseStage.REVOKED},
    ReleaseStage.CANARY: {ReleaseStage.STABLE, ReleaseStage.REVOKED},
    ReleaseStage.STABLE: {ReleaseStage.REVOKED},
    ReleaseStage.REVOKED: set(),
}


@dataclass(frozen=True, slots=True)
class PromotionReceipt:
    release: str
    artifact_digest: str
    from_stage: str
    to_stage: str
    verifier: str


def promote(release: str, artifact_digest: str, current: ReleaseStage | str, target: ReleaseStage | str, *, verifier: str, gates_ok: bool) -> PromotionReceipt:
    current, target = ReleaseStage(current), ReleaseStage(target)
    if target not in _ALLOWED[current]:
        raise ValueError(f"release_train:invalid_transition:{current.value}:{target.value}")
    if target != ReleaseStage.REVOKED and not gates_ok:
        raise PermissionError("release_train:gates_failed")
    if not verifier.strip():
        raise ValueError("release_train:verifier_required")
    if len(artifact_digest) != 64 or any(c not in "0123456789abcdef" for c in artifact_digest.lower()):
        raise ValueError("release_train:artifact_digest")
    return PromotionReceipt(release, artifact_digest.lower(), current.value, target.value, verifier)
