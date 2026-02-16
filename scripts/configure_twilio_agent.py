"""Bootstrap local Twilio/WhatsApp env keys for NotificationAgent."""

from __future__ import annotations

from pathlib import Path


DEFAULTS = {
    "WHATSAPP_NOTIFICATIONS_ENABLED": "true",
    "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "TWILIO_AUTH_TOKEN": "replace_me",
    "WHATSAPP_FROM": "whatsapp:+14155238886",
    "WHATSAPP_TO": "whatsapp:+15551234567",
    "WHATSAPP_CHANNEL_BRIDGE_TO": "whatsapp:+15551234567",
}


def parse_env(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k, v = stripped.split("=", 1)
        data[k.strip()] = v.strip()
    return data


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"

    existing_text = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    existing = parse_env(existing_text)

    lines: list[str] = []
    if existing_text:
        lines.append(existing_text.rstrip("\n"))

    inserted = 0
    for key, value in DEFAULTS.items():
        if key in existing:
            continue
        lines.append(f"{key}={value}")
        inserted += 1

    output = "\n".join(lines).strip() + "\n"
    env_path.write_text(output, encoding="utf-8")
    print(f"Updated {env_path} (inserted={inserted}, existing={len(DEFAULTS)-inserted})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
