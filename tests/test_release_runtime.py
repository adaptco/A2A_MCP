from __future__ import annotations

from fastapi.testclient import TestClient

import mcp_server
from orchestrator.webhook import app


class DummyResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_webhook_healthz_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get('/healthz')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_trigger_new_research_uses_env_api_base_url(monkeypatch):
    seen = {}

    def fake_post(url, params, timeout):
        seen['url'] = url
        seen['params'] = params
        seen['timeout'] = timeout
        return DummyResponse({'queued': True})

    monkeypatch.setenv('MCP_API_BASE_URL', 'http://middleware_api:9000')
    monkeypatch.setenv('MCP_API_TIMEOUT_SECONDS', '7')
    monkeypatch.setattr(mcp_server.requests, 'post', fake_post)

    payload = mcp_server.trigger_new_research('run integration checks')

    assert payload == {'queued': True}
    assert seen['url'] == 'http://middleware_api:9000/orchestrate'
    assert seen['params'] == {'user_query': 'run integration checks'}
    assert seen['timeout'] == 7.0
