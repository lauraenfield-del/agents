from __future__ import annotations

import json
from urllib import error, request
from urllib.parse import urlparse

from core.security.credentials import CredentialStore, SecretResolutionError
from core.tools.web import _validate_url_for_ssrf, _build_ssrf_safe_opener


def _host_allowed(hostname: str, allowed_hosts: tuple[str, ...]) -> bool:
    host = (hostname or "").lower()
    for allowed in allowed_hosts:
        allowed_l = allowed.lower()
        if host == allowed_l or host.endswith(f".{allowed_l}"):
            return True
    return False


def execute_service_request(
    *,
    service_name: str,
    method: str,
    url: str,
    payload: dict | None,
    timeout_seconds: float,
    secret_scope: str,
    secret_name: str,
    secret_version: str | None,
    allowed_hosts: tuple[str, ...],
    extra_headers: dict[str, str] | None = None,
    authorization_scheme: str = "Bearer",
    auth_header_name: str = "Authorization",
) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return {"status": "error", "details": "Only http/https URLs are supported."}
    if not _host_allowed(parsed.hostname or "", allowed_hosts):
        return {
            "status": "error",
            "details": f"Host '{parsed.hostname or ''}' is not in the {service_name} allow-list.",
        }
    ssrf_err = _validate_url_for_ssrf(url)
    if ssrf_err:
        return {"status": "error", "details": ssrf_err}

    store = CredentialStore()
    try:
        api_token = store.resolve(secret_scope, secret_name, version=secret_version)
    except SecretResolutionError as exc:
        return {"status": "error", "details": str(exc)}

    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    auth_value = f"{authorization_scheme} {api_token}".strip() if authorization_scheme else api_token
    headers = {
        auth_header_name: auth_value,
        "Content-Type": "application/json",
        "User-Agent": "agents-framework/1.0",
    }
    if extra_headers:
        headers.update(extra_headers)

    req = request.Request(url=url, method=method.upper(), headers=headers, data=body)
    from core.tools.web import (
        _SSRFSafeHTTPHandler,
        _SSRFSafeHTTPSHandler,
        _SSRFSafeRedirectHandler,
    )

    class _AllowListedRedirectHandler(_SSRFSafeRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            parsed_redirect = urlparse(newurl)
            if not _host_allowed(parsed_redirect.hostname or "", allowed_hosts):
                raise error.URLError(
                    f"Redirect blocked: host '{parsed_redirect.hostname or ''}' is not in the {service_name} allow-list."
                )
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = request.build_opener(
        _AllowListedRedirectHandler,
        _SSRFSafeHTTPHandler,
        _SSRFSafeHTTPSHandler,
    )
    try:
        with opener.open(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data = raw
            if "application/json" in resp.headers.get("Content-Type", ""):
                try:
                    data = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    pass
            return {
                "status": "ok",
                "service": service_name,
                "http_status": resp.status,
                "credential": store.metadata(secret_scope, secret_name, secret_version),
                "result": data,
            }
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        return {
            "status": "error",
            "service": service_name,
            "http_status": exc.code,
            "details": store.redact_text(details[:2000]),
            "credential": store.metadata(secret_scope, secret_name, secret_version),
        }
    except error.URLError as exc:
        details = str(exc.reason)
        return {
            "status": "error",
            "service": service_name,
            "details": store.redact_text(details),
            "credential": store.metadata(secret_scope, secret_name, secret_version),
        }
