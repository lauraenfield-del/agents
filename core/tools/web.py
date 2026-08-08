"""Web-fetch tool.

Fetches the content of a URL over HTTP/HTTPS and returns the response body as
plain text.  HTML responses are converted to readable text using *html.parser*
from the standard library so no extra dependency is required.  Pass
``as_html=true`` to get raw HTML instead.

Requires: ``requests`` (already in most Python environments; add to
requirements.txt if missing).
"""
from __future__ import annotations

import html
from html.parser import HTMLParser

from core.interfaces.agent import Tool


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
                "timeout": {
                    "type": "number",
                    "description": "Request timeout in seconds. Defaults to 15.",
                },
            },
            "required": ["url"],
        }

    def execute(self, url: str, as_html: bool = False, timeout: int = 15) -> str:
        try:
            import requests  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "The 'requests' package is required for WebFetchTool. "
                "Install it with: pip install requests"
            ) from exc

        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "agents-framework/1.0"})
            response.raise_for_status()
        except requests.RequestException as exc:
            return f"Error fetching {url}: {exc}"

        content_type = response.headers.get("Content-Type", "")
        if as_html or "text/html" not in content_type:
            return response.text

        extractor = _TextExtractor()
        extractor.feed(response.text)
        return extractor.get_text()
