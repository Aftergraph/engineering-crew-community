from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ArchitectureContract:
    module_owners: dict[str, str]
    allowed_dependencies: dict[str, tuple[str, ...]]

    @classmethod
    def from_file(cls, path: Path) -> "ArchitectureContract":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            module_owners=dict(raw["moduleOwners"]),
            allowed_dependencies={k: tuple(v) for k, v in raw["allowedDependencies"].items()},
        )

    def dependency_allowed(self, source_owner: str, target_owner: str) -> bool:
        return target_owner in self.allowed_dependencies.get(source_owner, ())

    def validate_tree(self, runtime_dir: Path) -> list[str]:
        runtime_dir = Path(runtime_dir)
        errors: list[str] = []
        actual = {p.stem for p in runtime_dir.glob("*.py") if p.name != "__init__.py"}
        declared = set(self.module_owners)
        for name in sorted(actual - declared):
            errors.append(f"ownerless_module:{name}")
        for name in sorted(declared - actual):
            errors.append(f"missing_module:{name}")
        return errors
