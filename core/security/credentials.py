from __future__ import annotations

import os
import re
from dataclasses import dataclass


_NAME_RE = re.compile(r"[^A-Z0-9_]")


class SecretResolutionError(ValueError):
    """Raised when a secret reference cannot be resolved."""


@dataclass(frozen=True)
class SecretReference:
    scope: str
    name: str
    version: str | None = None

    def env_key(self) -> str:
        scope = _sanitize(self.scope)
        name = _sanitize(self.name)
        if self.version:
            version = _sanitize(self.version)
            return f"AGENT_SECRET_{scope}_{name}_V{version}"
        return f"AGENT_SECRET_{scope}_{name}"


def _sanitize(value: str) -> str:
    normal = value.strip().upper().replace("-", "_")
    normal = _NAME_RE.sub("", normal)
    if not normal:
        raise SecretResolutionError("Secret scope/name cannot be empty.")
    return normal


class CredentialStore:
    """Environment-backed secret resolver with best-effort redaction support."""

    def __init__(self) -> None:
        self._resolved_values: set[str] = set()

    def resolve(self, scope: str, name: str, version: str | None = None) -> str:
        ref = SecretReference(scope=scope, name=name, version=version)
        value = os.getenv(ref.env_key())
        if not value:
            raise SecretResolutionError(
                f"Secret not found for scope='{scope}', name='{name}', version='{version or 'current'}'."
            )
        self._resolved_values.add(value)
        return value

    def metadata(self, scope: str, name: str, version: str | None = None) -> dict[str, str]:
        ref = SecretReference(scope=scope, name=name, version=version)
        return {
            "scope": _sanitize(ref.scope).lower(),
            "name": _sanitize(ref.name).lower(),
            "version": version or "current",
            "source": ref.env_key(),
        }

    def redact_text(self, text: str) -> str:
        redacted = text
        for secret in sorted(self._resolved_values, key=len, reverse=True):
            if secret:
                redacted = redacted.replace(secret, "***REDACTED***")
        return redacted
