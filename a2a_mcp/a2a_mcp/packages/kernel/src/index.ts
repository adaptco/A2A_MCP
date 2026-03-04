import Ajv from "ajv";
import addFormats from "ajv-formats";
import stableStringify from "stable-stringify";
import crypto from "crypto";
import cloneDeep from "lodash.clonedeep";
import stateSchema from "./schemas/state.schema.json";
import actionSchema from "./schemas/action.schema.json";

export type EntityKind = "Architect" | "Node" | "Conduit" | "Core" | "Anomaly" | "Drone";
export type ActionType =
  | "Move"
  | "PlayCard"
  | "Build"
  | "SyncData"
  | "SystemSpawn"
  | "ForgeRequest"
  | "ChronoSyncClaim";

export interface Entity {
  id: string;
  kind: EntityKind;
  owner?: string | null;
  q: number;
  r: number;
  hp: number;
  power: number;
}

export interface State {
  world_id: string;
  turn: number;
  coreSync: number;
  corruption: number;
  safety: number;
  resources: { compute: number; bandwidth: number; data: number };
  board: { entities: Entity[] };
  inventories: { players: { id: string; hand: string[]; deck: string[]; discard: string[] }[] };
  provenance: { forgeAssets: { id: string; tokenSeedHash: string; baseAssetId: string; styleClamp: number; url: string }[] };
}

export interface Action<TPayload = any> {
  type: ActionType;
  actor: string;
  payload: TPayload;
}

export interface ReduceResult {
  state: State;
  events: string[];
}

const ajv = new Ajv({ allErrors: true, removeAdditional: true, strict: true });
addFormats(ajv);
const validateState = ajv.compile<State>(stateSchema as any);
const validateAction = ajv.compile<Action>(actionSchema as any);

export function stableHash(input: unknown): string {
  return crypto.createHash("sha256").update(stableStringify(input)).digest("hex");
}

export function initialState(): State {
  return {
    world_id: "world-1",
    turn: 0,
    coreSync: 10,
    corruption: 0,
    safety: 10,
    resources: { compute: 3, bandwidth: 3, data: 3 },
    board: {
      entities: [
        { id: "architect", kind: "Architect", owner: "player-1", q: 0, r: 0, hp: 10, power: 2 },
        { id: "core", kind: "Core", owner: null, q: 0, r: 1, hp: 10, power: 0 },
        { id: "node-1", kind: "Node", owner: "player-1", q: 1, r: 0, hp: 5, power: 1 }
      ]
    },
    inventories: {
      players: [
        { id: "player-1", hand: ["boost", "shield"], deck: ["build", "move"], discard: [] }
      ]
    },
    provenance: { forgeAssets: [] }
  };
}

export function assertState(state: State): void {
  const valid = validateState(state);
  if (!valid) {
    throw new Error("Invalid state: " + ajv.errorsText(validateState.errors));
  }
}

export function assertAction(action: Action): void {
  const valid = validateAction(action);
  if (!valid) {
    throw new Error("Invalid action: " + ajv.errorsText(validateAction.errors));
  }
}

function findEntity(state: State, id: string): Entity | undefined {
  return state.board.entities.find((e) => e.id === id);
}

function moveEntity(state: State, entityId: string, q: number, r: number, events: string[]) {
  const entity = findEntity(state, entityId);
  if (!entity) throw new Error("Entity not found");
  entity.q = q;
  entity.r = r;
  events.push(`moved:${entityId}:${q},${r}`);
}

function playCard(state: State, actor: string, cardId: string, targetId: string, events: string[]) {
  const player = state.inventories.players.find((p) => p.id === actor);
  if (!player) throw new Error("player missing");
  if (!player.hand.includes(cardId)) throw new Error("card not in hand");
  const entity = findEntity(state, targetId);
  if (!entity) throw new Error("target missing");
  entity.hp += 1;
  player.hand = player.hand.filter((c) => c !== cardId);
  player.discard.push(cardId);
  state.resources.compute += 1;
  events.push(`card:${cardId}:buff:${targetId}`);
}

function buildStructure(state: State, actor: string, structure: "Node" | "Conduit", q: number, r: number, cost: State["resources"], events: string[]) {
  const player = state.inventories.players.find((p) => p.id === actor);
  if (!player) throw new Error("player missing");
  const occupied = state.board.entities.some((e) => e.q === q && e.r === r);
  if (occupied) throw new Error("occupied");
  if (state.resources.compute < cost.compute || state.resources.bandwidth < cost.bandwidth || state.resources.data < cost.data) {
    throw new Error("insufficient resources");
  }
  state.resources.compute -= cost.compute;
  state.resources.bandwidth -= cost.bandwidth;
  state.resources.data -= cost.data;
  const id = `${structure.toLowerCase()}-${state.board.entities.length + 1}`;
  state.board.entities.push({ id, kind: structure, owner: actor, q, r, hp: 4, power: 1 });
  events.push(`build:${id}`);
}

function syncData(state: State, nodeId: string, data: number, events: string[]) {
  const node = findEntity(state, nodeId);
  if (!node || node.kind !== "Node") throw new Error("node missing");
  state.coreSync = Math.min(100, state.coreSync + data);
  events.push(`sync:${nodeId}:${data}`);
}

function spawnSystem(state: State, spawnKind: EntityKind, q: number, r: number, power: number, hp: number, events: string[]) {
  const id = `${spawnKind.toLowerCase()}-${state.board.entities.length + 1}`;
  const occupied = state.board.entities.some((e) => e.q === q && e.r === r);
  if (occupied) throw new Error("occupied");
  state.board.entities.push({ id, kind: spawnKind, owner: null, q, r, hp, power });
  state.corruption += spawnKind === "Anomaly" ? 2 : 1;
  events.push(`spawn:${id}`);
}

function applyForge(state: State, payload: { tokenSeed: string; baseAssetId: string; styleClamp: number }) {
  const tokenSeedHash = stableHash(payload.tokenSeed);
  const record = {
    id: `asset-${state.provenance.forgeAssets.length + 1}`,
    tokenSeedHash,
    baseAssetId: payload.baseAssetId,
    styleClamp: payload.styleClamp,
    url: `https://assets.local/${tokenSeedHash}.glb`
  };
  state.provenance.forgeAssets.push(record);
  return record;
}

export function reduce(current: State, action: Action): ReduceResult {
  assertAction(action);
  const state = cloneDeep(current);
  assertState(state);
  const events: string[] = [];
  switch (action.type) {
    case "Move": {
      const { entityId, q, r } = action.payload as any;
      moveEntity(state, entityId, q, r, events);
      break;
    }
    case "PlayCard": {
      const { cardId, targetId } = action.payload as any;
      playCard(state, action.actor, cardId, targetId, events);
      break;
    }
    case "Build": {
      const { structure, q, r, cost } = action.payload as any;
      buildStructure(state, action.actor, structure, q, r, cost, events);
      break;
    }
    case "SyncData": {
      const { nodeId, data } = action.payload as any;
      syncData(state, nodeId, data, events);
      break;
    }
    case "SystemSpawn": {
      const { spawnKind, q, r, power, hp } = action.payload as any;
      spawnSystem(state, spawnKind, q, r, power, hp, events);
      break;
    }
    case "ForgeRequest": {
      const record = applyForge(state, action.payload as any);
      events.push(`forge:${record.id}`);
      break;
    }
    case "ChronoSyncClaim": {
      const { pidHash, rarityTier } = action.payload as any;
      state.provenance.forgeAssets.push({
        id: `tft-${state.provenance.forgeAssets.length + 1}`,
        tokenSeedHash: pidHash,
        baseAssetId: `tft-${rarityTier}`,
        styleClamp: rarityTier,
        url: `onchain://${pidHash}`
      });
      events.push(`claim:${pidHash}`);
      break;
    }
    default:
      throw new Error(`Unknown action ${(action as any).type}`);
  }
  state.turn += 1;
  assertState(state);
  return { state, events };
}

export function replay(initial: State, actions: Action[]): State {
  return actions.reduce((acc, action) => reduce(acc, action).state, cloneDeep(initial));
}

export function stateHash(state: State): string {
  return stableHash(state);
}

export { stateSchema, actionSchema, validateState, validateAction };
export * from "./physics";
