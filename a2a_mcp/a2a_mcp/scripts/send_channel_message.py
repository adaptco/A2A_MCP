"""CLI helper to send a WhatsApp channel update request via NotificationAgent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repository root is importable when script is invoked directly.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.notification_agent import NotificationAgent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--channel-url",
        default="https://whatsapp.com/channel/0029Vb6UzUH5a247SNGocW26",
    )
    parser.add_argument("--message", required=True)
    args = parser.parse_args()

    agent = NotificationAgent()
    result = agent.send_to_whatsapp_channel(
        channel_url=args.channel_url,
        message=args.message,
    )
    print(
        f"status={result.status} mode={result.mode} detail={result.detail}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
