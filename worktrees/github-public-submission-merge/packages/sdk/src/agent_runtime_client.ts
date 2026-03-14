import axios, { AxiosInstance } from "axios";

type Json = Record<string, unknown>;

type TokenizeResponse = { tokens: unknown[] };

type EncodeResponse = { stream: number[] };

type QubeResponse = { qube: unknown; digest: string; receipt: unknown };

type BuildCheckpointRequest = {
  prompt: string;
  seed: number;
  tensorSpec: string;
  strict?: boolean;
};

export class AgentRuntimeClient {
  private client: AxiosInstance;

  constructor(private baseUrl = "http://localhost:8787") {
    this.client = axios.create({ baseURL: this.baseUrl });
  }

  async post<T>(path: string, body: Json): Promise<T> {
    const res = await this.client.post<T>(path, body);
    return res.data;
  }

  async buildCheckpoint(req: BuildCheckpointRequest) {
    const tokens = await this.post<TokenizeResponse>("/tokenize", {
      prompt: req.prompt,
      strict: req.strict ?? true
    });

    const enc = await this.post<EncodeResponse>("/encode", {
      tokens: tokens.tokens,
      seed: req.seed,
      tensorSpec: req.tensorSpec
    });

    const qube = await this.post<QubeResponse>("/qube", {
      stream: enc.stream,
      tensorSpec: req.tensorSpec,
      seed: req.seed
    });

    return { tokens, enc, qube };
  }

  async verify(digest: string) {
    return this.post("/verify", { digest });
  }

  async replay(digest: string) {
    return this.post("/replay", { digest });
  }
}
