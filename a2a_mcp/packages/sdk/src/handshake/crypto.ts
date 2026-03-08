import { createHash } from "crypto";

const WALL_CLOCK_FIELDS = new Set([
  "wall_clock_ms",
  "wall_clock_ns",
  "wall_clock_ts",
  "timestamp",
  "created_at",
  "updated_at",
]);

function stripWallClockFields<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => stripWallClockFields(item)) as T;
  }

  if (value && typeof value === "object") {
    const canonical: Record<string, unknown> = {};
    for (const key of Object.keys(value as Record<string, unknown>).sort()) {
      if (WALL_CLOCK_FIELDS.has(key)) {
        continue;
      }
      canonical[key] = stripWallClockFields((value as Record<string, unknown>)[key]);
    }
    return canonical as T;
  }

  return value;
}

export function canonicalizeForHash(obj: unknown): string {
  return JSON.stringify(stripWallClockFields(obj));
}

export function computeHanEigenvalue(session_id: string, vanguard_token: string, lock_phrase: string): string {
  return createHash("sha256")
    .update(`${session_id}:${vanguard_token}:${lock_phrase}`, "utf8")
    .digest("hex");
}

export function computeHandshakeDigest(payloadWithoutWallClockFields: unknown): string {
  const canonical = canonicalizeForHash(payloadWithoutWallClockFields);
  return createHash("sha256").update(canonical, "utf8").digest("hex");
}

export { WALL_CLOCK_FIELDS };
