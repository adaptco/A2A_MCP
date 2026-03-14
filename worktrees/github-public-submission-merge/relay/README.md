# Relay Packet (Kestrel) Ingestion Artifacts

This directory holds the NDJSON packet used for CI ingestion dry-runs plus
the helper notes for replacing placeholder checksum fields with canonical
values.

## Files

- `relay_packet.kestrel.ndjson` — staged MANIFEST/ARTIFACT/SIGNATURE rows for
the ingest pipeline (placeholders included).
- `../scripts/jcs_checksum_helper.py` — utility to compute canonical JSON
  (JCS-style) strings, `payload_sha256`, and `payload_b64` for each row.

## Workflow

1. Update each `ARTIFACT` payload with the finalized URIs, byte sizes, and
   signing subjects.
2. Run the checksum helper to compute canonical strings and digests:

   ```bash
   python scripts/jcs_checksum_helper.py relay/relay_packet.kestrel.ndjson --ndjson
   ```

3. Copy the `canonical`, `sha256`, and `payload_b64` outputs back into the
   corresponding `payload_jcs`, `payload_sha256`, and `payload_jcs_b64` fields.
4. Sign the canonical strings with your Ed25519 key and fill the
   `signature_b64` field inside the `SIGNATURE` row.
5. Append the finalized NDJSON to the P3 ledger for ingestion tests.

This flow keeps the pre-flight artifacts deterministic while allowing
CI to verify ordering, schema shape, and atomic append semantics.
