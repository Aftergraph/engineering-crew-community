from __future__ import annotations
from dataclasses import dataclass
import re
from .component_registry import ComponentRegistry
from .design_tokens import DesignTokenSet, DesignTokenError
from .ui_contracts import ComponentNode, ExperienceSpec
_HEX=re.compile(r"^#([0-9a-fA-F]{6})$")
@dataclass(frozen=True, slots=True)
class AccessibilityIssue:
    severity:str; code:str; subject:str; detail:str
@dataclass(frozen=True, slots=True)
class AccessibilityReport:
    ok:bool; issues:tuple[AccessibilityIssue,...]; error_count:int; warning_count:int
def _lum(c):
    m=_HEX.match(c)
    if not m: raise ValueError("unsupported_color")
    xs=[int(m.group(1)[i:i+2],16)/255 for i in (0,2,4)]; xs=[x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in xs]
    return .2126*xs[0]+.7152*xs[1]+.0722*xs[2]
def contrast_ratio(a,b):
    x,y=sorted((_lum(a),_lum(b)),reverse=True); return (x+.05)/(y+.05)
class AccessibilityAuditor:
    def __init__(self,registry:ComponentRegistry): self.registry=registry
    def audit(self,spec:ExperienceSpec,tokens:DesignTokenSet|None=None):
        issues=[]; ids=set()
        def visit(n:ComponentNode):
            if n.id in ids: issues.append(AccessibilityIssue("error","duplicate_id",n.id,"Component IDs must be unique."))
            ids.add(n.id)
            try:c=self.registry.get(n.component)
            except ValueError: issues.append(AccessibilityIssue("error","unknown_component",n.id,n.component)); c=None
            if c and c.interactive:
                if "focus-visible" not in n.states: issues.append(AccessibilityIssue("error","focus_state_missing",n.id,"Interactive control lacks focus-visible state."))
                if c.accessible_name_props and not any(str(n.props.get(p,"")).strip() for p in c.accessible_name_props): issues.append(AccessibilityIssue("error","accessible_name_missing",n.id,"Interactive control requires an accessible name."))
                try: target=float(n.props.get("touchTargetPx",44))
                except Exception: target=0
                if target<24: issues.append(AccessibilityIssue("error","target_too_small",n.id,"WCAG 2.2 minimum target size is 24 CSS px unless an exception applies."))
                elif target<44: issues.append(AccessibilityIssue("warning","target_below_builder_recommendation",n.id,"24px passes the baseline; 44px is the builder comfort recommendation."))
            if n.component=="Image" and not (str(n.props.get("alt","")).strip() or n.props.get("decorative") is True): issues.append(AccessibilityIssue("error","image_alt_missing",n.id,"Image requires alt text or decorative=true."))
            if n.props.get("statusColorOnly") is True: issues.append(AccessibilityIssue("error","color_only_status",n.id,"Status cannot be communicated by color alone."))
            for ch in n.children: visit(ch)
        for s in spec.screens:
            visit(s.root)
            if "loading" in s.data_states and "error" not in s.data_states: issues.append(AccessibilityIssue("warning","error_state_missing",s.id,"Loading surface has no explicit error state."))
            if "loading" in s.data_states and "empty" not in s.data_states: issues.append(AccessibilityIssue("warning","empty_state_missing",s.id,"Loading surface has no explicit empty state."))
        if tokens:
            for fg,bg,minr in (("color.text.primary","color.background.canvas",4.5),("color.text.muted","color.background.canvas",4.5)):
                try:
                    a=tokens.get(fg).value; b=tokens.get(bg).value
                    if isinstance(a,str) and isinstance(b,str) and _HEX.match(a) and _HEX.match(b):
                        ratio=contrast_ratio(a,b)
                        if ratio<minr: issues.append(AccessibilityIssue("error","contrast_fail",f"{fg}/{bg}",f"Contrast {ratio:.2f}:1 < {minr}:1."))
                except (DesignTokenError,ValueError): pass
            if any(k.startswith("motion.") for k in tokens.flattened()) and "motion.reduced" not in tokens.flattened(): issues.append(AccessibilityIssue("warning","reduced_motion_token_missing","motion","Motion tokens exist without motion.reduced override."))
        ec=sum(i.severity=="error" for i in issues); wc=sum(i.severity=="warning" for i in issues)
        return AccessibilityReport(ec==0,tuple(issues),ec,wc)
