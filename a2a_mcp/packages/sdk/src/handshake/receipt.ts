import { canonicalizeForHash, computeHandshakeDigest } from "./crypto";

export type HandshakePayload = Record<string, unknown>;

export type HandshakeReceipt = {
  type: "handshake.receipt";
  digest: string;
  prev: string | null;
  payload: HandshakePayload;
  witness: {
    "handshake.bound": {
      digest: string;
      canonical_payload: string;
      prev: string | null;
    };
  };
};

export function buildHandshakeBoundWitness(payloadWithoutWallClockFields: HandshakePayload, prev: string | null): HandshakeReceipt {
  const canonical_payload = canonicalizeForHash(payloadWithoutWallClockFields);
  const digest = computeHandshakeDigest(payloadWithoutWallClockFields);

  return {
    type: "handshake.receipt",
    digest,
    prev,
    payload: payloadWithoutWallClockFields,
    witness: {
      "handshake.bound": {
        digest,
        canonical_payload,
        prev,
      },
    },
  };
}

export function chainHandshakeReceipt(
  payloadWithoutWallClockFields: HandshakePayload,
  previousReceipt: Pick<HandshakeReceipt, "digest"> | null,
): HandshakeReceipt {
  const prev = previousReceipt?.digest ?? null;
  return buildHandshakeBoundWitness(payloadWithoutWallClockFields, prev);
}
