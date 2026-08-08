import html
import ipaddress
import re
import socket
from urllib import error, request
from urllib.parse import urlparse

from core.interfaces.agent import Tool

_LOCALHOST_NAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


def _is_blocked_host(hostname: str) -> bool:
    if hostname in _LOCALHOST_NAMES or hostname.endswith(".localhost"):
        return True
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except ValueError:
        pass
    try:
        resolved = socket.getaddrinfo(hostname, None)
        for _family, _type, _proto, _canonname, sockaddr in resolved:
            ip_str = sockaddr[0]
            try:
                addr = ipaddress.ip_address(ip_str)
                if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
                    return True
            except ValueError:
                pass
    except OSError:
        pass
    return False


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
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"error": "invalid_scheme", "details": "Only http and https URLs are supported."}
        hostname = parsed.hostname or ""
        if _is_blocked_host(hostname):
            return {"error": "blocked_target", "details": "Access to localhost targets is not allowed."}

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
                raw = resp.read(max_chars * 4)
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
        no_script = re.sub(
            r"<script\b[\s\S]*?</script(?:\s+[^>]*)?\s*>",
            " ",
            html_text,
            flags=re.IGNORECASE,
        )
        no_style = re.sub(
            r"<style\b[\s\S]*?</style(?:\s+[^>]*)?\s*>",
            " ",
            no_script,
            flags=re.IGNORECASE,
        )
        no_tags = re.sub(r"<[^>]+>", " ", no_style)
        unescaped = html.unescape(no_tags)
        normalized = re.sub(r"\s+", " ", unescaped)
        return normalized.strip()
