import { promises as fs } from "fs";
import path from "path";
import { canonicalizeForHash } from "./crypto";

export const DEFAULT_LEDGER_EVENTS_PATH = path.join("sentinel", "ledger", "events", "handshake.ndjson");

export async function appendWitnessRecord(record: unknown, ledgerPath = DEFAULT_LEDGER_EVENTS_PATH): Promise<void> {
  const canonicalLine = `${canonicalizeForHash(record)}\n`;
  const writeBuffer = Buffer.from(canonicalLine, "utf8");

  if (writeBuffer.length === 0) {
    throw new Error("Refusing to write empty witness record.");
  }

  await fs.mkdir(path.dirname(ledgerPath), { recursive: true });
  const fileHandle = await fs.open(ledgerPath, "a");

  try {
    const { bytesWritten } = await fileHandle.write(writeBuffer, 0, writeBuffer.length, null);
    if (bytesWritten !== writeBuffer.length) {
      throw new Error(`Partial witness write detected (${bytesWritten}/${writeBuffer.length}).`);
    }
  } finally {
    await fileHandle.close();
  }
}
