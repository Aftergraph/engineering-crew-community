from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, re
from typing import Iterable
_SHA=re.compile(r"^[0-9a-f]{64}$")
@dataclass(frozen=True, slots=True)
class VisualObservation:
    artifact_digest:str; screen_id:str; viewport_width:int; viewport_height:int; theme:str; screenshot_sha256:str; pixel_diff_ratio:float=0.; overflow_count:int=0; clipping_count:int=0; layout_shift_score:float=0.; browser:str="chromium"; reduced_motion:bool=False
    def __post_init__(self):
        if not _SHA.match(self.artifact_digest) or not _SHA.match(self.screenshot_sha256): raise ValueError("visual_digest_invalid")
        if self.viewport_width<240 or self.viewport_height<240: raise ValueError("visual_viewport_invalid")
        if not 0<=self.pixel_diff_ratio<=1 or min(self.overflow_count,self.clipping_count,self.layout_shift_score)<0: raise ValueError("visual_metric_invalid")
@dataclass(frozen=True, slots=True)
class VisualMatrix:
    screens:tuple[str,...]; viewports:tuple[int,...]=(320,768,1440); themes:tuple[str,...]=("light","dark"); require_reduced_motion:bool=True
@dataclass(frozen=True, slots=True)
class VisualQAReport:
    ok:bool; reasons:tuple[str,...]; covered_cases:int; required_cases:int; digest:str
class VisualQAGate:
    def __init__(self,*,max_diff_ratio=.005,max_layout_shift=.1): self.max_diff_ratio=max_diff_ratio; self.max_layout_shift=max_layout_shift
    def evaluate(self,artifact_digest,observations:Iterable[VisualObservation],matrix:VisualMatrix):
        reasons=[]; keys=set(); reduced=set()
        for o in observations:
            if o.artifact_digest!=artifact_digest: reasons.append(f"visual_artifact_mismatch:{o.screen_id}:{o.viewport_width}:{o.theme}"); continue
            k=(o.screen_id,o.viewport_width,o.theme)
            if k in keys: reasons.append(f"visual_duplicate_case:{o.screen_id}:{o.viewport_width}:{o.theme}")
            keys.add(k)
            if o.reduced_motion: reduced.add(k)
            if o.pixel_diff_ratio>self.max_diff_ratio: reasons.append(f"visual_diff_exceeded:{o.screen_id}:{o.viewport_width}:{o.theme}")
            if o.overflow_count: reasons.append(f"visual_overflow:{o.screen_id}:{o.viewport_width}:{o.theme}:{o.overflow_count}")
            if o.clipping_count: reasons.append(f"visual_clipping:{o.screen_id}:{o.viewport_width}:{o.theme}:{o.clipping_count}")
            if o.layout_shift_score>self.max_layout_shift: reasons.append(f"visual_layout_shift:{o.screen_id}:{o.viewport_width}:{o.theme}")
        required={(s,v,t) for s in matrix.screens for v in matrix.viewports for t in matrix.themes}
        for k in sorted(required-keys): reasons.append(f"visual_case_missing:{k[0]}:{k[1]}:{k[2]}")
        if matrix.require_reduced_motion:
            for k in sorted(required-reduced): reasons.append(f"visual_reduced_motion_missing:{k[0]}:{k[1]}:{k[2]}")
        payload={"artifact":artifact_digest,"covered":sorted(keys),"required":sorted(required),"reasons":sorted(set(reasons))}
        dg=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return VisualQAReport(not reasons,tuple(dict.fromkeys(reasons)),len(keys&required),len(required),dg)
