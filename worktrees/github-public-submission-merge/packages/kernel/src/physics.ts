import crypto from "crypto";

export type Vector3 = [number, number, number];
export type Vector4 = [number, number, number, number];
export type Rank3Tensor = number[][][];

export type BooAvatarId = "boo-1" | "boo-2" | "boo-3" | "boo-4" | "boo-5" | "boo-6";
export type QubeFace = "U" | "D" | "L" | "R" | "F" | "B";

export interface BooAvatar {
  id: BooAvatarId;
  label: string;
  role: string;
  q: number;
  r: number;
}

export interface HexTile {
  center: { q: number; r: number };
  radius: number;
  vertices: { q: number; r: number }[];
}

export interface RuntimePlane {
  avatars: BooAvatar[];
  tile: HexTile;
}

export interface QubeToken {
  seed: string;
  faces: Record<QubeFace, string[]>;
}

export interface Expert {
  id: string;
  specialty: string;
  parameters: Record<string, number>;
}

export interface AgentModel {
  id: string;
  embedding: number[];
  model: string;
}

export interface MixtureAssignment {
  agentId: string;
  expertId: string;
  weight: number;
}

export interface ScaffoldEntry {
  token: string;
  agentId: string;
  expertId: string;
  weight: number;
}

export interface AttentionLoop {
  embedding: number[];
  weights: number[];
  xml: string;
}

export interface EpochPlan {
  id: string;
  title: string;
  summary: string;
  steps: string[];
}

function hashSeed(seed: string): string {
  return crypto.createHash("sha256").update(seed).digest("hex");
}

function normalizeWeights(values: number[]): number[] {
  const total = values.reduce((sum, value) => sum + value, 0);
  if (total === 0) return values.map(() => 0);
  return values.map((value) => value / total);
}

export function createHexTile(center: { q: number; r: number }, radius: number): HexTile {
  const vertices = [
    { q: center.q + radius, r: center.r },
    { q: center.q + radius, r: center.r - radius },
    { q: center.q, r: center.r - radius },
    { q: center.q - radius, r: center.r },
    { q: center.q - radius, r: center.r + radius },
    { q: center.q, r: center.r + radius }
  ];
  return { center, radius, vertices };
}

export function createBooPlane(): RuntimePlane {
  const avatars: BooAvatar[] = [
    { id: "boo-1", label: "Beacon", role: "anchor", q: 0, r: 1 },
    { id: "boo-2", label: "Beryl", role: "stabilizer", q: 1, r: 0 },
    { id: "boo-3", label: "Brim", role: "scout", q: 1, r: -1 },
    { id: "boo-4", label: "Braid", role: "weaver", q: 0, r: -1 },
    { id: "boo-5", label: "Bishop", role: "guardian", q: -1, r: 0 },
    { id: "boo-6", label: "Bloom", role: "scribe", q: -1, r: 1 }
  ];
  return { avatars, tile: createHexTile({ q: 0, r: 0 }, 1) };
}

export function createQubeToken(seed: string): QubeToken {
  const faces: Record<QubeFace, string[]> = { U: [], D: [], L: [], R: [], F: [], B: [] };
  const hashed = hashSeed(seed);
  const faceKeys: QubeFace[] = ["U", "D", "L", "R", "F", "B"];
  faceKeys.forEach((face, faceIndex) => {
    for (let i = 0; i < 9; i += 1) {
      faces[face].push(`${face}-${hashed.slice(faceIndex * 4, faceIndex * 4 + 4)}-${i}`);
    }
  });
  return { seed, faces };
}

export function createRank3Tensor(dimensions: Vector3, initialValue = 0): Rank3Tensor {
  const [x, y, z] = dimensions;
  return Array.from({ length: x }, () => Array.from({ length: y }, () => Array.from({ length: z }, () => initialValue)));
}

export function tensorEnergy(tensor: Rank3Tensor): number {
  return tensor.reduce((sum, matrix) => sum + matrix.reduce((rowSum, row) => rowSum + row.reduce((cellSum, cell) => cellSum + Math.abs(cell), 0), 0), 0);
}

export function filterSignal(samples: number[], alpha: number): number[] {
  if (samples.length === 0) return [];
  const filtered: number[] = [samples[0]];
  for (let i = 1; i < samples.length; i += 1) {
    filtered.push(alpha * samples[i] + (1 - alpha) * filtered[i - 1]);
  }
  return filtered;
}

export function enthalpyDelta(samples: number[]): number {
  if (samples.length < 2) return 0;
  return samples.slice(1).reduce((sum, value, index) => sum + Math.abs(value - samples[index]), 0);
}

export function evaluateFuzzy4D(input: Vector4, thresholds: Vector4): Vector4 {
  return input.map((value, index) => {
    const threshold = thresholds[index];
    if (threshold <= 0) return 0;
    return Math.min(1, Math.max(0, value / threshold));
  }) as Vector4;
}

export function weightsToXml(labels: string[], weights: number[]): string {
  const normalized = normalizeWeights(weights);
  const entries = labels.map((label, index) => `  <weight id="${label}" value="${normalized[index] ?? 0}" />`).join("\n");
  return `<weights>\n${entries}\n</weights>`;
}

export function buildAttentionLoop(embedding: number[], labels: string[]): AttentionLoop {
  const weights = normalizeWeights(embedding.map((value) => Math.abs(value)));
  return {
    embedding,
    weights,
    xml: weightsToXml(labels, weights)
  };
}

export function mixExperts(agents: AgentModel[], experts: Expert[], weightMatrix: number[][]): MixtureAssignment[] {
  return agents.flatMap((agent, agentIndex) => {
    const row = weightMatrix[agentIndex] ?? [];
    const normalized = normalizeWeights(experts.map((_, index) => row[index] ?? 0));
    return experts.map((expert, expertIndex) => ({
      agentId: agent.id,
      expertId: expert.id,
      weight: normalized[expertIndex] ?? 0
    }));
  });
}

export function buildScaffoldTable(assignments: MixtureAssignment[], tokens: string[]): ScaffoldEntry[] {
  return assignments.map((assignment, index) => ({
    token: tokens[index % tokens.length],
    agentId: assignment.agentId,
    expertId: assignment.expertId,
    weight: assignment.weight
  }));
}

export function flattenTo1DTokens(matrix: number[][], prefix = "token"): string[] {
  return matrix.flatMap((row, rowIndex) => row.map((_, colIndex) => `${prefix}-${rowIndex}-${colIndex}`));
}

export function createEpochPlan(title: string, summary: string, steps: string[]): EpochPlan {
  const id = hashSeed(`${title}:${summary}`).slice(0, 12);
  return { id, title, summary, steps };
}

export function orchestratePhysicsRuntime(params: {
  embedding: number[];
  labels: string[];
  experts: Expert[];
  agents: AgentModel[];
  weightMatrix: number[][];
  tensorDimensions: Vector3;
  signalSamples: number[];
  qubeSeed: string;
}) {
  const attention = buildAttentionLoop(params.embedding, params.labels);
  const plane = createBooPlane();
  const qube = createQubeToken(params.qubeSeed);
  const tensor = createRank3Tensor(params.tensorDimensions, 0);
  const energy = tensorEnergy(tensor);
  const filteredSignal = filterSignal(params.signalSamples, 0.3);
  const enthalpy = enthalpyDelta(filteredSignal);
  const assignments = mixExperts(params.agents, params.experts, params.weightMatrix);
  const tokens = flattenTo1DTokens(params.weightMatrix, "agent");
  const scaffold = buildScaffoldTable(assignments, tokens);

  return {
    attention,
    plane,
    qube,
    tensor,
    energy,
    filteredSignal,
    enthalpy,
    assignments,
    scaffold
  };
}
