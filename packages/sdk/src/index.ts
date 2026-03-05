import axios from "axios";
import { Action, State } from "@world-os/kernel";
export * from "./agent_field";
export * from "./agent_runtime_client";
export * from "./attested_inference_client";
export * from "./cie/agent";
export * from "./cie/ingestion";
export * from "./cie/types";

export interface ApiClientOptions {
  baseUrl: string;
}

export class ApiClient {
  constructor(private opts: ApiClientOptions) {}

  async health() {
    const res = await axios.get(`${this.opts.baseUrl}/health`);
    return res.data;
  }

  async getState(): Promise<{ state: State; hash: string }> {
    const res = await axios.get(`${this.opts.baseUrl}/game/state`);
    return res.data;
  }

  async proposeIntent(chat: string) {
    const res = await axios.post(`${this.opts.baseUrl}/game/intent`, { chat });
    return res.data as { action: Action; reasoning: string };
  }

  async act(action: Action) {
    const res = await axios.post(`${this.opts.baseUrl}/game/act`, action);
    return res.data as { state: State; events: string[]; hash: string };
  }

  async chronoChallenge(key: string, wallet: string) {
    const res = await axios.post(`${this.opts.baseUrl}/chrono/challenge`, { key, wallet });
    return res.data;
  }

  async chronoClaim(payload: any) {
    const res = await axios.post(`${this.opts.baseUrl}/chrono/claim`, payload);
    return res.data;
  }

  async forgeRequest(payload: { tokenSeed: string; baseAssetId: string; styleClamp: number }) {
    const res = await axios.post(`${this.opts.baseUrl}/forge/request`, payload);
    return res.data;
  }

  async forgeAssets() {
    const res = await axios.get(`${this.opts.baseUrl}/forge/assets`);
    return res.data;
  }
}

export * from "@world-os/kernel";
