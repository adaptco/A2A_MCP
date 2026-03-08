import { describe, expect, it } from "vitest";
import { promises as fs } from "fs";
import os from "os";
import path from "path";
import {
  appendWitnessRecord,
  canonicalizeForHash,
  chainHandshakeReceipt,
  computeHanEigenvalue,
  computeHandshakeDigest,
} from "./index";

describe("handshake helpers", () => {
  it("canonicalizes with sorted keys and strips wall-clock fields", () => {
    const canonical = canonicalizeForHash({
      b: 2,
      created_at: "drop",
      a: { z: 9, timestamp: 10, y: 8 },
    });

    expect(canonical).toBe('{"a":{"y":8,"z":9},"b":2}');
  });

  it("chains receipt prev digest", () => {
    const first = chainHandshakeReceipt({ session_id: "s1" }, null);
    const second = chainHandshakeReceipt({ session_id: "s2" }, first);

    expect(second.prev).toBe(first.digest);
    expect(second.witness["handshake.bound"].prev).toBe(first.digest);
  });

  it("appends one NDJSON line", async () => {
    const dir = await fs.mkdtemp(path.join(os.tmpdir(), "handshake-"));
    const file = path.join(dir, "events.ndjson");

    await appendWitnessRecord({ b: 2, a: 1 }, file);
    const text = await fs.readFile(file, "utf8");

    expect(text).toBe('{"a":1,"b":2}\n');
  });

  it("computes stable hashes", () => {
    expect(computeHanEigenvalue("sid", "token", "lock")).toHaveLength(64);
    expect(computeHandshakeDigest({ x: 1 })).toHaveLength(64);
  });
});
