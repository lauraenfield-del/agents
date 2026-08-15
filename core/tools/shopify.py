from __future__ import annotations

import re
from urllib.parse import urlparse

from core.interfaces.agent import Tool
from core.tools.integration_common import execute_service_request


_SHOPIFY_HOST_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.myshopify\.com$")
_PRODUCT_ID_RE = re.compile(r"^[1-9][0-9]*$")


def _normalize_store_domain(store_domain: str) -> str | None:
    candidate = store_domain.strip()
    if not candidate:
        return None
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.params or parsed.query or parsed.fragment or parsed.username or parsed.password:
        return None
    if parsed.path not in {"", "/"}:
        return None
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if not _SHOPIFY_HOST_RE.fullmatch(hostname):
        return None
    return hostname


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
                "product_id": {"type": "string"},
                "payload": {"type": "object"},
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
        api_version: str = "2026-07",
        product_id: str = "",
        payload: dict | None = None,
        secret_version: str | None = None,
        timeout_seconds: float = 20,
        approved: bool = False,
    ) -> dict:
        route_map = {
            "get_orders": ("GET", f"/admin/api/{api_version}/orders.json"),
            "get_customers": ("GET", f"/admin/api/{api_version}/customers.json"),
        }
        if action == "update_product" and not approved:
            return {
                "status": "requires_approval",
                "details": "update_product is high risk and requires approved=true.",
            }
        if action == "update_product":
            method = "PUT"
            if not _PRODUCT_ID_RE.fullmatch(product_id):
                return {
                    "status": "error",
                    "details": "update_product requires a valid product_id.",
                }
            endpoint = f"/admin/api/{api_version}/products/{product_id}.json"
        else:
            method, endpoint = route_map[action]
        normalized_store_domain = _normalize_store_domain(store_domain)
        if normalized_store_domain is None:
            return {
                "status": "error",
                "details": "store_domain must be a valid Shopify hostname ending in .myshopify.com.",
            }
        url = f"https://{normalized_store_domain}{endpoint}"

        return execute_service_request(
            service_name="shopify",
            method=method,
            url=url,
            payload=payload if method != "GET" else None,
            timeout_seconds=timeout_seconds,
            secret_scope=secret_scope,
            secret_name=secret_name,
            secret_version=secret_version,
            allowed_hosts=(normalized_store_domain,),
            allowed_secret_scopes=("shopify",),
            authorization_scheme="",
            auth_header_name="X-Shopify-Access-Token",
        )
