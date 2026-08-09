"""Web search tool.

Performs a web search using the DuckDuckGo Instant Answer API (no API key
required) and returns a list of results containing titles, URLs, and snippets.

For more comprehensive results the tool also accepts an optional ``engine``
parameter:

* ``"duckduckgo"`` (default) – free, no key required.
* ``"google"`` – requires ``GOOGLE_API_KEY`` and ``GOOGLE_CSE_ID`` env vars
  and the ``requests`` package.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import List, Dict

from core.interfaces.agent import Tool


def _duckduckgo_search(query: str, max_results: int) -> List[Dict[str, str]]:
    """Search via DuckDuckGo Instant Answer API (no key needed)."""
    encoded_query = urllib.parse.quote_plus(query)
    url = (
        f"https://api.duckduckgo.com/?q={encoded_query}"
        "&format=json&no_html=1&skip_disambig=1"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return [{"error": str(exc)}]

    results: List[Dict[str, str]] = []

    # Abstract (top result)
    if data.get("AbstractText"):
        results.append({
            "title": data.get("Heading", query),
            "url": data.get("AbstractURL", ""),
            "snippet": data["AbstractText"],
        })

    # Related topics
    for topic in data.get("RelatedTopics", []):
        if len(results) >= max_results:
            break
        if "Text" in topic and "FirstURL" in topic:
            results.append({
                "title": topic.get("Text", "")[:80],
                "url": topic["FirstURL"],
                "snippet": topic["Text"],
            })

    return results or [{"message": "No results found for the query."}]


def _google_search(query: str, max_results: int) -> List[Dict[str, str]]:
    """Search via Google Custom Search JSON API (requires API key)."""
    try:
        import requests  # type: ignore
    except ImportError as exc:
        raise ImportError("pip install requests") from exc

    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        raise ValueError(
            "GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables must be set "
            "to use the google search engine."
        )

    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": min(max_results, 10),
    }
    response = requests.get(
        "https://www.googleapis.com/customsearch/v1", params=params, timeout=10
    )
    response.raise_for_status()
    items = response.json().get("items", [])
    return [
        {
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        }
        for item in items
    ]


class WebSearchTool(Tool):
    """Searches the web and returns a list of results."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for a query and return a list of relevant results "
            "with titles, URLs, and snippets."
        )

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return. Defaults to 5.",
                },
                "engine": {
                    "type": "string",
                    "enum": ["duckduckgo", "google"],
                    "description": "Search engine to use. Defaults to 'duckduckgo'.",
                },
            },
            "required": ["query"],
        }

    def execute(
        self,
        query: str,
        max_results: int = 5,
        engine: str = "duckduckgo",
    ) -> str:
        if engine == "google":
            results = _google_search(query, max_results)
        else:
            results = _duckduckgo_search(query, max_results)

        lines = []
        for i, result in enumerate(results[:max_results], 1):
            if "error" in result:
                lines.append(f"Error: {result['error']}")
            elif "message" in result:
                lines.append(result["message"])
            else:
                lines.append(
                    f"{i}. {result.get('title', '')}\n"
                    f"   URL: {result.get('url', '')}\n"
                    f"   {result.get('snippet', '')}"
                )
        return "\n\n".join(lines)
