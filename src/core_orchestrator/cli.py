"""Command line interface for the orchestrator."""
from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Sequence

from .databases import OrganizeSentinel
from .parsers.discord import DiscordParser
from .router import Router
from .sinks import GoogleCalendarSink, NotionSink, ShopifySink
from .world_model import WorldModelIngress

_LOG_FORMAT = "%(levelname)s | %(name)s | %(message)s"


def _load_messages(path: Path) -> Sequence[dict]:
    payload = json.loads(path.read_text())
    if isinstance(payload, dict):
        messages = payload.get("messages", [])
    else:
        messages = payload
    if not isinstance(messages, Sequence):
        raise TypeError("Input payload must be a sequence of message objects")
    return messages


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Route Discord events to downstream sinks")
    parser.add_argument("--input", type=Path, help="Path to a JSON file containing Discord messages")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use built-in demo payloads instead of reading an input file",
    )
    parser.add_argument(
        "--channel",
        dest="channels",
        action="append",
        help="Only process messages originating from the given channel (can be used multiple times)",
    )
    parser.add_argument("--limit", type=int, help="Maximum number of events to process in this run")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute sink deliveries. Without this flag the orchestrator only logs what it would do.",
    )
    parser.add_argument(
        "--sinks",
        nargs="+",
        choices=["notion", "google-calendar", "shopify"],
        help="Restrict execution to the provided sinks. Defaults to all sinks.",
    )
    parser.add_argument(
        "--notion-database",
        default=os.getenv("NOTION_DATABASE_ID"),
        help="Override the Notion database id (defaults to NOTION_DATABASE_ID env variable)",
    )
    parser.add_argument(
        "--calendar-id",
        default=os.getenv("GOOGLE_CALENDAR_ID"),
        help="Override the Google Calendar id (defaults to GOOGLE_CALENDAR_ID env variable)",
    )
    parser.add_argument(
        "--shopify-store",
        default=os.getenv("SHOPIFY_STORE_DOMAIN"),
        help="Override the Shopify store domain (defaults to SHOPIFY_STORE_DOMAIN env variable)",
    )
    parser.add_argument(
        "--default-duration",
        type=int,
        default=60,
        help="Fallback duration in minutes for calendar events (defaults to 60)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    default_repo = os.getenv("SSOT_REPO_PATH")
    default_repo_path = Path(default_repo) if default_repo else Path("adaptco-ssot")
    parser.add_argument(
        "--ssot-repo",
        type=Path,
        default=default_repo_path,
        help="Path to the repository that should store the SSOT snapshot (defaults to SSOT_REPO_PATH)",
    )
    parser.add_argument(
        "--ssot-database",
        default=os.getenv("SSOT_DATABASE_FILE", "data/core-orchestrator/events.json"),
        help="Relative path within the SSOT repo for the snapshot JSON file",
    )
    parser.add_argument(
        "--disable-ssot",
        action="store_true",
        help="Skip writing SSOT snapshots",
    )
    parser.add_argument(
        "--disable-world-model-ingress",
        action="store_true",
        help="Disable world-model ingress embedding and gating",
    )
    parser.add_argument(
        "--world-model-threshold",
        type=float,
        default=0.45,
        help="Normalized dot-product threshold used by ingress gating",
    )
    return parser


def _build_router(args: argparse.Namespace) -> Router:
    dry_run = not args.apply
    selected_sinks = set(args.sinks or ["notion", "google-calendar", "shopify"])

    sinks = []
    if "notion" in selected_sinks:
        sinks.append(
            NotionSink(
                database_id=args.notion_database or os.getenv("NOTION_DATABASE_ID", "demo-database"),
                api_token=os.getenv("NOTION_API_TOKEN"),
                dry_run=dry_run,
            )
        )
    if "google-calendar" in selected_sinks:
        sinks.append(
            GoogleCalendarSink(
                calendar_id=args.calendar_id or os.getenv("GOOGLE_CALENDAR_ID", "demo-calendar"),
                api_token=os.getenv("GOOGLE_API_TOKEN"),
                default_duration_minutes=args.default_duration,
                dry_run=dry_run,
            )
        )
    if "shopify" in selected_sinks:
        sinks.append(
            ShopifySink(
                store_domain=args.shopify_store or os.getenv("SHOPIFY_STORE_DOMAIN", "demo.myshopify.com"),
                access_token=os.getenv("SHOPIFY_ACCESS_TOKEN"),
                dry_run=dry_run,
            )
        )

    messages: Sequence[dict]
    if args.demo or not args.input:
        messages = DiscordParser.demo_messages()
    else:
        messages = _load_messages(args.input)
    parser = DiscordParser(messages, channel_whitelist=args.channels)

    sentinel = None
    if not args.disable_ssot:
        repo_path = args.ssot_repo or os.getenv("SSOT_REPO_PATH") or Path("adaptco-ssot")
        database_path = args.ssot_database or os.getenv("SSOT_DATABASE_FILE") or "data/core-orchestrator/events.json"
        if repo_path:
            sentinel = OrganizeSentinel(repo_path=repo_path, relative_path=database_path)

    ingress = None
    if not args.disable_world_model_ingress:
        ingress = WorldModelIngress(
            {
                "agent-planner": [1.0] + [0.0] * 15,
                "agent-executor": [0.0, 1.0] + [0.0] * 14,
                "agent-observer": [0.0, 0.0, 1.0] + [0.0] * 13,
            },
            threshold=args.world_model_threshold,
            dimensions=16,
        )

    router = Router([parser], sinks, sentinel=sentinel, ingress=ingress)
    return router


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format=_LOG_FORMAT)
    router = _build_router(args)
    processed = router.dispatch(limit=args.limit)
    logging.getLogger(__name__).info("Processed %s event(s)", processed)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
