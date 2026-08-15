from urllib import error, request

from core.tools.canva import CanvaTool
from core.tools.integration_common import _AllowedHostsRedirectHandler, _host_allowed
from core.tools.sendblue import SendblueTool
from core.tools.shopify import ShopifyTool


class _DummyResponse:
    status = 200
    headers = {"Content-Type": "application/json"}

    def __init__(self, content: bytes = b'{"ok": true}'):
        self._content = content

    def read(self):
        return self._content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyOpener:
    def open(self, *_args, **_kwargs):
        return _DummyResponse()


def test_sendblue_tool_uses_secret_reference(monkeypatch):
    monkeypatch.setenv("AGENT_SECRET_SENDBLUE_PRIMARY", "sb-token")
    monkeypatch.setattr("core.tools.integration_common._build_service_opener", lambda *_args, **_kwargs: _DummyOpener())

    tool = SendblueTool()
    result = tool.execute(action="list_threads", secret_scope="sendblue", secret_name="primary")
    assert result["status"] == "ok"
    assert result["service"] == "sendblue"
    assert result["credential"]["name"] == "primary"


def test_shopify_update_requires_explicit_approval():
    tool = ShopifyTool()
    result = tool.execute(
        action="update_product",
        store_domain="example.myshopify.com",
        secret_scope="shopify",
        secret_name="main",
    )
    assert result["status"] == "requires_approval"


def test_shopify_normalizes_store_domain_before_request(monkeypatch):
    captured = {}

    def fake_execute_service_request(**kwargs):
        captured.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr("core.tools.shopify.execute_service_request", fake_execute_service_request)

    tool = ShopifyTool()
    result = tool.execute(
        action="get_orders",
        store_domain="https://Example.MyShopify.com/",
        secret_scope="shopify",
        secret_name="main",
    )

    assert result["status"] == "ok"
    assert captured["url"] == "https://example.myshopify.com/admin/api/2025-01/orders.json"
    assert captured["allowed_hosts"] == ("example.myshopify.com",)


def test_shopify_rejects_non_shopify_domain():
    tool = ShopifyTool()
    result = tool.execute(
        action="get_orders",
        store_domain="https://example.com/",
        secret_scope="shopify",
        secret_name="main",
    )

    assert result["status"] == "error"
    assert ".myshopify.com" in result["details"]


def test_shopify_rejects_lookalike_domain():
    tool = ShopifyTool()
    result = tool.execute(
        action="get_orders",
        store_domain="example.myshopify.com.evil.test",
        secret_scope="shopify",
        secret_name="main",
    )

    assert result["status"] == "error"
    assert ".myshopify.com" in result["details"]


def test_integration_redirect_handler_blocks_disallowed_host():
    handler = _AllowedHostsRedirectHandler("shopify", ("example.myshopify.com",))
    req = request.Request("https://example.myshopify.com/admin/api/2025-01/orders.json")

    try:
        handler.redirect_request(req, None, 302, "Found", {}, "https://example.com/redirect")
    except error.URLError as exc:
        assert "allow-list" in str(exc.reason)
    else:
        raise AssertionError("Expected redirect to a non-allow-listed host to be blocked.")


def test_host_allow_list_requires_exact_match():
    assert _host_allowed("api.sendblue.co", ("api.sendblue.co",))
    assert not _host_allowed("evil.api.sendblue.co", ("api.sendblue.co",))


def test_canva_export_requires_explicit_approval():
    tool = CanvaTool()
    result = tool.execute(
        action="export_design",
        secret_scope="canva",
        secret_name="primary",
    )
    assert result["status"] == "requires_approval"
