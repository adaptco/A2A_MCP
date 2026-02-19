#!/usr/bin/env python3
"""Minimal websocket smoke client for pipeline event assertions."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, Iterable

import websockets


def _event_name(message: dict[str, Any]) -> str:
    for key in ("event", "type", "name", "topic"):
        value = message.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _matches(message: dict[str, Any], token: str) -> bool:
    return _event_name(message) == token or token in json.dumps(message, sort_keys=True)


async def _run(url: str, payload: str, expects: Iterable[str], rejects: Iterable[str], timeout: float) -> int:
    expected = set(expects)
    rejected = set(rejects)

    async with websockets.connect(url) as websocket:
        await websocket.send(payload)

        while expected:
            raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                message = {"raw": raw}

            for token in list(rejected):
                if _matches(message, token):
                    print(f"rejected token observed: {token}", file=sys.stderr)
                    return 2

            for token in list(expected):
                if _matches(message, token):
                    expected.remove(token)

        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--expect", action="append", default=[])
    parser.add_argument("--reject", action="append", default=[])
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    payload = sys.stdin.read().strip()
    if not payload:
        print("stdin payload is required", file=sys.stderr)
        return 2

    return asyncio.run(
        _run(
            url=args.url,
            payload=payload,
            expects=args.expect,
            rejects=args.reject,
            timeout=args.timeout,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
