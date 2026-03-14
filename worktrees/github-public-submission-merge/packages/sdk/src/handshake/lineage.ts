import { createHash } from "node:crypto";

export interface NdjsonWitness {
  format: "ndjson";
  line_number: number;
  stream_id: string;
}

export interface HandshakeEvent {
  kind: string;
  session_id: string;
  event_id: string;
  prev?: string;
  entropy_threshold: number;
  han_eigenvalue: number;
  lineage_witness: NdjsonWitness;
  [key: string]: unknown;
}

export interface SessionLineage {
  sessionId: string;
  events: HandshakeEvent[];
  revoked: boolean;
  revokedAtEventId?: string;
  seenEventIds: Set<string>;
}

export function computeHanEigenvalue(event: Pick<HandshakeEvent, "kind" | "session_id" | "event_id" | "prev" | "entropy_threshold">): number {
  const basis = [
    event.kind,
    event.session_id,
    event.event_id,
    String(event.prev ?? ""),
    String(event.entropy_threshold)
  ].join("|");
  const digest = sha256Hex(basis).slice(0, 12);
  const normalized = parseInt(digest, 16) / (16 ** 12 - 1);
  return Number(normalized.toFixed(6));
}

export function parseNdjsonEvents(ndjson: string): HandshakeEvent[] {
  return ndjson
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(line);
      } catch {
        throw new Error(`Invalid JSON at NDJSON line ${index + 1}`);
      }

      if (!isHandshakeEvent(parsed)) {
        throw new Error(`Invalid handshake event shape at NDJSON line ${index + 1}`);
      }

      const expectedEigenvalue = computeHanEigenvalue(parsed);
      if (Number(parsed.han_eigenvalue.toFixed(6)) !== expectedEigenvalue) {
        throw new Error(
          `Invalid han_eigenvalue at NDJSON line ${index + 1}: expected ${expectedEigenvalue}, got ${parsed.han_eigenvalue}`
        );
      }

      if (parsed.lineage_witness.line_number !== index + 1) {
        throw new Error(
          `Invalid NDJSON witness line_number at NDJSON line ${index + 1}: expected ${index + 1}, got ${parsed.lineage_witness.line_number}`
        );
      }

      return parsed;
    });
}

export function reconstructSessionLineageFromNdjson(ndjson: string): Map<string, SessionLineage> {
  return reconstructSessionLineage(parseNdjsonEvents(ndjson));
}

export function reconstructSessionLineage(events: HandshakeEvent[]): Map<string, SessionLineage> {
  const bySession = new Map<string, SessionLineage>();

  for (const event of events) {
    const lineage = bySession.get(event.session_id) ?? {
      sessionId: event.session_id,
      events: [],
      revoked: false,
      seenEventIds: new Set<string>()
    };

    if (lineage.seenEventIds.has(event.event_id)) {
      throw new Error(`Invalid lineage for session ${event.session_id}: duplicate event_id=${event.event_id}`);
    }

    const previousEvent = lineage.events[lineage.events.length - 1];
    if (previousEvent && event.prev !== previousEvent.event_id) {
      throw new Error(
        `Invalid lineage for session ${event.session_id}: expected prev=${previousEvent.event_id}, got prev=${String(event.prev)}`
      );
    }

    if (
      lineage.revoked &&
      (event.kind === "handshake.fossilized" || event.kind === "handshake.bound")
    ) {
      throw new Error(
        `Invalid lineage for session ${event.session_id}: ${event.kind} after revocation at ${lineage.revokedAtEventId}`
      );
    }

    lineage.events.push(event);
    lineage.seenEventIds.add(event.event_id);

    if (event.kind === "handshake.revoked") {
      lineage.revoked = true;
      lineage.revokedAtEventId = event.event_id;
    }

    bySession.set(event.session_id, lineage);
  }

  return bySession;
}

function isHandshakeEvent(value: unknown): value is HandshakeEvent {
  if (!value || typeof value !== "object") {
    return false;
  }

  const record = value as Record<string, unknown>;
  const witness = record.lineage_witness as Record<string, unknown> | undefined;
  return (
    typeof record.kind === "string" &&
    typeof record.session_id === "string" &&
    typeof record.event_id === "string" &&
    (record.prev === undefined || typeof record.prev === "string") &&
    typeof record.entropy_threshold === "number" &&
    Number.isFinite(record.entropy_threshold) &&
    typeof record.han_eigenvalue === "number" &&
    Number.isFinite(record.han_eigenvalue) &&
    !!witness &&
    witness.format === "ndjson" &&
    typeof witness.stream_id === "string" &&
    witness.stream_id.length > 0 &&
    typeof witness.line_number === "number" &&
    Number.isInteger(witness.line_number) &&
    witness.line_number > 0
  );
}

function sha256Hex(input: string): string {
  return createHash("sha256").update(input, "utf8").digest("hex");
}
