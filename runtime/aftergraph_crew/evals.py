from __future__ import annotations

import json
from pathlib import Path

from .router import CrewRouter


def run_route_evals(root: Path) -> dict[str, object]:
    root = Path(root)
    router = CrewRouter.from_files(root / "config" / "crew.json", root / "config" / "routing.json")
    failures: list[dict[str, object]] = []
    total = 0
    for line in (root / "evals" / "scenarios.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        total += 1
        case = json.loads(line)
        decision = router.route(case["request"])
        missing = sorted(set(case["required_roles"]) - set(decision.roles))
        if decision.workflow != case["workflow"] or missing:
            failures.append({
                "id": case["id"],
                "expected_workflow": case["workflow"],
                "actual_workflow": decision.workflow,
                "missing_roles": missing,
            })
    return {"total": total, "passed": total - len(failures), "failed": len(failures), "failures": failures}
