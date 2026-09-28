from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class InstallReceipt:
    schema: str
    version: str
    artifact_sha256: str
    slot: str
    previous_slot: str | None


class AtomicInstaller:
    """Two-slot install layout with explicit activation and rollback receipts."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.slots = self.root / "slots"
        self.state = self.root / "install-state.json"
        self.slots.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _digest(path: Path) -> str:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def _state(self) -> dict:
        if not self.state.exists():
            return {"active": None, "previous": None}
        return json.loads(self.state.read_text())

    def stage_file(self, artifact: Path, version: str) -> str:
        digest = self._digest(artifact)
        slot = f"{version}-{digest[:12]}"
        dest = self.slots / slot
        if dest.exists():
            existing = dest / Path(artifact).name
            if not existing.exists() or self._digest(existing) != digest:
                raise RuntimeError("install:slot_digest_conflict")
            return slot
        tmp = Path(tempfile.mkdtemp(prefix="stage-", dir=self.slots))
        try:
            shutil.copy2(artifact, tmp / Path(artifact).name)
            os.replace(tmp, dest)
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)
            raise
        return slot

    def activate(self, slot: str, version: str, artifact_sha256: str) -> InstallReceipt:
        if not (self.slots / slot).is_dir():
            raise FileNotFoundError("install:unknown_slot")
        current = self._state()
        new = {"active": slot, "previous": current.get("active")}
        tmp = self.state.with_suffix(".tmp")
        tmp.write_text(json.dumps(new, sort_keys=True))
        os.replace(tmp, self.state)
        return InstallReceipt("InstallReceipt/v1", version, artifact_sha256, slot, current.get("active"))

    def rollback(self) -> str:
        current = self._state()
        previous = current.get("previous")
        if not previous or not (self.slots / previous).is_dir():
            raise RuntimeError("install:no_rollback_slot")
        new = {"active": previous, "previous": current.get("active")}
        tmp = self.state.with_suffix(".tmp")
        tmp.write_text(json.dumps(new, sort_keys=True))
        os.replace(tmp, self.state)
        return previous
