from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

_URL=re.compile(r'(?i)(git\+|https?://|ssh://)')

@dataclass(frozen=True, slots=True)
class DependencyHygieneReport:
    ok: bool
    errors: tuple[str,...]
    dependencies: tuple[str,...]


def audit_pyproject(path: Path, *, community: bool=False) -> DependencyHygieneReport:
    data=tomllib.loads(Path(path).read_text())
    project=data.get('project',{})
    deps=list(project.get('dependencies',[]) or [])
    for rows in (project.get('optional-dependencies',{}) or {}).values(): deps.extend(rows)
    errors=[]
    for dep in deps:
        if _URL.search(dep): errors.append(f'dependency:direct_url_forbidden:{dep}')
        if '@' in dep: errors.append(f'dependency:unpinned_source_reference:{dep}')
    if community:
        lic=project.get('license')
        text=lic.get('text') if isinstance(lic,dict) else lic
        if text != 'Apache-2.0': errors.append('dependency:community_license_not_apache_2')
    return DependencyHygieneReport(not errors,tuple(errors),tuple(sorted(deps)))
