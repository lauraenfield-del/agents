import json
import os
from typing import Any
from urllib import error, request

from core.interfaces.agent import Model


class OpenAICompatibleModel(Model):
    def __init__(
        self,
        model_name: str | None = None,
        api_base: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 45.0,
    ):
        self.model_name = model_name or os.getenv("AGENTS_MODEL_NAME", "gpt-4.1-mini")
        self.api_base = (api_base or os.getenv("AGENTS_MODEL_API_BASE", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("AGENTS_MODEL_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError(
                "No model API key configured. Set AGENTS_MODEL_API_KEY or OPENAI_API_KEY to enable live model generation."
            )

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }

        req = request.Request(
            f"{self.api_base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                body = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Model request failed with HTTP {exc.code}: {details}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Model request failed: {exc.reason}") from exc

        try:
            parsed: dict[str, Any] = json.loads(body)
            content = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("Model response was malformed and could not be parsed.") from exc

        if not isinstance(content, str):
            raise RuntimeError("Model response content was not text.")

        return content.strip()
