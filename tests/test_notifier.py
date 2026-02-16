import json

from orchestrator.notifier import (
    WhatsAppNotifier,
    send_pipeline_completion_notification,
    twilio_env_template,
)


def test_notifier_from_env_disabled(monkeypatch):
    monkeypatch.delenv("WHATSAPP_NOTIFICATIONS_ENABLED", raising=False)
    assert WhatsAppNotifier.from_env() is None


def test_notifier_from_env_enabled(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_FROM", "whatsapp:+14155238886")
    monkeypatch.setenv("WHATSAPP_TO", "whatsapp:+15551234567")

    notifier = WhatsAppNotifier.from_env()
    assert notifier is not None
    assert notifier.account_sid == "AC123"


def test_send_pipeline_notification_formats_message():
    class StubNotifier:
        def __init__(self):
            self.message = None

        def send(self, message):
            self.message = message

    stub = StubNotifier()
    send_pipeline_completion_notification(
        stub,
        project_name="Game model",
        success=True,
        completed_actions=7,
        failed_actions=0,
    )
    assert "A2A task complete: Game model" in stub.message
    assert "Status: SUCCESS" in stub.message


def test_twilio_env_template_is_valid_json():
    template = twilio_env_template()
    data = json.loads(template)
    assert data["WHATSAPP_NOTIFICATIONS_ENABLED"] == "true"
    assert data["TWILIO_ACCOUNT_SID"].startswith("AC")
