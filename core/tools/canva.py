from __future__ import annotations

from core.interfaces.agent import Tool
from core.tools.integration_common import execute_service_request


class CanvaTool(Tool):
    @property
    def name(self) -> str:
        return "canva"

    @property
    def description(self) -> str:
        return "Create, update, and export Canva designs through API-driven actions."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["create_design", "update_design", "export_design"]},
                "path": {"type": "string"},
                "payload": {"type": "object"},
                "secret_scope": {"type": "string"},
                "secret_name": {"type": "string"},
                "secret_version": {"type": "string"},
                "api_base": {"type": "string"},
                "timeout_seconds": {"type": "number", "minimum": 1, "maximum": 60},
                "approved": {"type": "boolean"},
            },
            "required": ["action", "secret_scope", "secret_name"],
            "additionalProperties": False,
        }

    def execute(
        self,
        action: str,
        secret_scope: str,
        secret_name: str,
        path: str = "",
        payload: dict | None = None,
        secret_version: str | None = None,
        api_base: str = "https://api.canva.com",
        timeout_seconds: float = 20,
        approved: bool = False,
    ) -> dict:
        route_map = {
            "create_design": ("POST", "/rest/v1/designs"),
            "update_design": ("PATCH", "/rest/v1/designs"),
            "export_design": ("POST", "/rest/v1/exports"),
        }
        method, default_path = route_map[action]
        if action in {"update_design", "export_design"} and not approved:
            return {
                "status": "requires_approval",
                "details": f"{action} is high risk and requires approved=true.",
            }
        endpoint = path or default_path
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        return execute_service_request(
            service_name="canva",
            method=method,
            url=f"{api_base.rstrip('/')}{endpoint}",
            payload=payload if method != "GET" else None,
            timeout_seconds=timeout_seconds,
            secret_scope=secret_scope,
            secret_name=secret_name,
            secret_version=secret_version,
            allowed_hosts=("api.canva.com", "www.canva.com"),
        )
