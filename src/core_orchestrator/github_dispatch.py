"""Utilities for dispatching orchestration blocks to GitHub Actions."""
from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from typing import Any, Dict, Mapping, MutableMapping, Optional

import requests

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
DEFAULT_EVENT_TYPE = "append_logic_block"


def _normalize_coords(payload: MutableMapping[str, Any]) -> None:
    """Ensure coordinates are serialized as a list for JSON payloads."""

    if "coords" not in payload:
        return
    coords = payload["coords"]
    if coords is None or isinstance(coords, list):
        return
    try:
        payload["coords"] = list(coords)
    except TypeError:
        payload["coords"] = [coords]


def make_tx_id(payload: Mapping[str, Any], *, salt_with_uuid: bool = True) -> str:
    """Compute a stable transaction id from the payload.

    Parameters
    ----------
    payload:
        The payload to hash.
    salt_with_uuid:
        Append a short ``uuid4`` suffix to the digest to reduce the risk of
        collisions across near-identical payloads.
    """

    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if not salt_with_uuid:
        return digest
    return f"{digest[:16]}-{uuid.uuid4().hex[:8]}"


def send_block(
    owner: str,
    repo: str,
    token: str,
    payload: Mapping[str, Any],
    *,
    event_type: str = DEFAULT_EVENT_TYPE,
    tx_id: Optional[str] = None,
    max_retries: int = 3,
    backoff_base: float = 0.5,
    timeout: int = 10,
    salt_tx_id: bool = True,
) -> Dict[str, Any]:
    """Send a repository_dispatch event to GitHub with retries.

    Returns a summary dict with ``success``, ``status_code``, ``body``, and
    ``tx_id`` keys.
    """

    client_payload: Dict[str, Any] = dict(payload)
    _normalize_coords(client_payload)
    tx = tx_id or make_tx_id(client_payload, salt_with_uuid=salt_tx_id)
    client_payload["tx_id"] = tx

    url = f"{GITHUB_API}/repos/{owner}/{repo}/dispatches"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = {"event_type": event_type, "client_payload": client_payload}
    body_json = json.dumps(body, separators=(",", ":"), sort_keys=True)

    last_error: Optional[str] = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, headers=headers, data=body_json, timeout=timeout)
        except requests.RequestException as exc:
            last_error = str(exc)
            logger.warning(
                "Dispatch attempt %s/%s failed for tx_id=%s: %s",
                attempt + 1,
                max_retries + 1,
                tx,
                exc,
            )
        else:
            if response.status_code == 204:
                logger.info("GitHub dispatch accepted tx_id=%s", tx)
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "body": response.text,
                    "tx_id": tx,
                }
            if 400 <= response.status_code < 500:
                logger.error(
                    "GitHub dispatch rejected tx_id=%s with %s: %s",
                    tx,
                    response.status_code,
                    response.text,
                )
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "body": response.text,
                    "tx_id": tx,
                }
            last_error = f"HTTP {response.status_code}: {response.text}"
            logger.warning(
                "GitHub dispatch retrying tx_id=%s after %s (attempt %s/%s)",
                tx,
                last_error,
                attempt + 1,
                max_retries + 1,
            )

        if attempt < max_retries:
            time.sleep(backoff_base * (2**attempt))

    return {"success": False, "status_code": None, "body": last_error, "tx_id": tx}


__all__ = ["send_block", "make_tx_id"]
