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
    def __init__(self):
        self.request = None

    def open(self, req, *_args, **_kwargs):
        self.request = req
        return _DummyResponse()


def test_sendblue_tool_uses_secret_reference(monkeypatch):
    monkeypatch.setenv("AGENT_SECRET_SENDBLUE_PRIMARY_ID", "sb-key-id")
    monkeypatch.setenv("AGENT_SECRET_SENDBLUE_PRIMARY_SECRET", "sb-secret")
    opener = _DummyOpener()
    monkeypatch.setattr("core.tools.integration_common._build_service_opener", lambda *_args, **_kwargs: opener)

    tool = SendblueTool()
    result = tool.execute(
        action="list_threads",
        secret_scope="sendblue",
        key_id_secret_name="primary_id",
        secret_name="primary_secret",
    )
    assert result["status"] == "ok"
    assert result["service"] == "sendblue"
    assert result["credential"]["name"] == "primary_secret"
    headers = {name.lower(): value for name, value in opener.request.header_items()}
    assert headers["sb-api-key-id"] == "sb-key-id"
    assert headers["sb-api-secret-key"] == "sb-secret"
    assert "authorization" not in headers


def test_sendblue_send_message_requires_explicit_approval():
    tool = SendblueTool()
    result = tool.execute(
        action="send_message",
        secret_scope="sendblue",
        key_id_secret_name="primary_id",
        secret_name="primary_secret",
    )

    assert result["status"] == "requires_approval"


def test_sendblue_rejects_non_https_api_base():
    tool = SendblueTool()
    result = tool.execute(
        action="list_threads",
        secret_scope="sendblue",
        key_id_secret_name="primary_id",
        secret_name="primary_secret",
        api_base="http://api.sendblue.co",
    )

    assert result["status"] == "error"
    assert result["details"] == "Only HTTPS URLs are supported for authenticated service requests."


def test_sendblue_rejects_unknown_action():
    tool = SendblueTool()
    result = tool.execute(
        action="unknown",
        secret_scope="sendblue",
        key_id_secret_name="primary_id",
        secret_name="primary_secret",
    )

    assert result["status"] == "error"
    assert result["details"] == "Unsupported Sendblue action: unknown."


def test_shopify_update_requires_explicit_approval():
    tool = ShopifyTool()
    result = tool.execute(
        action="update_product",
        store_domain="example.myshopify.com",
        secret_scope="shopify",
        secret_name="main",
    )
    assert result["status"] == "requires_approval"


def test_shopify_update_requires_product_id_after_approval():
    tool = ShopifyTool()
    result = tool.execute(
        action="update_product",
        store_domain="example.myshopify.com",
        secret_scope="shopify",
        secret_name="main",
        approved=True,
    )

    assert result["status"] == "error"
    assert result["details"] == "update_product requires a valid product_id."


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
    assert captured["url"] == "https://example.myshopify.com/admin/api/2026-07/orders.json"
    assert captured["allowed_hosts"] == ("example.myshopify.com",)


def test_shopify_rejects_wrong_secret_scope():
    tool = ShopifyTool()
    result = tool.execute(
        action="get_orders",
        store_domain="example.myshopify.com",
        secret_scope="sendblue",
        secret_name="main",
    )

    assert result["status"] == "error"
    assert result["details"] == "Secret scope 'sendblue' is not allowed for shopify."


def test_shopify_rejects_unknown_action():
    tool = ShopifyTool()
    result = tool.execute(
        action="unknown",
        store_domain="example.myshopify.com",
        secret_scope="shopify",
        secret_name="main",
    )

    assert result["status"] == "error"
    assert result["details"] == "Unsupported Shopify action: unknown."


def test_shopify_rejects_non_shopify_domain():
    tool = ShopifyTool()
    result = tool.execute(
        action="get_orders",
        store_domain="https://example.com/",
        secret_scope="shopify",
        secret_name="main",
    )

    assert result["status"] == "error"
    assert result["details"] == "store_domain must be a valid Shopify hostname ending in .myshopify.com."


def test_shopify_rejects_lookalike_domain():
    tool = ShopifyTool()
    result = tool.execute(
        action="get_orders",
        store_domain="example.myshopify.com.evil.test",
        secret_scope="shopify",
        secret_name="main",
    )

    assert result["status"] == "error"
    assert result["details"] == "store_domain must be a valid Shopify hostname ending in .myshopify.com."


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


def test_canva_update_requires_valid_design_id_after_approval():
    tool = CanvaTool()
    result = tool.execute(
        action="update_design",
        secret_scope="canva",
        secret_name="primary",
        approved=True,
    )

    assert result["status"] == "error"
    assert result["details"] == "update_design requires a valid design_id."


def test_canva_rejects_unknown_action():
    tool = CanvaTool()
    result = tool.execute(
        action="unknown",
        secret_scope="canva",
        secret_name="primary",
    )

    assert result["status"] == "error"
    assert result["details"] == "Unsupported Canva action: unknown."
