from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping
@dataclass(frozen=True, slots=True)
class ContainerRule:
    component_id:str; min_width:int|None=None; max_width:int|None=None; styles:Mapping[str,str]=field(default_factory=dict); container_name:str="ui"
    def __post_init__(self):
        if not self.component_id or not self.container_name: raise ValueError("container_rule_identity_required")
        if self.min_width is not None and self.min_width<0: raise ValueError("container_min_width")
        if self.max_width is not None and self.max_width<0: raise ValueError("container_max_width")
        if self.min_width is not None and self.max_width is not None and self.min_width>self.max_width: raise ValueError("container_range_invalid")
        if not self.styles: raise ValueError("container_rule_styles_required")
@dataclass(frozen=True, slots=True)
class ResponsiveLayoutPlan:
    rules:tuple[ContainerRule,...]=(); viewports:tuple[int,...]=(320,375,768,1024,1440)
    def __post_init__(self):
        if any(v<240 or v>5120 for v in self.viewports): raise ValueError("viewport_out_of_range")
        if len(set(self.viewports))!=len(self.viewports): raise ValueError("viewport_duplicate")
    def validate(self,ids:set[str]):
        errors=[]
        for r in self.rules:
            if r.component_id not in ids: errors.append(f"responsive_unknown_component:{r.component_id}")
        rows=list(self.rules)
        for i,a in enumerate(rows):
            for b in rows[i+1:]:
                if a.component_id!=b.component_id or a.container_name!=b.container_name: continue
                alo=-1 if a.min_width is None else a.min_width; ahi=10**9 if a.max_width is None else a.max_width; blo=-1 if b.min_width is None else b.min_width; bhi=10**9 if b.max_width is None else b.max_width
                if max(alo,blo)<=min(ahi,bhi) and set(a.styles)&set(b.styles): errors.append(f"responsive_conflicting_rules:{a.component_id}")
        return tuple(dict.fromkeys(errors))
    def to_css(self):
        lines=["[data-ui-container]{container-type:inline-size;container-name:ui}"]
        for r in self.rules:
            cond=[]
            if r.min_width is not None: cond.append(f"width >= {r.min_width}px")
            if r.max_width is not None: cond.append(f"width <= {r.max_width}px")
            q=" and ".join(f"({x})" for x in cond) if cond else "(width >= 0px)"
            lines += [f"@container {r.container_name} {q} {{",f"  [data-ui-id=\"{r.component_id}\"] {{"]+[f"    {k}: {v};" for k,v in sorted(r.styles.items())]+["  }","}"]
        return "\n".join(lines)+"\n"
