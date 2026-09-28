from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .accessibility_audit import AccessibilityAuditor
from .component_registry import default_component_registry
from .control_metrics import MissionObservation, aggregate_metrics
from .design_tokens import DesignTokenSet
from .experience_graph import ExperienceGraph
from .responsive_layout import ResponsiveLayoutPlan, ContainerRule
from .ui_compiler import UICompiler
from .ui_contracts import ComponentNode, ExperienceSpec, ScreenSpec
from .version import RELEASE_VERSION


TOOLS = (
    {"name": "community_doctor", "description": "Report Community edition identity and portable capabilities."},
    {"name": "uiux_audit", "description": "Audit an ExperienceSpec for flow and accessibility blockers."},
    {"name": "uiux_compile", "description": "Compile a deterministic HTML UI artifact from a minimal spec."},
    {"name": "metrics_aggregate", "description": "Aggregate verified outcome metrics from observations."},
)


class CommunityMCPServer:
    protocol = "2026-07-28"

    def handle(self, request: dict) -> dict:
        rid = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}
        if method == "server/discover":
            return {"jsonrpc": "2.0", "id": rid, "result": {"name": "aftergraph-engineering-crew-community", "version": RELEASE_VERSION, "protocolVersion": self.protocol, "capabilities": {"tools": {}}}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": rid, "result": {"tools": list(TOOLS)}}
        if method != "tools/call":
            return self._error(rid, -32601, "method_not_found")
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            result = self._call(name, args)
        except Exception as exc:
            return self._error(rid, -32000, f"tool_error:{exc}")
        return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": json.dumps(result, sort_keys=True)}], "structuredContent": result}}

    def _call(self, name: str, args: dict) -> dict:
        if name == "community_doctor":
            return {"ok": True, "edition": "community", "license": "Apache-2.0", "version": RELEASE_VERSION, "capabilities": ["mcp", "skills", "uiux", "context", "evidence", "metrics"]}
        if name == "metrics_aggregate":
            rows = [MissionObservation(**row) for row in args.get("observations", [])]
            return asdict(aggregate_metrics(rows))
        spec, tokens, layout = self._experience(args)
        registry = default_component_registry()
        if name == "uiux_audit":
            graph = ExperienceGraph(spec).validate()
            a11y = AccessibilityAuditor(registry).audit(spec, tokens)
            return {"ok": graph.ok and a11y.ok, "graph": asdict(graph), "accessibility": asdict(a11y)}
        if name == "uiux_compile":
            graph = ExperienceGraph(spec).validate()
            a11y = AccessibilityAuditor(registry).audit(spec, tokens)
            if not graph.ok or not a11y.ok:
                raise ValueError("uiux_gate_failed")
            art = UICompiler(registry).compile(spec, tokens, layout, target=args.get("target", "html"))
            return {"ok": True, "digest": art.digest, "manifest": art.manifest(), "files": dict(art.files)}
        raise ValueError("unknown_tool")

    @staticmethod
    def _error(rid, code, message):
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}

    @staticmethod
    def _experience(args: dict):
        raw = args.get("experience") or {}
        nodes = tuple(ComponentNode(id=n["id"], component=n["component"], props=n.get("props", {}), children=()) for n in raw.get("nodes", []))
        root = ComponentNode("root", "Stack", {}, nodes)
        screen = ScreenSpec(raw.get("screenId", "main"), raw.get("title", "Main"), root, "ready")
        spec = ExperienceSpec(raw.get("experienceId", "community-demo"), raw.get("productName", "Community UI"), screen.id, (screen,), ())
        token_doc = args.get("tokens") or {"color": {"text": {"$type": "color", "$value": "#111111"}, "background": {"$type": "color", "$value": "#ffffff"}}}
        tokens = DesignTokenSet(token_doc)
        rules = tuple(ContainerRule(r["selector"], min_width=r.get("minWidth"), max_width=r.get("maxWidth"), styles=r.get("styles", {})) for r in args.get("layout", []))
        return spec, tokens, ResponsiveLayoutPlan(rules, (320, 768, 1440))
