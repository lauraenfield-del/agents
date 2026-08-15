from core.tools.canva import CanvaTool
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
    monkeypatch.setattr("core.tools.integration_common._build_ssrf_safe_opener", lambda: _DummyOpener())

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


def test_canva_export_requires_explicit_approval():
    tool = CanvaTool()
    result = tool.execute(
        action="export_design",
        secret_scope="canva",
        secret_name="primary",
    )
    assert result["status"] == "requires_approval"
