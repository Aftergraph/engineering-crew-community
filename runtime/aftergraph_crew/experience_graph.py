from __future__ import annotations
from dataclasses import dataclass
from .ui_contracts import ExperienceSpec
@dataclass(frozen=True, slots=True)
class ExperienceGraphReport:
    ok:bool; reachable:tuple[str,...]; terminal:tuple[str,...]; errors:tuple[str,...]; warnings:tuple[str,...]
class ExperienceGraph:
    def validate(self,spec:ExperienceSpec):
        ids={s.id for s in spec.screens}; edges={x:[] for x in ids}; errors=[]; warnings=[]
        for f in spec.flows:
            if f.source not in ids: errors.append(f"flow_unknown_source:{f.source}"); continue
            if f.target not in ids: errors.append(f"flow_unknown_target:{f.target}"); continue
            edges[f.source].append(f.target)
        seen=set(); stack=[spec.entry_screen]
        while stack:
            cur=stack.pop()
            if cur in seen: continue
            seen.add(cur); stack.extend(edges.get(cur,()))
        for sid in sorted(ids-seen): errors.append(f"screen_unreachable:{sid}")
        terminals={s.id for s in spec.screens if s.terminal}
        for s in spec.screens:
            if not s.terminal and len(spec.screens)>1 and not edges.get(s.id): warnings.append(f"screen_dead_end:{s.id}")
            if any(x in s.data_states for x in {"loading","empty","error"}) and "ready" not in s.data_states: errors.append(f"screen_ready_state_missing:{s.id}")
        if len(spec.screens)>1 and not terminals: warnings.append("experience_terminal_screen_missing")
        return ExperienceGraphReport(not errors,tuple(sorted(seen)),tuple(sorted(terminals)),tuple(dict.fromkeys(errors)),tuple(dict.fromkeys(warnings)))
