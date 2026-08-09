"""Web-fetch tool.

Fetches the content of a URL over HTTP/HTTPS and returns the response body as
plain text.  HTML responses are converted to readable text using *html.parser*
from the standard library so no extra dependency is required.  Pass
``as_html=true`` to get raw HTML instead.

Security controls:
* Only ``http`` and ``https`` schemes are accepted.
* Requests to localhost, loopback, link-local, and private IP ranges are
  blocked by default (SSRF guard).
* Every redirect destination is validated against the same rules.
"""
from __future__ import annotations

import html
import http.client
import ipaddress
import socket
from html.parser import HTMLParser
from urllib import error, request
from urllib.parse import urlparse

from core.interfaces.agent import Tool

_LOCALHOST_NAMES: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})


def _is_blocked_host(hostname: str) -> bool:
    """Return True if *hostname* resolves to a private/loopback/reserved address."""
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


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved


def _resolve_public_endpoints(hostname: str, port: int) -> list[tuple]:
    try:
        resolved = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise error.URLError(f"Failed to resolve host '{hostname}': {exc}") from exc

    public_endpoints: list[tuple] = []
    for family, socktype, proto, canonname, sockaddr in resolved:
        ip_str = sockaddr[0]
        if not _is_blocked_ip(ip_str):
            public_endpoints.append((family, socktype, proto, canonname, sockaddr))
    return public_endpoints


def _connect_to_validated_public_endpoint(
    hostname: str,
    port: int,
    timeout: float | None,
    source_address: tuple[str, int] | None = None,
) -> socket.socket:
    endpoints = _resolve_public_endpoints(hostname, port)
    if not endpoints:
        raise error.URLError("Access to localhost/private targets is not allowed.")

    last_exc: OSError | None = None
    for family, socktype, proto, _canonname, sockaddr in endpoints:
        sock = socket.socket(family, socktype, proto)
        try:
            if timeout is not None:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as exc:
            last_exc = exc
            sock.close()
    if last_exc is None:
        raise error.URLError("Unable to establish connection.")
    raise error.URLError(f"Connection failed: {last_exc}")


def _validate_url_for_ssrf(url: str) -> str | None:
    """Return an error string if *url* fails SSRF validation, else ``None``."""
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


class _SSRFSafeHTTPConnection(http.client.HTTPConnection):
    def connect(self) -> None:
        target_host = self._tunnel_host or self.host
        target_port = getattr(self, "_tunnel_port", None) or self.port
        self.sock = _connect_to_validated_public_endpoint(
            hostname=target_host,
            port=target_port,
            timeout=self.timeout,
            source_address=self.source_address,
        )
        if self._tunnel_host:
            self._tunnel()


class _SSRFSafeHTTPSConnection(http.client.HTTPSConnection):
    def connect(self) -> None:
        target_host = self._tunnel_host or self.host
        target_port = getattr(self, "_tunnel_port", None) or self.port
        raw_sock = _connect_to_validated_public_endpoint(
            hostname=target_host,
            port=target_port,
            timeout=self.timeout,
            source_address=self.source_address,
        )
        self.sock = raw_sock
        if self._tunnel_host:
            self._tunnel()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


class _SSRFSafeHTTPHandler(request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_SSRFSafeHTTPConnection, req)


class _SSRFSafeHTTPSHandler(request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_SSRFSafeHTTPSConnection, req)


def _build_ssrf_safe_opener() -> request.OpenerDirector:
    """Return a urllib opener that validates every redirect against SSRF rules."""
    return request.build_opener(
        _SSRFSafeRedirectHandler,
        _SSRFSafeHTTPHandler,
        _SSRFSafeHTTPSHandler,
    )


class _TextExtractor(HTMLParser):
    """Minimal HTML-to-text converter (no external deps)."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_tags = {"script", "style", "head", "meta", "link"}
        self._current_skip: int = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._skip_tags:
            self._current_skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip_tags and self._current_skip:
            self._current_skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._current_skip:
            stripped = data.strip()
            if stripped:
                self._parts.append(html.unescape(stripped))

    def get_text(self) -> str:
        return "\n".join(self._parts)


class WebFetchTool(Tool):
    """Fetches a URL and returns its text content."""

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return (
            "Fetch the content of a URL and return it as plain text (or raw HTML). "
            "Useful for reading web pages, APIs, and online documents."
        )

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch.",
                },
                "as_html": {
                    "type": "boolean",
                    "description": "Return raw HTML instead of extracted text. Defaults to false.",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum characters to return. Defaults to 8000.",
                },
                "timeout": {
                    "type": "number",
                    "description": "Request timeout in seconds. Defaults to 15.",
                },
            },
            "required": ["url"],
        }

    def execute(
        self,
        url: str,
        as_html: bool = False,
        max_chars: int = 8000,
        timeout: int = 15,
    ) -> str:
        err = _validate_url_for_ssrf(url)
        if err:
            return f"Error: {err}"

        req = request.Request(
            url,
            headers={"User-Agent": "agents-framework/1.0"},
            method="GET",
        )
        opener = _build_ssrf_safe_opener()
        try:
            with opener.open(req, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read(max_chars * 4)
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            return f"Error HTTP {exc.code}: {details[:max_chars]}"
        except error.URLError as exc:
            return f"Error fetching {url}: {exc.reason}"

        text = raw.decode("utf-8", errors="replace")
        if not as_html and "text/html" in content_type:
            extractor = _TextExtractor()
            extractor.feed(text)
            text = extractor.get_text()

        return text[:max_chars]


# Backward-compatible alias
WebTool = WebFetchTool
