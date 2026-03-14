import { describe, expect, it } from "vitest";
import { computeHanEigenvalue, reconstructSessionLineageFromNdjson } from "../src/handshake/lineage";

function event(input: {
  kind: string;
  session_id: string;
  event_id: string;
  prev?: string;
  entropy_threshold?: number;
  line?: number;
}) {
  const entropy_threshold = input.entropy_threshold ?? 0.25;
  const payload = {
    kind: input.kind,
    session_id: input.session_id,
    event_id: input.event_id,
    ...(input.prev ? { prev: input.prev } : {}),
    entropy_threshold,
    lineage_witness: {
      format: "ndjson" as const,
      line_number: input.line ?? 1,
      stream_id: `handshake.${input.session_id}`
    }
  };

  return {
    ...payload,
    han_eigenvalue: computeHanEigenvalue(payload)
  };
}

describe("handshake lineage reconstruction", () => {
  it("accepts normal bound chain", () => {
    const e1 = event({ kind: "handshake.opened", session_id: "s-1", event_id: "e-1", line: 1 });
    const e2 = event({ kind: "handshake.bound", session_id: "s-1", event_id: "e-2", prev: "e-1", line: 2 });
    const e3 = event({ kind: "handshake.fossilized", session_id: "s-1", event_id: "e-3", prev: "e-2", line: 3 });
    const ndjson = [e1, e2, e3].map((e) => JSON.stringify(e)).join("\n");

    const lineage = reconstructSessionLineageFromNdjson(ndjson).get("s-1");
    expect(lineage).toBeDefined();
    expect(lineage?.events).toHaveLength(3);
    expect(lineage?.revoked).toBe(false);
  });

  it("rejects revoked-and-continued chain", () => {
    const ndjson = [
      event({ kind: "handshake.opened", session_id: "s-1", event_id: "e-1", line: 1 }),
      event({ kind: "handshake.revoked", session_id: "s-1", event_id: "e-2", prev: "e-1", line: 2 }),
      event({ kind: "handshake.bound", session_id: "s-1", event_id: "e-3", prev: "e-2", line: 3 })
    ].map((e) => JSON.stringify(e)).join("\n");

    expect(() => reconstructSessionLineageFromNdjson(ndjson)).toThrow(/after revocation/);
  });

  it("rejects mismatched prev chain link", () => {
    const ndjson = [
      event({ kind: "handshake.opened", session_id: "s-1", event_id: "e-1", line: 1 }),
      event({ kind: "handshake.bound", session_id: "s-1", event_id: "e-2", prev: "not-e-1", line: 2 })
    ].map((e) => JSON.stringify(e)).join("\n");

    expect(() => reconstructSessionLineageFromNdjson(ndjson)).toThrow(/expected prev=e-1/);
  });

  it("rejects duplicate event_id in same session", () => {
    const ndjson = [
      event({ kind: "handshake.opened", session_id: "s-1", event_id: "e-1", line: 1 }),
      event({ kind: "handshake.bound", session_id: "s-1", event_id: "e-1", prev: "e-1", line: 2 })
    ].map((e) => JSON.stringify(e)).join("\n");

    expect(() => reconstructSessionLineageFromNdjson(ndjson)).toThrow(/duplicate event_id/);
  });

  it("rejects eigenvalue mismatch", () => {
    const bad = event({ kind: "handshake.opened", session_id: "s-1", event_id: "e-1", line: 1 });
    const ndjson = JSON.stringify({ ...bad, han_eigenvalue: bad.han_eigenvalue + 0.001 });
    expect(() => reconstructSessionLineageFromNdjson(ndjson)).toThrow(/Invalid han_eigenvalue/);
  });

  it("rejects NDJSON witness line mismatch", () => {
    const bad = event({ kind: "handshake.opened", session_id: "s-1", event_id: "e-1", line: 2 });
    const ndjson = JSON.stringify(bad);
    expect(() => reconstructSessionLineageFromNdjson(ndjson)).toThrow(/Invalid NDJSON witness line_number/);
  });
});
