import pytest

from core.security.credentials import CredentialStore, SecretResolutionError


def test_credential_store_resolves_current_secret(monkeypatch):
    monkeypatch.setenv("AGENT_SECRET_SEND_BLUE_PRIMARY", "secret-token")
    store = CredentialStore()
    value = store.resolve("send-blue", "primary")
    assert value == "secret-token"


def test_credential_store_resolves_versioned_secret(monkeypatch):
    monkeypatch.setenv("AGENT_SECRET_SHOPIFY_MAIN_V2", "token-v2")
    store = CredentialStore()
    value = store.resolve("shopify", "main", version="2")
    assert value == "token-v2"


def test_credential_store_redacts_resolved_values(monkeypatch):
    monkeypatch.setenv("AGENT_SECRET_CANVA_PRIMARY", "super-secret")
    store = CredentialStore()
    store.resolve("canva", "primary")
    assert store.redact_text("token=super-secret") == "token=***REDACTED***"


def test_credential_store_raises_for_missing_secret():
    store = CredentialStore()
    with pytest.raises(SecretResolutionError, match="Secret not found"):
        store.resolve("sendblue", "missing")
