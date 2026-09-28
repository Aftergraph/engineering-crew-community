from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .ui_contracts import ComponentNode
@dataclass(frozen=True, slots=True)
class ComponentContract:
    name:str; semantic:str; interactive:bool=False; required_props:frozenset[str]=frozenset(); required_states:frozenset[str]=frozenset({"default"}); accessible_name_props:tuple[str,...]=(); aria_pattern:str|None=None
class ComponentRegistry:
    def __init__(self,contracts:Iterable[ComponentContract]=()): self._items={}; [self.register(x) for x in contracts]
    def register(self,item):
        if item.name in self._items: raise ValueError(f"component_duplicate:{item.name}")
        if not item.name or not item.semantic: raise ValueError("component_identity_required")
        self._items[item.name]=item
    def get(self,name):
        if name not in self._items: raise ValueError(f"unknown_component:{name}")
        return self._items[name]
    def names(self): return tuple(sorted(self._items))
    def validate_node(self,node):
        errors=[]
        try:c=self.get(node.component)
        except ValueError as exc: return (str(exc),)
        for p in sorted(c.required_props):
            if p not in node.props or node.props[p] in (None,""): errors.append(f"component_required_prop:{node.id}:{p}")
        for state in sorted(c.required_states-set(node.states)): errors.append(f"component_state_missing:{node.id}:{state}")
        if c.interactive and c.accessible_name_props and not any(str(node.props.get(p,"")).strip() for p in c.accessible_name_props): errors.append(f"component_accessible_name_missing:{node.id}")
        seen={node.id}
        def walk(n):
            if n.id in seen: errors.append(f"component_id_duplicate:{n.id}")
            else: seen.add(n.id)
            try: cc=self.get(n.component)
            except ValueError as exc: errors.append(str(exc)); cc=None
            if cc:
                for p in sorted(cc.required_props):
                    if p not in n.props or n.props[p] in (None,""): errors.append(f"component_required_prop:{n.id}:{p}")
                for state in sorted(cc.required_states-set(n.states)): errors.append(f"component_state_missing:{n.id}:{state}")
                if cc.interactive and cc.accessible_name_props and not any(str(n.props.get(p,"")).strip() for p in cc.accessible_name_props): errors.append(f"component_accessible_name_missing:{n.id}")
            for ch in n.children: walk(ch)
        for ch in node.children: walk(ch)
        return tuple(dict.fromkeys(errors))
def default_component_registry():
    focus=frozenset({"default","hover","focus-visible","disabled"})
    return ComponentRegistry((
      ComponentContract("Page","main"),ComponentContract("Section","section"),ComponentContract("Stack","div"),ComponentContract("Grid","div"),
      ComponentContract("Text","p",required_props=frozenset({"text"})),ComponentContract("Heading","h2",required_props=frozenset({"text"})),
      ComponentContract("Button","button",True,frozenset({"label"}),focus,("label","ariaLabel"),"button"),ComponentContract("IconButton","button",True,frozenset(),focus,("ariaLabel",),"button"),
      ComponentContract("Link","a",True,frozenset({"label","href"}),frozenset({"default","hover","focus-visible"}),("label","ariaLabel"),"link"),
      ComponentContract("TextField","input",True,frozenset({"label","name"}),frozenset({"default","focus-visible","disabled","invalid"}),("label","ariaLabel"),"textbox"),
      ComponentContract("Select","select",True,frozenset({"label","name"}),frozenset({"default","focus-visible","disabled"}),("label","ariaLabel"),"combobox"),
      ComponentContract("Checkbox","input",True,frozenset({"label","name"}),frozenset({"default","focus-visible","disabled","checked"}),("label","ariaLabel"),"checkbox"),
      ComponentContract("Switch","button",True,frozenset({"label"}),frozenset({"default","focus-visible","disabled","checked"}),("label","ariaLabel"),"switch"),
      ComponentContract("Dialog","dialog",False,frozenset({"label"}),frozenset({"default","open"}),("label","ariaLabel"),"dialog"),ComponentContract("Tabs","div",True,frozenset({"label"}),frozenset({"default","focus-visible"}),("label",),"tabs"),
      ComponentContract("Card","article"),ComponentContract("Nav","nav",False,frozenset({"label"}),frozenset({"default"}),("label",),"navigation"),ComponentContract("Image","img"),
      ComponentContract("Badge","span",required_props=frozenset({"text"})),ComponentContract("Alert","div",False,frozenset({"text"}),frozenset({"default"}),(),"alert"),ComponentContract("Table","table",False,frozenset({"caption"})),ComponentContract("Divider","hr"),ComponentContract("Spacer","div")
    ))
