from agents.notification_agent import NotificationAgent


class StubNotifier:
    def __init__(self):
        self.messages = []

    def send(self, message, to_number=None):
        self.messages.append({"message": message, "to_number": to_number})


def test_notification_agent_rejects_invalid_channel_url():
    agent = NotificationAgent(notifier=StubNotifier())
    result = agent.send_to_whatsapp_channel(
        channel_url="https://example.com/not-whatsapp",
        message="hello",
    )
    assert result.status == "FAILED"
    assert result.mode == "validation"


def test_notification_agent_sends_bridge_notification(monkeypatch):
    notifier = StubNotifier()
    monkeypatch.setenv("WHATSAPP_CHANNEL_BRIDGE_TO", "whatsapp:+15550001111")
    agent = NotificationAgent(notifier=notifier)

    result = agent.send_to_whatsapp_channel(
        channel_url="https://whatsapp.com/channel/0029Vb6UzUH5a247SNGocW26",
        message="Build complete",
    )

    assert result.status == "SENT"
    assert result.mode == "bridge_to_operator"
    assert len(notifier.messages) == 1
    assert "Channel post request" in notifier.messages[0]["message"]
