"""Corridor-grade LedgerEmitter (atomic append + running Merkle root)."""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import os
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

_HAS_JCS = importlib.util.find_spec("jcs") is not None
if _HAS_JCS:
    import jcs  # type: ignore

    def canonicalize(obj: Any) -> bytes:
        return jcs.dumps(obj).encode("utf-8")

    CANONICALIZER_ID = "python-jcs:rfc8785"
else:

    def canonicalize(obj: Any) -> bytes:
        def _sort(o: Any) -> Any:
            if isinstance(o, dict):
                return {k: _sort(o[k]) for k in sorted(o.keys())}
            if isinstance(o, list):
                return [_sort(x) for x in o]
            return o

        return json.dumps(_sort(obj), separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    CANONICALIZER_ID = "fallback:sorted-json"


LEAF_PREFIX = b"CORRIDOR_MERKLE_LEAF_V1\x00"
NODE_PREFIX = b"CORRIDOR_MERKLE_NODE_V1\x00"
EMPTY_PREFIX = b"CORRIDOR_MERKLE_EMPTY_V1\x00"
MMR_BAG_PREFIX = b"CORRIDOR_MMR_BAG_V1\x00"
MMR_GAP_PREFIX = b"CORRIDOR_MMR_GAP_V1\x00"
MMR_PEAK_PREFIX = b"CORRIDOR_MMR_PEAK_V1\x00"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_digest(data: bytes) -> str:
    return "sha256:" + sha256_hex(data)


def now_ns() -> int:
    return time.time_ns()


def _hex_bytes_from_sha256(digest: str) -> bytes:
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise ValueError("digest must be sha256:hex")
    hx = digest.split(":", 1)[1]
    if len(hx) != 64:
        raise ValueError("sha256 hex length must be 64")
    return bytes.fromhex(hx)


def _leaf_hash(leaf_digest: str) -> bytes:
    return hashlib.sha256(LEAF_PREFIX + _hex_bytes_from_sha256(leaf_digest)).digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(NODE_PREFIX + left + right).digest()


def _empty_root() -> str:
    return sha256_digest(EMPTY_PREFIX)


def merkle_root_from_leaves(leaves: List[str]) -> str:
    """Deterministic binary Merkle root over leaf digests (sha256:hex)."""
    if not leaves:
        return _empty_root()

    nodes = [_leaf_hash(leaf) for leaf in leaves]
    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
        nxt: List[bytes] = []
        for i in range(0, len(nodes), 2):
            nxt.append(_node_hash(nodes[i], nodes[i + 1]))
        nodes = nxt
    return "sha256:" + nodes[0].hex()


def _mmr_bag(peaks_with_gaps: List[str]) -> str:
    """Deterministic bagging of MMR peaks into a single root."""
    acc = hashlib.sha256(MMR_BAG_PREFIX).digest()
    for peak in peaks_with_gaps:
        if peak == "":
            acc = hashlib.sha256(MMR_GAP_PREFIX + acc).digest()
        else:
            acc = hashlib.sha256(MMR_PEAK_PREFIX + acc + _hex_bytes_from_sha256(peak)).digest()
    return "sha256:" + acc.hex()


def _mmr_push(peaks: List[str], leaf_digest: str) -> Tuple[List[str], str]:
    """Push a leaf into MMR peaks."""
    node = _leaf_hash(leaf_digest)
    height = 0
    new_peaks_bytes: List[Optional[bytes]] = []
    for peak in peaks:
        if peak == "":
            new_peaks_bytes.append(None)
        else:
            new_peaks_bytes.append(_hex_bytes_from_sha256(peak))

    while height < len(new_peaks_bytes) and new_peaks_bytes[height] is not None:
        left = new_peaks_bytes[height]
        right = node
        node = _node_hash(left, right)
        new_peaks_bytes[height] = None
        height += 1

    while height >= len(new_peaks_bytes):
        new_peaks_bytes.append(None)

    new_peaks_bytes[height] = node

    packed: List[str] = []
    for item in new_peaks_bytes:
        if item is None:
            packed.append("")
        else:
            packed.append("sha256:" + item.hex())

    return packed, _mmr_bag(packed)


def _atomic_write_json(path: str, obj: Dict[str, Any]) -> None:
    """Write JSON to a temp file then atomically replace the target file."""
    tmp = path + ".tmp"
    data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n"

    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def _fsync_dir(dir_path: str) -> None:
    try:
        fd = os.open(dir_path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        pass


_POSIX = os.name == "posix"
_NT = os.name == "nt"
if _POSIX:
    import fcntl  # type: ignore
else:
    fcntl = None  # type: ignore[assignment]
if _NT:
    import msvcrt  # type: ignore
else:
    msvcrt = None  # type: ignore[assignment]


class _FileLock:
    """Best-effort cross-platform file lock using a lock file."""

    def __init__(self, lock_path: str):
        self.lock_path = lock_path
        self._fh: Optional[Any] = None

    def __enter__(self) -> "_FileLock":
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
        self._fh = open(self.lock_path, "a+", encoding="utf-8")
        if _POSIX and fcntl is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
            except OSError:
                pass
        elif _NT and msvcrt is not None:
            try:
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_LOCK, 1)
            except OSError:
                pass
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not self._fh:
            return
        try:
            if _POSIX and fcntl is not None:
                try:
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
            elif _NT and msvcrt is not None:
                try:
                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
        finally:
            self._fh.close()
            self._fh = None


class LedgerEmitter:
    """Corridor-grade emitter for TranscriptLeaf objects (dataclass or dict-like)."""

    def __init__(
        self,
        base_dir: str,
        ledger_name: str = "fossil-ledger.ndjson",
        state_name: str = "fossil-ledger.state.json",
        lock_name: str = "fossil-ledger.lock",
        seal_phrase: str = "Canonical truth, attested and replayable.",
        merkle_mode: str = "LEAVES",
        store_leaf_digests_in_state: bool = True,
        enable_file_lock: bool = True,
    ) -> None:
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

        self.ledger_path = os.path.join(self.base_dir, ledger_name)
        self.state_path = os.path.join(self.base_dir, state_name)
        self.lock_path = os.path.join(self.base_dir, lock_name)

        self.seal_phrase = seal_phrase
        self.merkle_mode = merkle_mode.upper().strip()
        self.store_leaf_digests_in_state = bool(store_leaf_digests_in_state)
        self.enable_file_lock = bool(enable_file_lock)

        if self.merkle_mode not in ("LEAVES", "MMR"):
            raise ValueError("merkle_mode must be LEAVES or MMR")

        if self.merkle_mode == "MMR":
            self.store_leaf_digests_in_state = False

        open(self.ledger_path, "a", encoding="utf-8").close()

        self._lock = asyncio.Lock()
        self._state = self._load_or_init_state()

    def _load_or_init_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_path):
            with open(self.state_path, "r", encoding="utf-8") as handle:
                st = json.loads(handle.read())

            if st.get("schema_version") != "LedgerState.v1":
                raise ValueError("Ledger state schema_version mismatch")
            if st.get("ledger_path") != os.path.basename(self.ledger_path):
                raise ValueError("Ledger state ledger_path mismatch")
            if st.get("canonicalizer") != CANONICALIZER_ID:
                raise ValueError("Ledger state canonicalizer mismatch")
            if st.get("seal_phrase") != self.seal_phrase:
                raise ValueError("Ledger state seal_phrase mismatch")
            if st.get("merkle_mode") != self.merkle_mode:
                raise ValueError("Ledger state merkle_mode mismatch")
            if not isinstance(st.get("count"), int) or st["count"] < 0:
                raise ValueError("Ledger state count invalid")
            if not isinstance(st.get("merkle_root"), str):
                raise ValueError("Ledger state merkle_root invalid")

            if self.merkle_mode == "LEAVES":
                if st.get("leaf_digests") is None:
                    raise ValueError("LEAVES mode requires leaf_digests in state")
                if not isinstance(st.get("leaf_digests"), list):
                    raise ValueError("state leaf_digests invalid")
            else:
                if not isinstance(st.get("mmr_peaks"), list):
                    raise ValueError("MMR mode requires mmr_peaks list")

            return st

        st: Dict[str, Any] = {
            "schema_version": "LedgerState.v1",
            "ledger_path": os.path.basename(self.ledger_path),
            "canonicalizer": CANONICALIZER_ID,
            "seal_phrase": self.seal_phrase,
            "merkle_mode": self.merkle_mode,
            "count": 0,
            "merkle_root": _empty_root(),
            "updated_ns": now_ns(),
        }

        if self.merkle_mode == "LEAVES":
            st["leaf_digests"] = [] if self.store_leaf_digests_in_state else []
            if not self.store_leaf_digests_in_state:
                raise ValueError(
                    "LEAVES mode requires store_leaf_digests_in_state=True (or use merkle_mode=MMR)"
                )
        else:
            st["mmr_peaks"] = []

        _atomic_write_json(self.state_path, st)
        _fsync_dir(self.base_dir)
        return st

    def _state_leaf_digests(self) -> List[str]:
        ld = self._state.get("leaf_digests")
        if not isinstance(ld, list):
            raise ValueError("state leaf_digests invalid")
        return ld

    def _state_mmr_peaks(self) -> List[str]:
        pk = self._state.get("mmr_peaks")
        if not isinstance(pk, list):
            raise ValueError("state mmr_peaks invalid")
        return pk

    async def emit_leaf(self, leaf: Any) -> str:
        """Emit a TranscriptLeaf and return leaf_digest."""
        async with self._lock:
            lock_ctx = _FileLock(self.lock_path) if self.enable_file_lock else None
            if lock_ctx:
                with lock_ctx:
                    return self._emit_leaf_locked(leaf)
            return self._emit_leaf_locked(leaf)

    def _emit_leaf_locked(self, leaf: Any) -> str:
        if hasattr(leaf, "to_dict") and callable(getattr(leaf, "to_dict")):
            leaf_dict = leaf.to_dict()
        elif hasattr(leaf, "__dataclass_fields__"):
            leaf_dict = asdict(leaf)
        elif isinstance(leaf, dict):
            leaf_dict = leaf
        else:
            raise TypeError("leaf must be dict-like or dataclass-like")

        leaf_canonical = canonicalize(leaf_dict)
        leaf_digest = sha256_digest(leaf_canonical)

        seq = int(self._state["count"]) + 1
        ts = now_ns()

        if self.merkle_mode == "LEAVES":
            leaves = self._state_leaf_digests()
            leaves.append(leaf_digest)
            merkle_root = merkle_root_from_leaves(leaves)
        else:
            peaks = self._state_mmr_peaks()
            new_peaks, merkle_root = _mmr_push(peaks, leaf_digest)
            self._state["mmr_peaks"] = new_peaks

        line = {
            "schema_version": "VaultLedgerLine.v1",
            "seq": seq,
            "timestamp_ns": ts,
            "canonicalizer": CANONICALIZER_ID,
            "seal_phrase": self.seal_phrase,
            "leaf_digest": leaf_digest,
            "leaf": leaf_dict,
            "leaf_canonical_utf8": leaf_canonical.decode("utf-8", errors="strict"),
            "merkle_mode": self.merkle_mode,
            "merkle_root": merkle_root,
        }

        with open(self.ledger_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, separators=(",", ":"), ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

        self._state["count"] = seq
        self._state["merkle_root"] = merkle_root
        self._state["updated_ns"] = ts

        _atomic_write_json(self.state_path, self._state)
        _fsync_dir(self.base_dir)

        return leaf_digest

    def current_merkle_root(self) -> str:
        return str(self._state["merkle_root"])

    def count(self) -> int:
        return int(self._state["count"])


def verify_ledger(
    base_dir: str,
    ledger_name: str = "fossil-ledger.ndjson",
    state_name: str = "fossil-ledger.state.json",
) -> Dict[str, Any]:
    ledger_path = os.path.join(base_dir, ledger_name)
    state_path = os.path.join(base_dir, state_name)

    with open(state_path, "r", encoding="utf-8") as handle:
        st = json.loads(handle.read())

    merkle_mode = st.get("merkle_mode", "LEAVES")
    last_seq = 0

    if merkle_mode == "LEAVES":
        leaves: List[str] = []
        with open(ledger_path, "r", encoding="utf-8") as handle:
            for line in handle:
                obj = json.loads(line)
                if obj.get("schema_version") != "VaultLedgerLine.v1":
                    raise ValueError("ledger line schema_version mismatch")
                seq = int(obj["seq"])
                if seq != last_seq + 1:
                    raise ValueError("ledger seq discontinuity")
                last_seq = seq
                leaves.append(obj["leaf_digest"])
        root = merkle_root_from_leaves(leaves)
    elif merkle_mode == "MMR":
        peaks: List[str] = []
        with open(ledger_path, "r", encoding="utf-8") as handle:
            for line in handle:
                obj = json.loads(line)
                if obj.get("schema_version") != "VaultLedgerLine.v1":
                    raise ValueError("ledger line schema_version mismatch")
                seq = int(obj["seq"])
                if seq != last_seq + 1:
                    raise ValueError("ledger seq discontinuity")
                last_seq = seq
                peaks, root = _mmr_push(peaks, obj["leaf_digest"])
    else:
        raise ValueError(f"Unknown merkle_mode in state: {merkle_mode}")

    ok = (last_seq == int(st["count"])) and (root == st["merkle_root"])
    return {
        "ok": ok,
        "computed_count": last_seq,
        "computed_merkle_root": root,
        "state_count": st["count"],
        "state_merkle_root": st["merkle_root"],
        "canonicalizer": st.get("canonicalizer"),
        "merkle_mode": merkle_mode,
    }
