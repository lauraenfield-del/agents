import html
import re
from urllib import error, request

from core.interfaces.agent import Tool


class WebTool(Tool):
    @property
    def name(self) -> str:
        return "web"

    @property
    def description(self) -> str:
        return "Fetches web pages over HTTP(S) and returns text content for reading."

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "max_chars": {"type": "integer", "minimum": 256, "maximum": 50000},
            },
            "required": ["url"],
            "additionalProperties": False,
        }

    def execute(self, url: str, max_chars: int = 8000):
        req = request.Request(
            url,
            headers={
                "User-Agent": "agents-framework/1.0",
                "Accept": "text/html,application/json,text/plain,*/*",
            },
            method="GET",
        )
        try:
            with request.urlopen(req, timeout=20) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read()
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            return {"error": f"HTTP {exc.code}", "details": details[:max_chars]}
        except error.URLError as exc:
            return {"error": "network_error", "details": str(exc.reason)}

        text = raw.decode("utf-8", errors="replace")
        if "text/html" in content_type:
            text = self._html_to_text(text)

        return {
            "url": url,
            "content_type": content_type,
            "text": text[:max_chars],
        }

    def _html_to_text(self, html_text: str) -> str:
        no_script = re.sub(r"<script[\s\S]*?</script>", " ", html_text, flags=re.IGNORECASE)
        no_style = re.sub(r"<style[\s\S]*?</style>", " ", no_script, flags=re.IGNORECASE)
        no_tags = re.sub(r"<[^>]+>", " ", no_style)
        unescaped = html.unescape(no_tags)
        normalized = re.sub(r"\s+", " ", unescaped)
        return normalized.strip()
