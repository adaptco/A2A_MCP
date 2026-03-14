import crypto from "crypto";

const DOMAIN = "PSP.MerkleRoot.v1";
const SHA_TAG_PREFIX = "sha256:";

function shaTagToBytes(tag: string): Buffer {
  if (!new RegExp(`^${SHA_TAG_PREFIX}[0-9a-f]{64}$`).test(tag)) {
    throw new Error(`bad sha tag: ${tag}`);
  }
  return Buffer.from(tag.slice(SHA_TAG_PREFIX.length), "hex");
}

function bytesToShaTag(bytes: Buffer): string {
  if (bytes.length !== 32) throw new Error("sha256 digest must be 32 bytes");
  return `${SHA_TAG_PREFIX}${bytes.toString("hex")}`;
}

function sha256Bytes(payload: Buffer): Buffer {
  return crypto.createHash("sha256").update(payload).digest();
}

export function pspMerkleRootFromTickHashes(tickHashes: string[]): string {
  if (tickHashes.length === 0) return `${SHA_TAG_PREFIX}${"0".repeat(64)}`;

  const domain = Buffer.from(DOMAIN, "utf8");
  const zero = Buffer.from([0x00]);
  let layer = tickHashes.map(shaTagToBytes);

  while (layer.length > 1) {
    const next: Buffer[] = [];
    for (let i = 0; i < layer.length; i += 2) {
      const left = layer[i];
      const right = layer[i + 1] ?? layer[i];
      const preimage = Buffer.concat([domain, zero, left, right]);
      next.push(sha256Bytes(preimage));
    }
    layer = next;
  }

  return bytesToShaTag(layer[0]);
}
