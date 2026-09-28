from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse


class DeploymentMode(str, Enum):
    LOCAL = "local"
    NODE = "node"
    SERVER = "server"


@dataclass(frozen=True, slots=True)
class ProductionConfig:
    mode: DeploymentMode
    state_dir: Path
    fail_closed: bool = True
    allow_dev_auth: bool = False
    public_base_url: str | None = None
    otlp_endpoint: str | None = None
    max_workers: int = 8

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        if not self.fail_closed:
            errors.append("production:fail_closed_required")
        if self.allow_dev_auth and self.mode != DeploymentMode.LOCAL:
            errors.append("production:dev_auth_forbidden")
        if not 1 <= self.max_workers <= 512:
            errors.append("production:max_workers")
        for label, value in (("public_base_url", self.public_base_url), ("otlp_endpoint", self.otlp_endpoint)):
            if value:
                u = urlparse(value)
                if u.scheme not in {"https", "http"} or not u.netloc:
                    errors.append(f"production:{label}_invalid")
                if self.mode != DeploymentMode.LOCAL and u.scheme != "https":
                    errors.append(f"production:{label}_https_required")
        return tuple(errors)
