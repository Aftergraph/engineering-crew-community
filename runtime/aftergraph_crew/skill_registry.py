from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path, PurePosixPath
import re
from typing import Any
from urllib.parse import urlparse


_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _frontmatter(text: str) -> dict[str, Any]:
    match = _FRONTMATTER.match(text)
    if not match:
        raise ValueError("skill_frontmatter_missing")
    result: dict[str, Any] = {}
    for raw in match.group(1).splitlines():
        if ":" not in raw or raw.lstrip().startswith("#"):
            continue
        key, value = raw.split(":", 1)
        value = value.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        result[key.strip()] = value
    if not result.get("name") or not result.get("description"):
        raise ValueError("skill_frontmatter_identity")
    return result


class SkillRegistry:
    """Static MCP Skills extension registry backed by packaged skill files."""

    def __init__(self, skills_root: Path):
        self.root = Path(skills_root).resolve()
        if not self.root.is_dir():
            raise ValueError("skills_root_missing")

    @staticmethod
    def _uri(skill_name: str, relative: str = "SKILL.md") -> str:
        return f"skill://{skill_name}/{relative}"

    def _skill_dir(self, name: str) -> Path:
        path = (self.root / name).resolve()
        if self.root not in path.parents or not path.is_dir():
            raise ValueError("unknown_skill")
        return path

    def _entry(self, skill_dir: Path) -> dict[str, Any]:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            raise ValueError("skill_entrypoint_missing")
        frontmatter = _frontmatter(skill_md.read_text(encoding="utf-8"))
        name = str(frontmatter["name"])
        if name != skill_dir.name:
            raise ValueError("skill_name_mismatch")
        resources: list[dict[str, Any]] = []
        for path in sorted(p for p in skill_dir.rglob("*") if p.is_file()):
            rel = path.relative_to(skill_dir).as_posix()
            data = path.read_bytes()
            resources.append({"uri": self._uri(name, rel), "digest": _sha(data), "size": len(data)})
        return {"uri": self._uri(name), "frontmatter": frontmatter, "resources": resources}

    def list(self) -> list[dict[str, Any]]:
        return [self._entry(p) for p in sorted(self.root.iterdir()) if p.is_dir() and (p / "SKILL.md").is_file()]

    def get(self, uri: str) -> dict[str, Any]:
        parsed = urlparse(uri)
        if parsed.scheme != "skill" or not parsed.netloc or parsed.path != "/SKILL.md":
            raise ValueError("unknown_skill_uri")
        return self._entry(self._skill_dir(parsed.netloc))

    def _resolve_resource(self, uri: str) -> tuple[str, Path, str]:
        parsed = urlparse(uri)
        if parsed.scheme != "skill" or not parsed.netloc:
            raise ValueError("unknown_skill_resource")
        rel = parsed.path.lstrip("/")
        if not rel:
            raise ValueError("skill_resource_is_directory")
        posix = PurePosixPath(rel)
        if posix.is_absolute() or ".." in posix.parts:
            raise ValueError("unsafe_skill_resource")
        root = self._skill_dir(parsed.netloc)
        path = (root / Path(*posix.parts)).resolve()
        if root not in path.parents and path != root:
            raise ValueError("unsafe_skill_resource")
        if not path.is_file():
            raise ValueError("unknown_skill_resource")
        return parsed.netloc, path, rel

    def read(self, uri: str) -> dict[str, Any]:
        name, path, rel = self._resolve_resource(uri)
        data = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "text/plain"
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("binary_skill_resource_unsupported")
        return {"uri": self._uri(name, rel), "mimeType": mime, "text": text, "_digest": _sha(data), "_size": len(data)}

    def directory(self, uri: str) -> list[dict[str, Any]]:
        parsed = urlparse(uri)
        if parsed.scheme != "skill" or not parsed.netloc:
            raise ValueError("unknown_skill_directory")
        root = self._skill_dir(parsed.netloc)
        rel = parsed.path.lstrip("/")
        posix = PurePosixPath(rel or ".")
        if posix.is_absolute() or ".." in posix.parts:
            raise ValueError("unsafe_skill_directory")
        path = root if rel == "" else (root / Path(*posix.parts)).resolve()
        if path != root and root not in path.parents:
            raise ValueError("unsafe_skill_directory")
        if not path.is_dir():
            raise ValueError("unknown_skill_directory")
        out: list[dict[str, Any]] = []
        for child in sorted(path.iterdir(), key=lambda p: p.name):
            child_rel = child.relative_to(root).as_posix()
            row = {"uri": f"skill://{parsed.netloc}/{child_rel}", "name": child.name}
            row["mimeType"] = "inode/directory" if child.is_dir() else (mimetypes.guess_type(child.name)[0] or "text/plain")
            out.append(row)
        return out
