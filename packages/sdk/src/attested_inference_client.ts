import crypto from "crypto";

type JsonRecord = Record<string, unknown>;

type LedgerSink = (record: JsonRecord) => Promise<void>;

type GetHash = () => Promise<string>;

type StreamFn = (body: JsonRecord) => AsyncIterable<string>;

type AttestedInferenceClientOptions = {
  model: string;
  reducer: string;
  ledgerSink: LedgerSink;
  getPreStateHash: GetHash;
  getPostStateHash: GetHash;
};

type ReceiptVerdict = "complete" | "aborted" | "timeout";

export class AttestedInferenceClient {
  private model: string;
  private reducer: string;
  private ledgerSink: LedgerSink;
  private getPreStateHash: GetHash;
  private getPostStateHash: GetHash;

  constructor(opts: AttestedInferenceClientOptions) {
    this.model = opts.model;
    this.reducer = opts.reducer;
    this.ledgerSink = opts.ledgerSink;
    this.getPreStateHash = opts.getPreStateHash;
    this.getPostStateHash = opts.getPostStateHash;
  }

  private sha256(payload: string): string {
    return crypto.createHash("sha256").update(payload, "utf8").digest("hex");
  }

  private merkleRoot(hashes: string[]): string {
    let layer = hashes.length > 0 ? hashes.slice() : [this.sha256("EMPTY")];

    while (layer.length > 1) {
      const next: string[] = [];
      for (let i = 0; i < layer.length; i += 2) {
        const left = layer[i];
        const right = layer[i + 1] ?? left;
        next.push(this.sha256(`${left}${right}`));
      }
      layer = next;
    }

    return layer[0];
  }

  async *stream(requestBody: JsonRecord, streamFn: StreamFn): AsyncIterable<string> {
    const callId = crypto.randomUUID();
    const timestampUtc = new Date().toISOString();
    const requestJson = JSON.stringify(requestBody);
    const requestHash = this.sha256(requestJson);
    const preStateHash = await this.getPreStateHash();

    await this.ledgerSink({
      schema_version: "InferenceCall.v1",
      call_id: callId,
      timestamp_utc: timestampUtc,
      model: this.model,
      request_hash: requestHash,
      reducer: this.reducer,
      pre_state_hash: preStateHash
    });

    let seq = 0;
    let cumulativeHash = this.sha256("");
    const tokenHashes: string[] = [];
    let fullOutput = "";
    let verdict: ReceiptVerdict = "complete";
    let caughtError: unknown;

    try {
      for await (const token of streamFn(requestBody)) {
        const tokenHash = this.sha256(token);
        cumulativeHash = this.sha256(`${cumulativeHash}${tokenHash}`);
        tokenHashes.push(tokenHash);
        fullOutput += token;

        await this.ledgerSink({
          schema_version: "TokenEvent.v1",
          call_id: callId,
          seq,
          token,
          token_hash: tokenHash,
          cumulative_hash: cumulativeHash
        });

        seq += 1;
        yield token;
      }
    } catch (error) {
      verdict = "aborted";
      caughtError = error;
    }

    const outputHash = this.sha256(fullOutput);
    const postStateHash = await this.getPostStateHash();
    const merkleRoot = this.merkleRoot(tokenHashes);

    await this.ledgerSink({
      schema_version: "InferenceReceipt.v1",
      call_id: callId,
      post_state_hash: postStateHash,
      output_hash: outputHash,
      merkle_root: merkleRoot,
      verdict
    });

    if (caughtError) {
      throw caughtError;
    }
  }
}
