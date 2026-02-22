from __future__ import annotations

from dataclasses import dataclass

from prime_directive.sovereignty.event import SovereigntyEvent
from prime_directive.util.hashing import canonical_json, sha256_hex


@dataclass(frozen=True)
class ChainedEvent:
    event: SovereigntyEvent
    hash_current: str


def compute_event_hash(event: SovereigntyEvent) -> str:
    return sha256_hex(canonical_json(event.canonical_payload()))


def append_event(
    sequence: int,
    event_type: str,
    state: str,
    payload: dict,
    prev_hash: str = "",
) -> ChainedEvent:
    event = SovereigntyEvent(
        sequence=sequence,
        event_type=event_type,
        state=state,
        payload=payload,
        prev_hash=prev_hash,
    )
    return ChainedEvent(event=event, hash_current=compute_event_hash(event))


def verify_chain(events: list[ChainedEvent]) -> bool:
    prev_hash = ""
    for idx, item in enumerate(events, start=1):
        if item.event.sequence != idx:
            return False
        if item.event.prev_hash != prev_hash:
            return False
        if compute_event_hash(item.event) != item.hash_current:
            return False
        prev_hash = item.hash_current
    return True
