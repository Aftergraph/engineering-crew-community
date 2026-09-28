from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .atomic_install import AtomicInstaller
from .compatibility_v13 import UpgradeContract, plan_migration
from .release_channel_v13 import ReleaseChannelManifest


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _major(v: str) -> int:
    return int(v.split('.',1)[0])


@dataclass(frozen=True, slots=True)
class UpdateReceipt:
    schema: str
    from_version: str
    to_version: str
    artifact_sha256: str
    slot: str
    previous_slot: str | None
    migration_steps: tuple[str,...]
    health_ok: bool
    rolled_back: bool
    channel_sequence: int


class UpdateManager:
    """Transactional local updater: verify -> stage -> migrate -> activate -> health -> rollback."""

    def __init__(self, installer: AtomicInstaller):
        self.installer=installer

    def update(self, *, artifact: Path, artifact_name: str, current_version: str,
               manifest: ReleaseChannelManifest, contract: UpgradeContract,
               manifest_errors: tuple[str,...], health_check: Callable[[], bool],
               allow_major_downgrade: bool=False) -> UpdateReceipt:
        if manifest_errors:
            raise PermissionError('update:channel_unverified:' + ','.join(manifest_errors))
        if manifest.release_version != contract.to_version or contract.from_version != current_version:
            raise ValueError('update:contract_version_mismatch')
        if _major(contract.to_version) < _major(current_version) and not allow_major_downgrade:
            raise PermissionError('update:downgrade_forbidden')
        descriptor=next((x for x in manifest.artifacts if x.name==artifact_name),None)
        if descriptor is None:
            raise ValueError('update:artifact_not_in_channel')
        actual=_sha(artifact)
        if descriptor.sha256 != actual:
            raise ValueError('update:artifact_digest_mismatch')
        if descriptor.size != Path(artifact).stat().st_size:
            raise ValueError('update:artifact_size_mismatch')
        migration=plan_migration(contract)
        slot=self.installer.stage_file(artifact, contract.to_version)
        receipt=self.installer.activate(slot, contract.to_version, actual)
        ok=False
        rolled=False
        try:
            ok=bool(health_check())
        except Exception:
            ok=False
        if not ok:
            if receipt.previous_slot:
                self.installer.rollback(); rolled=True
            raise RuntimeError('update:post_activation_health_failed')
        return UpdateReceipt('UpdateReceipt/v1', current_version, contract.to_version, actual, slot,
                             receipt.previous_slot, migration.applied_steps, True, rolled, manifest.sequence)
