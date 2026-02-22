from __future__ import annotations

import json
from types import SimpleNamespace

import requests

from core_orchestrator.github_dispatch import DEFAULT_EVENT_TYPE, send_block


def _response(status: int, text: str = "") -> SimpleNamespace:
    return SimpleNamespace(status_code=status, text=text)


def test_send_block_success(monkeypatch):
    posted = []

    def fake_post(url, headers, data, timeout):
        posted.append({"url": url, "headers": headers, "data": data, "timeout": timeout})
        return _response(204, "")

    monkeypatch.setattr("core_orchestrator.github_dispatch.requests.post", fake_post)

    result = send_block(
        "acme",
        "demo",
        "token-123",
        {"coords": (1.0, 2.0), "character": "MegaMan"},
        tx_id="fixed-tx",
        max_retries=0,
    )

    assert result["success"] is True
    body = json.loads(posted[0]["data"])
    assert body["event_type"] == DEFAULT_EVENT_TYPE
    assert body["client_payload"]["coords"] == [1.0, 2.0]
    assert body["client_payload"]["tx_id"] == "fixed-tx"
    assert posted[0]["headers"]["Authorization"] == "token token-123"


def test_send_block_retries_on_server_error(monkeypatch):
    calls = []
    responses = iter([_response(500, "nope"), _response(204, "")])

    def fake_post(url, headers, data, timeout):
        calls.append(url)
        return next(responses)

    sleep_intervals = []

    def fake_sleep(interval):
        sleep_intervals.append(interval)

    monkeypatch.setattr("core_orchestrator.github_dispatch.requests.post", fake_post)
    monkeypatch.setattr("core_orchestrator.github_dispatch.time.sleep", fake_sleep)

    result = send_block(
        "acme",
        "demo",
        "token-123",
        {"coords": [0.1, 0.2]},
        tx_id="retryable",
        max_retries=2,
        backoff_base=0.25,
    )

    assert result["success"] is True
    assert len(calls) == 2
    assert sleep_intervals == [0.25]


def test_client_error_does_not_retry(monkeypatch):
    calls = []

    def fake_post(url, headers, data, timeout):
        calls.append(url)
        return _response(401, "bad token")

    sleep_intervals = []
    monkeypatch.setattr("core_orchestrator.github_dispatch.requests.post", fake_post)
    monkeypatch.setattr("core_orchestrator.github_dispatch.time.sleep", sleep_intervals.append)

    result = send_block(
        "acme",
        "demo",
        "token-123",
        {"character": "Zero"},
        tx_id="client-error",
        max_retries=3,
    )

    assert result["success"] is False
    assert result["status_code"] == 401
    assert calls == [
        "https://api.github.com/repos/acme/demo/dispatches",
    ]
    assert not sleep_intervals


def test_network_error_reports_failure(monkeypatch):
    payloads = []

    def fake_post(url, headers, data, timeout):
        payloads.append(json.loads(data)["client_payload"])
        raise requests.RequestException("network down")

    monkeypatch.setattr("core_orchestrator.github_dispatch.requests.post", fake_post)
    monkeypatch.setattr("core_orchestrator.github_dispatch.time.sleep", lambda _: None)

    result = send_block(
        "acme",
        "demo",
        "token-123",
        {"coords": 42},
        tx_id="network-failure",
        max_retries=2,
        backoff_base=0.1,
    )

    assert result["success"] is False
    assert result["status_code"] is None
    assert len(payloads) == 3
    assert all(payload["coords"] == [42] for payload in payloads)
    assert all(payload["tx_id"] == "network-failure" for payload in payloads)
