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


def _validate_url_for_ssrf(url: str) -> str | None:
    """Return an error string if the URL fails SSRF validation, else None."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return "Only http and https URLs are supported."
    hostname = parsed.hostname or ""
    if _is_blocked_host(hostname):
        return "Access to localhost/private targets is not allowed."
    return None


class _SSRFSafeRedirectHandler(request.HTTPRedirectHandler):
    """Redirect handler that validates every redirect destination against SSRF rules."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        err = _validate_url_for_ssrf(newurl)
        if err:
            raise error.URLError(f"Redirect blocked (SSRF): {err}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_ssrf_safe_opener() -> request.OpenerDirector:
    """Return a urllib opener that validates every redirect against SSRF rules."""
    return request.build_opener(_SSRFSafeRedirectHandler)


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
        err = _validate_url_for_ssrf(url)
        if err:
            return {"error": "blocked_target", "details": err}

        req = request.Request(
            url,
            headers={
                "User-Agent": "agents-framework/1.0",
                "Accept": "text/html,application/json,text/plain,*/*",
            },
            method="GET",
        )
        opener = build_ssrf_safe_opener()
        try:
            with opener.open(req, timeout=20) as resp:
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
