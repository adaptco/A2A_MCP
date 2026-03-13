import { describe, it, expect } from "vitest";
import { initialState, reduce, replay, stateHash, Action } from "../src";

const sampleActions: Action[] = [
  { type: "Move", actor: "player-1", payload: { entityId: "architect", q: 1, r: 1 } },
  { type: "PlayCard", actor: "player-1", payload: { cardId: "boost", targetId: "architect", time: 1 } },
  { type: "Build", actor: "player-1", payload: { structure: "Node", q: 2, r: 0, cost: { compute: 1, bandwidth: 1, data: 1 } } },
  { type: "SyncData", actor: "player-1", payload: { nodeId: "node-1", data: 5, time: 2 } }
];

describe("deterministic reducer", () => {
  it("replays deterministically", () => {
    const first = replay(initialState(), sampleActions);
    const second = replay(initialState(), sampleActions);
    expect(first).toEqual(second);
    expect(stateHash(first)).toEqual(stateHash(second));
  });

  it("rejects invalid actions", () => {
    expect(() => reduce(initialState(), { type: "Move", actor: "player-1", payload: { entityId: "none", q: 0, r: 0 } })).toThrow();
  });
});
