from __future__ import annotations
from dataclasses import dataclass
import hashlib, html, json, re
from typing import Mapping, Any
from .component_registry import ComponentRegistry
from .design_tokens import DesignTokenSet
from .responsive_layout import ResponsiveLayoutPlan
from .ui_contracts import ComponentNode, ExperienceSpec
@dataclass(frozen=True, slots=True)
class UIArtifactBundle:
    target:str; experience_digest:str; token_digest:str; files:Mapping[str,str]; digest:str
    def manifest(self): return {"schema":"UIArtifactBundle/v1","target":self.target,"experienceDigest":self.experience_digest,"tokenDigest":self.token_digest,"digest":self.digest,"files":{k:hashlib.sha256(v.encode()).hexdigest() for k,v in sorted(self.files.items())}}
class UICompiler:
    def __init__(self,registry:ComponentRegistry): self.registry=registry
    def _render(self,n:ComponentNode):
        c=self.registry.get(n.component); p=n.props; attrs=[f'data-ui-id="{html.escape(n.id)}"',f'data-ui-component="{html.escape(n.component)}"',f'class="ui-{re.sub(r"[^a-z0-9]+","-",n.component.lower())}"']
        if p.get("ariaLabel"): attrs.append(f'aria-label="{html.escape(str(p["ariaLabel"]))}"')
        if n.component=="Nav" and p.get("label"): attrs.append(f'aria-label="{html.escape(str(p["label"]))}"')
        if n.component=="Link": attrs.append(f'href="{html.escape(str(p.get("href","#")))}"')
        if n.component=="Image":
            attrs += [f'src="{html.escape(str(p.get("src","")))}"',f'alt="{html.escape(str(p.get("alt","")))}"']
            if p.get("decorative"): attrs.append('aria-hidden="true"')
            return f"<img {' '.join(attrs)} />"
        if n.component in {"TextField","Select","Checkbox"}:
            fid=f"field-{html.escape(n.id)}"; label=f'<label for="{fid}">{html.escape(str(p.get("label","")))}</label>'; name=html.escape(str(p.get("name",n.id)))
            if n.component=="TextField": control=f'<input id="{fid}" name="{name}" type="{html.escape(str(p.get("type","text")))}" {" ".join(attrs)} />'
            elif n.component=="Select": control=f'<select id="{fid}" name="{name}" {" ".join(attrs)}></select>'
            else: control=f'<input id="{fid}" name="{name}" type="checkbox" {" ".join(attrs)} />'
            return f'<div class="ui-field">{label}{control}</div>'
        if n.component=="Switch": attrs += ['role="switch"','aria-checked="false"']
        if n.component=="Alert": attrs.append('role="alert"')
        if n.component=="Tabs": attrs.append('role="tablist"')
        tag=c.semantic
        if n.component=="Heading": tag=str(p.get("as","h2")); tag=tag if tag in {"h1","h2","h3","h4","h5","h6"} else "h2"
        body="".join(self._render(ch) for ch in n.children)
        if n.component in {"Text","Heading","Badge","Alert"}: body=html.escape(str(p.get("text",p.get("label",""))))+body
        elif n.component in {"Button","IconButton","Link","Switch"}: body=html.escape(str(p.get("label",p.get("ariaLabel",""))))+body
        elif n.component=="Dialog" and (label:=p.get("label") or p.get("ariaLabel")): attrs.append(f'aria-label="{html.escape(str(label))}"')
        elif n.component=="Table" and p.get("caption"): body=f'<caption>{html.escape(str(p["caption"]))}</caption>'+body
        if tag=="hr": return f"<hr {' '.join(attrs)} />"
        return f"<{tag} {' '.join(attrs)}>{body}</{tag}>"
    def compile(self,spec:ExperienceSpec,tokens:DesignTokenSet,layout:ResponsiveLayoutPlan,target="html"):
        if target not in {"html","react"}: raise ValueError("unsupported_ui_target")
        css=tokens.to_css()+"""
*,*::before,*::after{box-sizing:border-box}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}html{color-scheme:light dark}body{margin:0;font-family:var(--font-family-body,system-ui,sans-serif);background:var(--color-background-canvas,#fff);color:var(--color-text-primary,#111)}
[data-ui-container]{container-type:inline-size;container-name:ui}.ui-stack{display:flex;flex-direction:column;gap:var(--space-4,1rem)}.ui-grid{display:grid;gap:var(--space-4,1rem)}button,a,input,select,[role=switch],[role=tab]{font:inherit}button,a,input,select,[role=switch]{min-block-size:44px}.ui-button,.ui-iconbutton{border:0;border-radius:var(--radius-md,.75rem);padding:var(--space-3,.75rem) var(--space-4,1rem);cursor:pointer}.ui-card{border-radius:var(--radius-lg,1rem);padding:var(--space-5,1.25rem);background:var(--color-surface-card,#fff)}:focus-visible{outline:2px solid var(--color-focus,#5b5bf7);outline-offset:3px}@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation-duration:.001ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition-duration:.001ms!important}}
"""+layout.to_css()
        body="".join(f'<section data-screen-id="{html.escape(s.id)}" data-ui-container{"" if s.id==spec.entry_screen else " hidden"}><h1 class="sr-only">{html.escape(s.title)}</h1>{self._render(s.root)}</section>' for s in spec.screens)
        manifest={"schema":"ExperienceManifest/v1","experience":spec.to_dict(),"entry":spec.entry_screen}
        files={"design-tokens.json":json.dumps(tokens.document,indent=2,sort_keys=True,ensure_ascii=False)+"\n","styles.css":css,"ui-manifest.json":json.dumps(manifest,indent=2,sort_keys=True,ensure_ascii=False)+"\n"}
        if target=="html": files["index.html"]='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(spec.product_name)+'</title><link rel="stylesheet" href="styles.css"></head><body>'+body+'</body></html>\n'
        else:
            react=body.replace(' class=', ' className=').replace(' for=', ' htmlFor=').replace(' hidden>', ' hidden>')
            files["src/App.tsx"]="export default function App(){return (<>"+react+"</>);}\n"; files["src/styles.css"]=css
        payload={"target":target,"experience":spec.digest,"tokens":tokens.digest,"files":{k:hashlib.sha256(v.encode()).hexdigest() for k,v in sorted(files.items())}}
        dg=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return UIArtifactBundle(target,spec.digest,tokens.digest,files,dg)
