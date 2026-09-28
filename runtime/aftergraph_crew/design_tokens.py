from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, re
from typing import Any, Mapping
_ALIAS=re.compile(r"^\{([^{}]+)\}$")
@dataclass(frozen=True, slots=True)
class ResolvedToken:
    path:str; token_type:str; value:Any; description:str|None=None
class DesignTokenError(ValueError): pass
class DesignTokenSet:
    """Deterministic DTCG-2025.10-compatible token resolver for portable UI builds."""
    def __init__(self, document:Mapping[str,Any]):
        self.document=dict(document); self._raw={}; self._walk(self.document,(),None)
        if not self._raw: raise DesignTokenError("design_tokens_empty")
        self._resolved={p:self._resolve(p,()) for p in self._raw}
    def _walk(self,obj,prefix,inherited):
        group_type=str(obj.get("$type")) if "$type" in obj else inherited
        for key,value in obj.items():
            if key.startswith("$"): continue
            if not isinstance(value,Mapping): raise DesignTokenError(f"invalid_token_or_group:{'.'.join(prefix+(key,))}")
            path=prefix+(key,)
            if "$value" in value:
                typ=str(value.get("$type") or group_type or "unknown")
                if typ=="unknown": raise DesignTokenError(f"token_type_required:{'.'.join(path)}")
                self._raw['.'.join(path)]=(typ,value["$value"],value.get("$description"))
            else: self._walk(value,path,str(value.get("$type")) if "$type" in value else group_type)
    def _resolve(self,path,stack):
        if path not in self._raw: raise DesignTokenError(f"unknown_token_alias:{path}")
        if path in stack: raise DesignTokenError("token_alias_cycle:"+"->".join(stack+(path,)))
        typ,value,desc=self._raw[path]
        if isinstance(value,str) and (m:=_ALIAS.match(value)):
            target=m.group(1); resolved=self._resolve(target,stack+(path,))
            if typ!=resolved.token_type: raise DesignTokenError(f"token_alias_type_mismatch:{path}:{target}")
            value=resolved.value
        return ResolvedToken(path,typ,value,desc)
    @property
    def digest(self):
        p={k:{"type":v.token_type,"value":v.value} for k,v in sorted(self._resolved.items())}
        return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    def get(self,path):
        if path not in self._resolved: raise DesignTokenError(f"unknown_token:{path}")
        return self._resolved[path]
    def flattened(self): return dict(self._resolved)
    @staticmethod
    def _css_name(path): return "--"+re.sub(r"[^a-zA-Z0-9_-]+","-",path.replace(".","-"))
    @staticmethod
    def _css_value(t):
        v=t.value; typ=t.token_type
        if typ=="dimension" and isinstance(v,Mapping):
            n=v.get("value"); u=v.get("unit")
            if not isinstance(n,(int,float)) or u not in {"px","rem","em","%","vw","vh","ms","s"}: raise DesignTokenError(f"unsupported_dimension:{t.path}")
            return f"{n:g}{u}"
        if typ=="fontFamily" and isinstance(v,list): return ", ".join(json.dumps(str(x)) for x in v)
        if typ in {"number","duration"} and isinstance(v,(int,float)): return str(v)
        if typ=="boolean": return "1" if v else "0"
        if isinstance(v,str): return v
        if typ in {"shadow","border","typography","transition","gradient"}: return json.dumps(v,separators=(",",":"),ensure_ascii=False)
        raise DesignTokenError(f"unsupported_css_projection:{t.path}:{typ}")
    def to_css(self,selector=":root"):
        lines=[f"{selector} {{"]+[f"  {self._css_name(p)}: {self._css_value(t)};" for p,t in sorted(self._resolved.items())]+["}"]
        return "\n".join(lines)+"\n"
