import type { PamRequestType, PamRuntimeLane } from "./pam.js";

export type WhamRouteId = "office-hub" | "parker-mission";
export type WhamControlMode = "human-in-the-loop";
export type WhamDirection = "up" | "down" | "left" | "right";
export type WhamInputKind =
  | "move"
  | "interact"
  | "route"
  | "toggle_terminal"
  | "checkpoint_commit"
  | "auto_fix";
export type WhamChatTarget = "npc" | "terminal";

export interface WhamPosition {
  x: number;
  y: number;
}

export interface WhamAvatarSnapshot extends WhamPosition {
  avatarId: string;
  displayName: string;
  heading: WhamDirection;
  state:
    | "idle"
    | "walking"
    | "interacting"
    | "checkpoint_ready"
    | "terminal_active";
  routeId: WhamRouteId;
  zoneId: string;
  nearbyNpcId?: string | null;
  nearbyCheckpointId?: string | null;
}

export interface WhamNpcSummary extends WhamPosition {
  npcId: string;
  name: string;
  role: string;
  agentRole: string;
  zId: string;
  loraRank: number;
  domain: string;
  intro: string;
  promptStyle: string;
}

export interface WhamOfficeScene {
  zoneId: string;
  rooms: Array<{
    roomId: string;
    label: string;
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
  npcs: WhamNpcSummary[];
  focusNpcId?: string | null;
}

export interface WhamCheckpointSnapshot extends WhamPosition {
  checkpointId: string;
  label: string;
  reached: boolean;
}

export interface WhamMissionScene {
  zoneId: string;
  width: number;
  height: number;
  walls: WhamPosition[];
  exitPortal: WhamPosition;
  checkpoints: WhamCheckpointSnapshot[];
  objective: string;
}

export interface WhamTerminalEntry {
  entryId: string;
  source: "user" | "system" | "agent";
  message: string;
  tick: number;
}

export interface WhamCheckpointArtifact {
  schema_version: "world.foundation.checkpoint.v1";
  checkpoint_id: string;
  assignment_id: string;
  session_id: string;
  route_id: WhamRouteId;
  hub_zone: string;
  mission_zone: string;
  avatar: WhamAvatarSnapshot;
  input_stream_stats: {
    total_inputs: number;
    move_inputs: number;
    interact_inputs: number;
    terminal_queries: number;
  };
  scenario_ref: string;
  wasd_module_ref: string;
}

export interface WhamSessionSnapshot {
  sessionId: string;
  routeId: WhamRouteId;
  controlMode: WhamControlMode;
  tick: number;
  avatar: WhamAvatarSnapshot;
  office: WhamOfficeScene;
  mission: WhamMissionScene;
  terminalOpen: boolean;
  terminalLog: WhamTerminalEntry[];
  checkpoint?: WhamCheckpointArtifact | null;
  assignmentId: string;
  scenarioPath: string;
  wasdModulePath: string;
  pam?: PamRuntimeLane;
}

export interface WhamInputRequest {
  kind: WhamInputKind;
  direction?: WhamDirection;
  routeId?: WhamRouteId;
  actor?: "human" | "agent";
  requestType?: PamRequestType;
  nodeId?: string;
  violationId?: string;
}

export interface WhamReplayEvent {
  tick: number;
  type: string;
  routeId: WhamRouteId;
  detail: Record<string, unknown>;
}

export interface WhamInputResponse {
  session: WhamSessionSnapshot;
  replayEvent: WhamReplayEvent;
}

export interface WhamChatRequest {
  target: WhamChatTarget;
  message: string;
  npcId?: string;
}

export interface WhamChatResponse {
  session: WhamSessionSnapshot;
  reply: {
    target: WhamChatTarget;
    speakerId: string;
    message: string;
  };
  suggestedAction?: {
    kind: WhamInputKind;
    direction?: WhamDirection;
    rationale: string;
  };
}
