from __future__ import annotations

import json
from urllib import error, request
from urllib.parse import urlparse

from core.security.credentials import CredentialStore, SecretResolutionError
from core.tools.web import _SSRFSafeHTTPHandler, _SSRFSafeHTTPSHandler, _validate_url_for_ssrf


def _host_allowed(hostname: str, allowed_hosts: tuple[str, ...]) -> bool:
    host = (hostname or "").lower()
    for allowed in allowed_hosts:
        allowed_l = allowed.lower()
        if host == allowed_l:
            return True
    return False


def _validate_service_url(url: str, service_name: str, allowed_hosts: tuple[str, ...]) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "Only http/https URLs are supported."
    if not _host_allowed(parsed.hostname or "", allowed_hosts):
        return f"Host '{parsed.hostname or ''}' is not in the {service_name} allow-list."
    return _validate_url_for_ssrf(url)


class _AllowedHostsRedirectHandler(request.HTTPRedirectHandler):
    def __init__(self, service_name: str, allowed_hosts: tuple[str, ...]) -> None:
        super().__init__()
        self._service_name = service_name
        self._allowed_hosts = allowed_hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        err = _validate_service_url(newurl, self._service_name, self._allowed_hosts)
        if err:
            raise error.URLError(f"Redirect blocked: {err}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _build_service_opener(service_name: str, allowed_hosts: tuple[str, ...]) -> request.OpenerDirector:
    return request.build_opener(
        _AllowedHostsRedirectHandler(service_name, allowed_hosts),
        _SSRFSafeHTTPHandler(),
        _SSRFSafeHTTPSHandler(),
    )


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
    url_err = _validate_service_url(url, service_name, allowed_hosts)
    if url_err:
        return {"status": "error", "details": url_err}

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
    opener = _build_service_opener(service_name, allowed_hosts)
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
