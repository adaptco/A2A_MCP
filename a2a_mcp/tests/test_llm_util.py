import pytest

from orchestrator.llm_util import LLMService


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.ok = 200 <= status_code < 300
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_llm_service_falls_back_on_unsupported_model(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_ENDPOINT", "https://example.invalid/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "codestral-latest")
    monkeypatch.setenv("LLM_FALLBACK_MODELS", "gpt-4o-mini")

    calls = []

    def fake_post(_endpoint, headers=None, json=None, timeout=None):
        calls.append(json["model"])
        if json["model"] == "codestral-latest":
            return _Response(
                400,
                {"error": {"message": "The requested model is not supported."}},
            )
        return _Response(
            200,
            {"choices": [{"message": {"content": "ok"}}]},
        )

    monkeypatch.setattr("requests.post", fake_post)
    svc = LLMService()
    out = svc.call_llm("hello")
    assert out == "ok"
    assert calls == ["codestral-latest", "gpt-4o-mini"]


def test_llm_service_errors_when_all_models_unsupported(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_ENDPOINT", "https://example.invalid/v1/chat/completions")
    monkeypatch.setenv("LLM_MODEL", "m1")
    monkeypatch.setenv("LLM_FALLBACK_MODELS", "m2")

    def fake_post(_endpoint, headers=None, json=None, timeout=None):
        return _Response(
            400,
            {"error": {"message": "The requested model is not supported."}},
        )

    monkeypatch.setattr("requests.post", fake_post)
    svc = LLMService()
    with pytest.raises(RuntimeError, match="No supported model found"):
        svc.call_llm("hello")
