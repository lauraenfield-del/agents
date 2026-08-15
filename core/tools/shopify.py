from __future__ import annotations

from core.interfaces.agent import Tool
from core.tools.integration_common import execute_service_request


class ShopifyTool(Tool):
    @property
    def name(self) -> str:
        return "shopify"

    @property
    def description(self) -> str:
        return "Read and update Shopify store resources through the Admin API."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["get_orders", "get_customers", "update_product"],
                },
                "store_domain": {"type": "string"},
                "api_version": {"type": "string"},
                "payload": {"type": "object"},
                "path": {"type": "string"},
                "secret_scope": {"type": "string"},
                "secret_name": {"type": "string"},
                "secret_version": {"type": "string"},
                "timeout_seconds": {"type": "number", "minimum": 1, "maximum": 60},
                "approved": {"type": "boolean"},
            },
            "required": ["action", "store_domain", "secret_scope", "secret_name"],
            "additionalProperties": False,
        }

    def execute(
        self,
        action: str,
        store_domain: str,
        secret_scope: str,
        secret_name: str,
        api_version: str = "2025-01",
        payload: dict | None = None,
        path: str = "",
        secret_version: str | None = None,
        timeout_seconds: float = 20,
        approved: bool = False,
    ) -> dict:
        route_map = {
            "get_orders": ("GET", f"/admin/api/{api_version}/orders.json"),
            "get_customers": ("GET", f"/admin/api/{api_version}/customers.json"),
            "update_product": ("PUT", f"/admin/api/{api_version}/products.json"),
        }
        method, default_path = route_map[action]
        if action == "update_product" and not approved:
            return {
                "status": "requires_approval",
                "details": "update_product is high risk and requires approved=true.",
            }
        endpoint = path or default_path
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        clean_domain = store_domain.strip()
        clean_domain = clean_domain.removeprefix("https://").removeprefix("http://").rstrip("/")
        clean_domain = clean_domain.split("/", 1)[0]
        if not clean_domain.lower().endswith(".myshopify.com"):
            return {
                "status": "error",
                "details": "store_domain must be a *.myshopify.com domain for the Shopify Admin API.",
            }

        url = f"https://{clean_domain}{endpoint}"

        return execute_service_request(
            service_name="shopify",
            method=method,
            url=url,
            payload=payload if method != "GET" else None,
            timeout_seconds=timeout_seconds,
            secret_scope=secret_scope,
            secret_name=secret_name,
            secret_version=secret_version,
            allowed_hosts=(clean_domain,),
            authorization_scheme="",
            auth_header_name="X-Shopify-Access-Token",
        )
