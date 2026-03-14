#!/usr/bin/env python3
"""Utility helpers for staging, sealing, and exporting the QUBE patent draft capsule."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUBE_DIR = ROOT / "capsules" / "doctrine" / "capsule.patentDraft.qube.v1"
DEFAULT_CAPSULE_PATH = DEFAULT_QUBE_DIR / "capsule.patentDraft.qube.v1.json"
DEFAULT_EXPORT_PATH = DEFAULT_QUBE_DIR / "capsule.export.qubePatent.v1.request.json"
DEFAULT_LEDGER_PATH = DEFAULT_QUBE_DIR / "ledger.jsonl"
DEFAULT_P3L_SOURCE = ROOT / "capsules" / "doctrine" / "raci.plan.v1.1" / "raci.plan.v1.1.json"

DEFAULT_STAGE_TS = "2025-09-19T04:46:00Z"
DEFAULT_SEAL_TS = "2025-09-19T04:48:30Z"
DEFAULT_EXPORT_TS = "2025-09-19T04:49:10Z"
DEFAULT_DUAL_RUN_SEED = "2025-09-19T04:40:00Z"
DEFAULT_DUAL_RUN_DELTA = "0"
DEFAULT_ARTIFACT_HASH = "sha256:aa04c37d52c182716bb11817902bef83fa30de12afa427d29b2792146f4bf478"
DEFAULT_FINAL_SEAL_HASH = "sha256:f8f9324315d14170e85c0e75182c904bc5803956215f50b2981d8a74bdc88ac2"
DEFAULT_CAPSULE_ID = "capsule.patentDraft.qube.v1"
DEFAULT_DEPLOYMENT_ID = "phase.1.qube"
DEFAULT_REPLAY_PACKET_ID = "replay:cdpy71:pathA"
DEFAULT_ARCHIVE_REF = "s3://qube/bundles/qube.v1.tar.zst"
DEFAULT_PROTOCOL = "capsule.export.qubePatent.v1"
DEFAULT_FORMAT = "artifactBundle"
DEFAULT_ISSUED_AT = "2025-09-19T04:45:00Z"
DEFAULT_ISSUER = "Council"
DEFAULT_EPOCH = "phase.1.init"
DEFAULT_TRIGGER_EVENT = "SEAL"
DEFAULT_EXPORT_POLICY = "policy:QUBE"
DEFAULT_APPEND_TARGET = "ledger/federation.jsonl"
DEFAULT_ATTESTATION = "2-of-3"
DEFAULT_P3L_REF = "urn:p3l:raci.plan.v1.1"
DEFAULT_QONLEDGE_REF = "urn:qon:raci.plan.v1.1"
DEFAULT_SR_GATE = "v1"
DEFAULT_MOE_TOPOLOGY = "experts:4, router:SR"
DEFAULT_MALINTENT = "BLQB9X/MIT.01"
DEFAULT_ARTIFACT_TYPE = "R0P3"
DEFAULT_ARTIFACT_FORMAT = "iRQLxTR33"
DEFAULT_POLICY = "P3L.v6"


@dataclass
class ExportConfig:
    deployment_id: str = DEFAULT_DEPLOYMENT_ID
    capsule_id: str = DEFAULT_CAPSULE_ID
    replay_packet_id: str = DEFAULT_REPLAY_PACKET_ID
    archive_ref: str = DEFAULT_ARCHIVE_REF
    protocol: str = DEFAULT_PROTOCOL
    format: str = DEFAULT_FORMAT
    issued_at: str = DEFAULT_ISSUED_AT
    issuer: str = DEFAULT_ISSUER
    epoch: str = DEFAULT_EPOCH
    trigger_event: str = DEFAULT_TRIGGER_EVENT
    export_policy_ref: str = DEFAULT_EXPORT_POLICY
    append_target: str = DEFAULT_APPEND_TARGET
    attestation_quorum: str = DEFAULT_ATTESTATION
    sha256_verification: bool = True
    merkle_proof: bool = True

    def to_request_body(self) -> Dict[str, Any]:
        return {
            "deploymentId": self.deployment_id,
            "capsuleId": self.capsule_id,
            "replayPacketId": self.replay_packet_id,
            "archiveRef": self.archive_ref,
            "dao": {
                "protocol": self.protocol,
                "format": self.format,
                "integrity": {
                    "sha256_verification": self.sha256_verification,
                    "merkle_proof": self.merkle_proof,
                    "attestation_quorum": self.attestation_quorum,
                },
                "ledger_binding": {
                    "append_target": self.append_target,
                    "proof_binding": "sha256:REQUEST",
                },
            },
            "meta": {
                "issued_at": self.issued_at,
                "issuer": self.issuer,
                "epoch": self.epoch,
                "trigger_event": self.trigger_event,
                "export_policy_ref": self.export_policy_ref,
            },
        }


@dataclass
class LedgerEvent:
    ts: str
    event_type: str
    payload: Dict[str, Any]
    capsule_id: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "ts": self.ts,
                "type": self.event_type,
                "capsule_id": self.capsule_id,
                "payload": self.payload,
            },
            separators=(",", ":"),
        )


def _load_ledger(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_ledger(path: Path, entries: List[Dict[str, Any]]) -> None:
    ordered = sorted(entries, key=lambda entry: entry["ts"])
    with path.open("w") as handle:
        for entry in ordered:
            handle.write(json.dumps(entry, separators=(",", ":")) + "\n")


def _compute_p3l_sha(p3l_source: Path) -> str:
    digest = hashlib.sha256(p3l_source.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _compute_merkle_root(p3l_sha: str, capsule_id: str) -> str:
    seed = f"{p3l_sha}{capsule_id}".encode()
    return hashlib.sha256(seed).hexdigest()


def _write_capsule(
    *,
    capsule_id: str,
    capsule_path: Path,
    p3l_source: Path,
    p3l_ref: str,
    sr_gate: str,
    moe_topology: str,
    malintent: str,
    artifact_type: str,
    artifact_format: str,
    qonledge_ref: str,
    scrollstream: bool,
    attestation_quorum: str,
    epoch: str,
    issuer: str,
    policy: str,
) -> str:
    p3l_sha = _compute_p3l_sha(p3l_source)
    body = {
        "capsule_id": capsule_id,
        "qube": {
            "p3l_ref": p3l_ref,
            "sr_gate": sr_gate,
            "moe_topology": moe_topology,
            "malintent": malintent,
            "artifact": {
                "type": artifact_type,
                "format": artifact_format,
            },
        },
        "lineage": {
            "qonledge_ref": qonledge_ref,
            "scrollstream": scrollstream,
        },
        "integrity": {
            "sha256_p3l": p3l_sha,
            "merkle_root": _compute_merkle_root(p3l_sha, capsule_id),
            "attestation_quorum": attestation_quorum,
        },
        "meta": {
            "epoch": epoch,
            "issuer": issuer,
            "policy": policy,
        },
    }
    capsule_path.parent.mkdir(parents=True, exist_ok=True)
    with capsule_path.open("w") as handle:
        json.dump(body, handle, indent=2)
        handle.write("\n")
    digest = hashlib.sha256(capsule_path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _canonical_request_payload(config: ExportConfig) -> str:
    return json.dumps(config.to_request_body(), indent=2) + "\n"


def _canonical_request_digest(config: ExportConfig) -> str:
    payload = _canonical_request_payload(config)
    return f"sha256:{hashlib.sha256(payload.encode()).hexdigest()}"


def _build_export_config(args: argparse.Namespace) -> ExportConfig:
    return ExportConfig(
        deployment_id=args.deployment_id,
        capsule_id=args.capsule_id,
        replay_packet_id=args.replay_packet_id,
        archive_ref=args.archive_ref,
        protocol=args.protocol,
        format=args.format,
        issued_at=args.request_issued_at,
        issuer=args.request_issuer,
        epoch=args.request_epoch,
        trigger_event=args.trigger_event,
        export_policy_ref=args.export_policy_ref,
        append_target=args.append_target,
        attestation_quorum=args.dao_attestation_quorum,
        sha256_verification=args.sha256_verification,
        merkle_proof=args.merkle_proof,
    )


def stage(args: argparse.Namespace) -> None:
    capsule_path = Path(args.capsule_path)
    ledger_path = Path(args.ledger_path)
    p3l_source = Path(args.p3l_source)

    ticket_hash = _write_capsule(
        capsule_id=args.capsule_id,
        capsule_path=capsule_path,
        p3l_source=p3l_source,
        p3l_ref=args.p3l_ref,
        sr_gate=args.sr_gate,
        moe_topology=args.moe_topology,
        malintent=args.malintent,
        artifact_type=args.artifact_type,
        artifact_format=args.artifact_format,
        qonledge_ref=args.qonledge_ref,
        scrollstream=args.scrollstream,
        attestation_quorum=args.attestation_quorum,
        epoch=args.epoch,
        issuer=args.issuer,
        policy=args.policy,
    )

    entries = _load_ledger(ledger_path)
    if args.force:
        entries = [entry for entry in entries if entry["type"] != "capsule.staged"]
    elif any(entry["type"] == "capsule.staged" for entry in entries):
        print("✅ Ledger already contains capsule.staged event")
        return

    stage_event = LedgerEvent(
        ts=args.stage_ts,
        event_type="capsule.staged",
        payload={
            "packaging_map": {
                "input": "P3L → qLock/LiD → QBits → SR Gate → MoE → BLQB9X → R0P3"
            },
            "gates": {
                "G01": {"ticket_hash": ticket_hash, "status": "PASS"},
                "G02": {"fitment": f"sr-gate:{args.sr_gate}", "status": "PASS"},
                "G03": {
                    "artifact_hashes": [args.artifact_hash],
                    "status": args.g03_status,
                },
                "G04": {
                    "expected_verify": args.g04_expected,
                    "status": args.g04_status,
                },
            },
            "dual_run": {"seed": args.dual_run_seed, "delta": args.dual_run_delta},
            "aegis": {
                "blqb9x_audit": args.blqb9x_audit,
                "qonledge_append": args.qonledge_append,
            },
        },
        capsule_id=args.capsule_id,
    )
    entries.append(json.loads(stage_event.to_json()))
    _write_ledger(ledger_path, entries)
    print(f"📜 Staged {args.capsule_id}")


def seal(args: argparse.Namespace) -> None:
    ledger_path = Path(args.ledger_path)
    entries = _load_ledger(ledger_path)
    if args.force:
        entries = [entry for entry in entries if entry["type"] != "capsule.sealed"]
    elif any(entry["type"] == "capsule.sealed" for entry in entries):
        print("✅ Ledger already contains capsule.sealed event")
        return

    export_config = _build_export_config(args)
    request_digest = _canonical_request_digest(export_config)
    sealed_event = LedgerEvent(
        ts=args.seal_ts,
        event_type="capsule.sealed",
        payload={
            "finalseal_hash": args.finalseal_hash,
            "gates": {
                "G03": {
                    "artifact_hashes": [args.artifact_hash],
                    "status": "PASS",
                },
                "G04": {"verify_result": "pass", "status": "PASS"},
            },
            "proof_binding": request_digest,
            "merkle_proof": args.merkle_proof,
            "attestation_quorum": export_config.attestation_quorum,
        },
        capsule_id=args.capsule_id,
    )
    entries.append(json.loads(sealed_event.to_json()))
    _write_ledger(ledger_path, entries)
    print("🔏 Recorded capsule seal with proof binding", request_digest)


def export(args: argparse.Namespace) -> None:
    ledger_path = Path(args.ledger_path)
    export_path = Path(args.export_path)

    export_config = _build_export_config(args)
    payload = _canonical_request_payload(export_config)

    export_path.parent.mkdir(parents=True, exist_ok=True)
    with export_path.open("w") as handle:
        handle.write(payload)

    request_digest = _canonical_request_digest(export_config)
    entries = _load_ledger(ledger_path)
    if args.force:
        entries = [entry for entry in entries if entry["type"] != "dao.export.requested"]
    elif any(entry["type"] == "dao.export.requested" for entry in entries):
        print("✅ Ledger already contains dao.export.requested event")
        return

    export_event = LedgerEvent(
        ts=args.export_ts,
        event_type="dao.export.requested",
        payload={
            "protocol": export_config.protocol,
            "request_ref": args.request_ref,
            "request_sha256": request_digest,
            "ledger_binding": {
                "append_target": export_config.append_target,
                "proof_binding": request_digest,
            },
        },
        capsule_id=export_config.capsule_id,
    )
    entries.append(json.loads(export_event.to_json()))
    _write_ledger(ledger_path, entries)
    print("🚚 Wrote export request payload")


def _add_common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--ledger-path",
        default=str(DEFAULT_LEDGER_PATH),
        help="Path to the capsule ledger JSONL file (default: %(default)s).",
    )
    parser.add_argument(
        "--capsule-id",
        default=DEFAULT_CAPSULE_ID,
        help="Capsule identifier to stamp on files and ledger events (default: %(default)s).",
    )


def _add_export_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--deployment-id",
        default=DEFAULT_DEPLOYMENT_ID,
        help="Deployment identifier for the DAO request (default: %(default)s).",
    )
    parser.add_argument(
        "--replay-packet-id",
        default=DEFAULT_REPLAY_PACKET_ID,
        help="Replay packet identifier used in the DAO request (default: %(default)s).",
    )
    parser.add_argument(
        "--archive-ref",
        default=DEFAULT_ARCHIVE_REF,
        help="Artifact archive reference (default: %(default)s).",
    )
    parser.add_argument(
        "--protocol",
        default=DEFAULT_PROTOCOL,
        help="DAO export protocol identifier (default: %(default)s).",
    )
    parser.add_argument(
        "--format",
        default=DEFAULT_FORMAT,
        help="DAO export format value (default: %(default)s).",
    )
    parser.add_argument(
        "--request-issued-at",
        default=DEFAULT_ISSUED_AT,
        help="ISO-8601 timestamp recorded in the export request (default: %(default)s).",
    )
    parser.add_argument(
        "--request-issuer",
        default=DEFAULT_ISSUER,
        help="Issuer recorded in the export request (default: %(default)s).",
    )
    parser.add_argument(
        "--request-epoch",
        default=DEFAULT_EPOCH,
        help="Epoch recorded in the export request (default: %(default)s).",
    )
    parser.add_argument(
        "--trigger-event",
        default=DEFAULT_TRIGGER_EVENT,
        help="Trigger event recorded in the export request (default: %(default)s).",
    )
    parser.add_argument(
        "--export-policy-ref",
        default=DEFAULT_EXPORT_POLICY,
        help="Policy reference recorded in the export request (default: %(default)s).",
    )
    parser.add_argument(
        "--append-target",
        default=DEFAULT_APPEND_TARGET,
        help="Ledger append target captured in the DAO request (default: %(default)s).",
    )
    parser.add_argument(
        "--dao-attestation-quorum",
        default=DEFAULT_ATTESTATION,
        help="Attestation quorum recorded in the DAO request (default: %(default)s).",
    )
    parser.add_argument(
        "--sha256-verification",
        dest="sha256_verification",
        action="store_true",
        default=True,
        help="Include sha256_verification=true in the DAO request (default: enabled).",
    )
    parser.add_argument(
        "--no-sha256-verification",
        dest="sha256_verification",
        action="store_false",
        help="Disable sha256 verification in the DAO request integrity block.",
    )
    parser.add_argument(
        "--merkle-proof",
        dest="merkle_proof",
        action="store_true",
        default=True,
        help="Include merkle_proof=true in the DAO request (default: enabled).",
    )
    parser.add_argument(
        "--no-merkle-proof",
        dest="merkle_proof",
        action="store_false",
        help="Disable the merkle_proof flag in the DAO request.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QUBE patent draft pipeline helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    stage_parser = subparsers.add_parser(
        "stage",
        help="Materialize the staged capsule header and ledger entry.",
    )
    _add_common_paths(stage_parser)
    stage_parser.add_argument(
        "--capsule-path",
        default=str(DEFAULT_CAPSULE_PATH),
        help="Path to write the staged capsule header (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--p3l-source",
        default=str(DEFAULT_P3L_SOURCE),
        help="Source JSON for computing the p3l hash (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--p3l-ref",
        default=DEFAULT_P3L_REF,
        help="Reference recorded in qube.p3l_ref (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--qonledge-ref",
        default=DEFAULT_QONLEDGE_REF,
        help="Reference recorded in lineage.qonledge_ref (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--sr-gate",
        default=DEFAULT_SR_GATE,
        help="SR gate identifier recorded in the capsule (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--moe-topology",
        default=DEFAULT_MOE_TOPOLOGY,
        help="MoE topology descriptor recorded in the capsule (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--malintent",
        default=DEFAULT_MALINTENT,
        help="Malintent profile recorded in the capsule (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--artifact-type",
        default=DEFAULT_ARTIFACT_TYPE,
        help="Artifact type recorded in the capsule (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--artifact-format",
        default=DEFAULT_ARTIFACT_FORMAT,
        help="Artifact format recorded in the capsule (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--attestation-quorum",
        default=DEFAULT_ATTESTATION,
        help="Integrity attestation quorum recorded in the capsule (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--epoch",
        default=DEFAULT_EPOCH,
        help="Epoch recorded in the capsule meta block (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--issuer",
        default=DEFAULT_ISSUER,
        help="Issuer recorded in the capsule meta block (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--policy",
        default=DEFAULT_POLICY,
        help="Policy recorded in the capsule meta block (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--stage-ts",
        default=DEFAULT_STAGE_TS,
        help="Timestamp for the capsule.staged ledger event (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--artifact-hash",
        default=DEFAULT_ARTIFACT_HASH,
        help="Artifact hash captured in gate G03 (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--dual-run-seed",
        default=DEFAULT_DUAL_RUN_SEED,
        help="Seed recorded for the dual-run determinism check (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--dual-run-delta",
        default=DEFAULT_DUAL_RUN_DELTA,
        help="Delta value recorded for the dual-run determinism check (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--g03-status",
        default="QUEUED",
        help="Status flag for gate G03 in the staged payload (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--g04-status",
        default="PENDING",
        help="Status flag for gate G04 in the staged payload (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--g04-expected",
        default="pending",
        help="Expected verification descriptor recorded for gate G04 (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--blqb9x-audit",
        default="pass",
        help="BLQB9X audit outcome recorded in the aegis block (default: %(default)s).",
    )
    stage_parser.add_argument(
        "--no-qonledge-append",
        dest="qonledge_append",
        action="store_false",
        help="Disable the QONLEDGE append flag in the aegis block.",
    )
    stage_parser.set_defaults(qonledge_append=True)
    stage_parser.add_argument(
        "--scrollstream",
        dest="scrollstream",
        action="store_true",
        default=True,
        help="Record lineage.scrollstream=true (default: enabled).",
    )
    stage_parser.add_argument(
        "--no-scrollstream",
        dest="scrollstream",
        action="store_false",
        help="Record lineage.scrollstream=false.",
    )
    stage_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite any existing capsule.staged ledger entry.",
    )

    seal_parser = subparsers.add_parser(
        "seal",
        help="Record the sealed ledger event for the QUBE capsule.",
    )
    _add_common_paths(seal_parser)
    _add_export_args(seal_parser)
    seal_parser.add_argument(
        "--seal-ts",
        default=DEFAULT_SEAL_TS,
        help="Timestamp for the capsule.sealed ledger event (default: %(default)s).",
    )
    seal_parser.add_argument(
        "--artifact-hash",
        default=DEFAULT_ARTIFACT_HASH,
        help="Artifact hash captured under gate G03 (default: %(default)s).",
    )
    seal_parser.add_argument(
        "--finalseal-hash",
        default=DEFAULT_FINAL_SEAL_HASH,
        help="Final seal hash recorded in the sealed ledger event (default: %(default)s).",
    )
    seal_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite any existing capsule.sealed ledger entry.",
    )

    export_parser = subparsers.add_parser(
        "export",
        help="Emit the DAO export request and ledger entry.",
    )
    _add_common_paths(export_parser)
    _add_export_args(export_parser)
    export_parser.add_argument(
        "--export-path",
        default=str(DEFAULT_EXPORT_PATH),
        help="Path to write the DAO export request stub (default: %(default)s).",
    )
    export_parser.add_argument(
        "--request-ref",
        default="capsule.export.qubePatent.v1.request.json",
        help="Reference stored in the dao.export.requested ledger payload (default: %(default)s).",
    )
    export_parser.add_argument(
        "--export-ts",
        default=DEFAULT_EXPORT_TS,
        help="Timestamp for the dao.export.requested ledger event (default: %(default)s).",
    )
    export_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite any existing dao.export.requested ledger entry.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "stage":
        stage(args)
    elif args.command == "seal":
        seal(args)
    else:
        export(args)


if __name__ == "__main__":
    main()
