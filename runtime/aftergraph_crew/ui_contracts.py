from __future__ import annotations
from dataclasses import dataclass, field
import hashlib, json
from typing import Any, Mapping

def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

@dataclass(frozen=True, slots=True)
class ComponentNode:
    id: str
    component: str
    props: Mapping[str, Any] = field(default_factory=dict)
    children: tuple["ComponentNode", ...] = ()
    states: frozenset[str] = frozenset({"default"})
    def __post_init__(self):
        if not self.id.strip(): raise ValueError("component_id_required")
        if not self.component.strip(): raise ValueError("component_type_required")
        if "default" not in self.states: raise ValueError("component_default_state_required")
    def to_dict(self):
        return {"id":self.id,"component":self.component,"props":dict(self.props),"states":sorted(self.states),"children":[c.to_dict() for c in self.children]}

@dataclass(frozen=True, slots=True)
class ScreenSpec:
    id: str
    title: str
    root: ComponentNode
    kind: str = "page"
    data_states: frozenset[str] = frozenset({"ready"})
    terminal: bool = False
    def __post_init__(self):
        if not self.id.strip() or not self.title.strip(): raise ValueError("screen_identity_required")
        if self.kind not in {"page","dialog","sheet","panel","onboarding"}: raise ValueError("unsupported_screen_kind")
        if not self.data_states: raise ValueError("screen_data_states_required")
    def to_dict(self):
        return {"id":self.id,"title":self.title,"kind":self.kind,"dataStates":sorted(self.data_states),"terminal":self.terminal,"root":self.root.to_dict()}

@dataclass(frozen=True, slots=True)
class FlowEdge:
    source: str
    target: str
    event: str
    condition: str | None = None
    def __post_init__(self):
        if not self.source or not self.target or not self.event: raise ValueError("flow_edge_identity_required")
    def to_dict(self): return {"source":self.source,"target":self.target,"event":self.event,"condition":self.condition}

@dataclass(frozen=True, slots=True)
class ExperienceSpec:
    experience_id: str
    product_name: str
    entry_screen: str
    screens: tuple[ScreenSpec, ...]
    flows: tuple[FlowEdge, ...] = ()
    goals: tuple[str, ...] = ()
    platform: str = "web"
    visual_direction: tuple[str, ...] = ()
    def __post_init__(self):
        if not self.experience_id.strip() or not self.product_name.strip(): raise ValueError("experience_identity_required")
        if self.platform not in {"web","mobile-web","desktop-web","embedded"}: raise ValueError("unsupported_experience_platform")
        ids=[s.id for s in self.screens]
        if len(ids)!=len(set(ids)): raise ValueError("duplicate_screen_id")
        if self.entry_screen not in ids: raise ValueError("entry_screen_missing")
    @property
    def digest(self): return _digest(self.to_dict())
    def to_dict(self):
        return {"schema":"ExperienceSpec/v1","experienceId":self.experience_id,"productName":self.product_name,"entryScreen":self.entry_screen,"screens":[s.to_dict() for s in self.screens],"flows":[f.to_dict() for f in self.flows],"goals":list(self.goals),"platform":self.platform,"visualDirection":list(self.visual_direction)}

def node_from_dict(raw: Mapping[str, Any]) -> ComponentNode:
    return ComponentNode(str(raw.get("id","")),str(raw.get("component","")),dict(raw.get("props") or {}),tuple(node_from_dict(x) for x in raw.get("children") or ()),frozenset(str(x) for x in raw.get("states") or ("default",)))

def experience_from_dict(raw: Mapping[str, Any]) -> ExperienceSpec:
    screens=tuple(ScreenSpec(str(x.get("id","")),str(x.get("title","")),node_from_dict(x.get("root") or {}),str(x.get("kind","page")),frozenset(str(s) for s in x.get("dataStates") or ("ready",)),bool(x.get("terminal",False))) for x in raw.get("screens") or ())
    flows=tuple(FlowEdge(str(x.get("source","")),str(x.get("target","")),str(x.get("event","")),x.get("condition")) for x in raw.get("flows") or ())
    return ExperienceSpec(str(raw.get("experienceId","")),str(raw.get("productName","")),str(raw.get("entryScreen","")),screens,flows,tuple(str(x) for x in raw.get("goals") or ()),str(raw.get("platform","web")),tuple(str(x) for x in raw.get("visualDirection") or ()))
