from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers import webhooks


def _request(client_host: str | None = "198.51.100.10", xff: str | None = None):
    headers = {}
    if xff is not None:
        headers["x-forwarded-for"] = xff
    client = SimpleNamespace(host=client_host) if client_host is not None else None
    return SimpleNamespace(headers=headers, client=client)


@pytest.fixture(autouse=True)
def _reset_webhook_settings(monkeypatch):
    monkeypatch.setattr(webhooks.settings, "webhook_trust_forwarded", False)
    monkeypatch.setattr(webhooks.settings, "webhook_trusted_proxy_hops", 1)
    monkeypatch.setattr(webhooks.settings, "alertmanager_webhook_allowed_ips", "")


def test_extract_client_ip_ignores_xff_when_forwarded_not_trusted():
    request = _request(client_host="198.51.100.10", xff="spoofed, 203.0.113.7")

    assert webhooks._extract_client_ip(request) == "198.51.100.10"


def test_extract_client_ip_uses_xff_from_right_by_trusted_hops(monkeypatch):
    monkeypatch.setattr(webhooks.settings, "webhook_trust_forwarded", True)

    assert webhooks._extract_client_ip(_request(xff="203.0.113.7")) == "203.0.113.7"
    assert webhooks._extract_client_ip(_request(xff="spoofed, 203.0.113.7")) == "203.0.113.7"

    monkeypatch.setattr(webhooks.settings, "webhook_trusted_proxy_hops", 2)

    assert webhooks._extract_client_ip(_request(xff="spoofed, 203.0.113.7")) == "spoofed"


def test_extract_client_ip_falls_back_to_socket_ip_when_xff_unusable(monkeypatch):
    monkeypatch.setattr(webhooks.settings, "webhook_trust_forwarded", True)
    monkeypatch.setattr(webhooks.settings, "webhook_trusted_proxy_hops", 2)

    assert webhooks._extract_client_ip(_request(xff="203.0.113.7")) == "198.51.100.10"
    assert webhooks._extract_client_ip(_request(xff=None)) == "198.51.100.10"
    assert webhooks._extract_client_ip(_request(xff=" , ")) == "198.51.100.10"


def test_parse_allowed_networks_accepts_ips_and_cidrs_and_skips_invalid():
    networks = webhooks._parse_allowed_networks(
        "198.51.100.10, 203.0.113.0/24, 2001:db8::/32, not-an-ip"
    )

    assert [str(network) for network in networks] == [
        "198.51.100.10/32",
        "203.0.113.0/24",
        "2001:db8::/32",
    ]


def test_enforce_ip_whitelist_allows_when_config_empty(monkeypatch):
    monkeypatch.setattr(webhooks.settings, "alertmanager_webhook_allowed_ips", "")

    webhooks._enforce_ip_whitelist(_request(client_host="198.51.100.10"))


def test_enforce_ip_whitelist_allows_matching_client_ip(monkeypatch):
    monkeypatch.setattr(webhooks.settings, "alertmanager_webhook_allowed_ips", "198.51.100.0/24")

    webhooks._enforce_ip_whitelist(_request(client_host="198.51.100.10"))


def test_enforce_ip_whitelist_rejects_unmatched_client_ip(monkeypatch):
    monkeypatch.setattr(webhooks.settings, "alertmanager_webhook_allowed_ips", "203.0.113.0/24")

    with pytest.raises(HTTPException) as exc_info:
        webhooks._enforce_ip_whitelist(_request(client_host="198.51.100.10"))

    assert exc_info.value.status_code == 403


def test_enforce_ip_whitelist_rejects_unavailable_client_ip(monkeypatch):
    monkeypatch.setattr(webhooks.settings, "alertmanager_webhook_allowed_ips", "198.51.100.0/24")

    with pytest.raises(HTTPException) as exc_info:
        webhooks._enforce_ip_whitelist(_request(client_host=None))

    assert exc_info.value.status_code == 403


def test_enforce_ip_whitelist_rejects_invalid_client_ip(monkeypatch):
    monkeypatch.setattr(webhooks.settings, "alertmanager_webhook_allowed_ips", "198.51.100.0/24")

    with pytest.raises(HTTPException) as exc_info:
        webhooks._enforce_ip_whitelist(_request(client_host="not-an-ip"))

    assert exc_info.value.status_code == 403


def test_receive_alertmanager_webhook_docstring_restored():
    assert webhooks.receive_alertmanager_webhook.__doc__ is not None
    assert "接收 Prometheus AlertManager webhook" in webhooks.receive_alertmanager_webhook.__doc__
