from __future__ import annotations

from core.interfaces.agent import Tool
from core.tools.integration_common import execute_service_request


class SendblueTool(Tool):
    @property
    def name(self) -> str:
        return "sendblue"

    @property
    def description(self) -> str:
        return "Send messages and manage contact-related operations through Sendblue."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["send_message", "list_threads", "get_contact"]},
                "path": {"type": "string"},
                "payload": {"type": "object"},
                "secret_scope": {"type": "string"},
                "secret_name": {"type": "string"},
                "secret_version": {"type": "string"},
                "api_base": {"type": "string"},
                "timeout_seconds": {"type": "number", "minimum": 1, "maximum": 60},
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
        api_base: str = "https://api.sendblue.co",
        timeout_seconds: float = 20,
    ) -> dict:
        route_map = {
            "send_message": ("POST", "/api/send-message"),
            "list_threads": ("GET", "/api/threads"),
            "get_contact": ("GET", "/api/contacts"),
        }
        method, default_path = route_map[action]
        endpoint = path or default_path
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        return execute_service_request(
            service_name="sendblue",
            method=method,
            url=f"{api_base.rstrip('/')}{endpoint}",
            payload=payload if method != "GET" else None,
            timeout_seconds=timeout_seconds,
            secret_scope=secret_scope,
            secret_name=secret_name,
            secret_version=secret_version,
            allowed_hosts=("api.sendblue.co",),
        )
