import axios from "axios";
import { Action, State } from "@world-os/kernel";
import type { PamLaneResponse } from "./pam.js";
import type {
  WhamChatRequest,
  WhamChatResponse,
  WhamInputRequest,
  WhamInputResponse,
  WhamReplayEvent,
  WhamSessionSnapshot,
} from "./wham.js";

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

  async chronoClaim(payload: unknown) {
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

  async getPamLane(): Promise<PamLaneResponse> {
    const res = await axios.get(`${this.opts.baseUrl}/pam/lane`);
    return res.data as PamLaneResponse;
  }

  async getWhamSession(): Promise<WhamSessionSnapshot> {
    const res = await axios.get(`${this.opts.baseUrl}/wham/session`);
    return res.data as WhamSessionSnapshot;
  }

  async sendWhamInput(payload: WhamInputRequest): Promise<WhamInputResponse> {
    const res = await axios.post(`${this.opts.baseUrl}/wham/input`, payload);
    return res.data as WhamInputResponse;
  }

  async sendWhamChat(payload: WhamChatRequest): Promise<WhamChatResponse> {
    const res = await axios.post(`${this.opts.baseUrl}/wham/chat`, payload);
    return res.data as WhamChatResponse;
  }

  async getWhamReplay(): Promise<{ events: WhamReplayEvent[] }> {
    const res = await axios.get(`${this.opts.baseUrl}/wham/replay`);
    return res.data as { events: WhamReplayEvent[] };
  }
}
