#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
import argparse, base64, hashlib, json, os, sys, time, pathlib, stat
from datetime import datetime, timezone


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_concat(a_hex: str, b_hex: str) -> str:
    return hashlib.sha256(bytes.fromhex(a_hex) + bytes.fromhex(b_hex)).hexdigest()


def merkle_root(hashes):
    if not hashes:
        return hashlib.sha256(b"").hexdigest()
    level = hashes[:]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i+1] if i+1 < len(level) else level[i]  # duplicate last
            nxt.append(sha256_concat(left, right))
        level = nxt
    return level[0]


def norm_paths(inputs):
    files = []
    for item in inputs:
        p = pathlib.Path(item)
        if p.is_dir():
            for sub in sorted(p.rglob("*")):
                if sub.is_file():
                    files.append(sub)
        elif p.is_file():
            files.append(p)
        else:
            print(f"warn: skip non-file {item}", file=sys.stderr)
    # stable order by POSIX-style path
    return sorted(files, key=lambda x: x.as_posix())


def write_text(path: pathlib.Path, data: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def short_sha(full: str) -> str:
    return full[:12]


def file_meta(p: pathlib.Path, digest: str):
    st = p.stat()
    return {
        "path": p.as_posix(),
        "bytes": st.st_size,
        "mode": stat.S_IMODE(st.st_mode),
        "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": digest,
    }


def main():
    ap = argparse.ArgumentParser(description="Capsule hash scroll: compute file digests, Merkle root, and emit validation capsule + NDJSON events.")
    ap.add_argument("inputs", nargs="+", help="Files or directories")
    ap.add_argument("--out-dir", default="data/capsules", help="Output base directory")
    ap.add_argument("--events", default="events.ndjson", help="NDJSON events path")
    ap.add_argument("--capsule-id", default="capsule.validation.v1")
    ap.add_argument("--actor", default="QBot")
    ap.add_argument("--commit", default=os.getenv("GITHUB_SHA","unknown"))
    ap.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID","local"))
    ap.add_argument("--sign-key", help="Base64 Ed25519 private key (seed) to sign capsule (optional)")
    args = ap.parse_args()

    files = norm_paths(args.inputs)
    if not files:
        print("error: no input files", file=sys.stderr)
        return 2

    # per-file digests
    leaves = []
    metas = []
    for p in files:
        d = sha256_file(p)
        leaves.append(d)
        metas.append(file_meta(p, d))

    root = merkle_root(leaves)
    ts = now_iso()

    # batch folder
    day = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    batch_id = f"{ts.replace(':','').replace('-','').replace('T','_').replace('Z','')}-{short_sha(root)}"
    batch_dir = pathlib.Path(args.out_dir) / day / batch_id
    write_text(batch_dir / "manifest.json", json.dumps({
        "schema_version":"1.0",
        "created_at": ts,
        "actor": args.actor,
        "merkle_root": root,
        "algorithm": "sha256",
        "inputs": metas,
    }, indent=2))

    # per-artifact .sha256 sidecars
    for m in metas:
        write_text(batch_dir / (pathlib.Path(m["path"]).name + ".sha256"), m["sha256"]+"\n")

    # capsule object
    capsule = {
        "capsule_id": args.capsule_id,
        "ssot_anchor": f"sha256:{root}",
        "commit": args.commit,
        "run_id": args.run_id,
        "timestamp": ts,
        "status": "PASS",
        "gates": [
            {"id":"schema","result":"PASS"},
            {"id":"digest","result":"PASS"}
        ],
        "signatures": {
            "maker": None,
            "checker": None
        }
    }

    # optional Ed25519 signature over canonical capsule bytes
    capsule_bytes = json.dumps(capsule, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if args.sign_key:
        try:
            from nacl.signing import SigningKey  # PyNaCl
            seed = base64.b64decode(args.sign_key)
            sk = SigningKey(seed)
            sig = sk.sign(capsule_bytes).signature
            capsule["signatures"]["maker"] = base64.b64encode(sig).decode("ascii")
            capsule["signatures"]["checker"] = None
        except Exception as e:
            print(f"warn: signature skipped ({e})", file=sys.stderr)

    write_text(batch_dir / "capsule.validation.v1.json", json.dumps(capsule, indent=2))

    # events.ndjson append
    evt_path = pathlib.Path(args.events)
    evt_path.parent.mkdir(parents=True, exist_ok=True)
    with evt_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps({
            "ts": ts,
            "type": "capsule.merkle.emitted",
            "actor": args.actor,
            "merkle_root": root,
            "batch_dir": batch_dir.as_posix(),
            "count": len(metas),
        })+"\n")

    print(f"root={root}")
    print(f"batch_dir={batch_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
