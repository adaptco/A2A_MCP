// Runtime control module for the Charley Fox -> Dot -> Gemini handoff.
export type WASDKey = "W" | "A" | "S" | "D";

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

export interface AgentState extends Vec3 {
  speed: number;
}

export interface TensorExchange {
  provider: "gemini";
  tokenEnv: "GEMINI_API_KEY";
  chatEndpoint: "/gemini/chat";
  embeddingEndpoint: "/gemini/embeddings";
  origin: Vec3;
  metric: "dot_product";
  vector: number[];
}

export interface ControlFrame {
  activeKeys: WASDKey[];
  reason: string;
  projectedTarget: Vec3;
  similarity: number;
}

const REFERENCE_AXIS: Vec3 = { x: 1, y: 1, z: 1 };

function magnitude(vector: Vec3): number {
  return Math.sqrt(vector.x ** 2 + vector.y ** 2 + vector.z ** 2);
}

function normalize(vector: Vec3): Vec3 {
  const length = magnitude(vector);
  if (length === 0) {
    return { x: 0, y: 0, z: 0 };
  }

  return {
    x: vector.x / length,
    y: vector.y / length,
    z: vector.z / length,
  };
}

function dotProduct(left: Vec3, right: Vec3): number {
  return left.x * right.x + left.y * right.y + left.z * right.z;
}

function projectTensor(vector: number[]): Vec3 {
  const [x = 0, y = 0, z = 0] = vector;
  return { x, y, z };
}

export class CharleyFoxGeminiDotWASDControlModule {
  static nextFrame(
    state: AgentState,
    exchange: TensorExchange,
    blocked: Set<WASDKey> = new Set(),
  ): ControlFrame {
    const projected = projectTensor(exchange.vector);
    const target = normalize({
      x: exchange.origin.x + projected.x,
      y: exchange.origin.y + projected.y,
      z: exchange.origin.z + projected.z,
    });
    const normalizedState = normalize(state);
    const dx = target.x - normalizedState.x;
    const dy = target.y - normalizedState.y;
    const horizontal: WASDKey = dx >= 0 ? "D" : "A";
    const vertical: WASDKey = dy >= 0 ? "W" : "S";
    const primary: WASDKey = Math.abs(dx) >= Math.abs(dy) ? horizontal : vertical;
    const secondary: WASDKey = primary === horizontal ? vertical : horizontal;

    const activeKeys: WASDKey[] = [];
    if (!blocked.has(primary)) {
      activeKeys.push(primary);
    }
    if (activeKeys.length === 0 && !blocked.has(secondary)) {
      activeKeys.push(secondary);
    }

    return {
      activeKeys,
      reason: activeKeys.length ? "dot_product_guided" : "all_directions_blocked",
      projectedTarget: target,
      similarity: dotProduct(target, normalize(REFERENCE_AXIS)),
    };
  }
}
