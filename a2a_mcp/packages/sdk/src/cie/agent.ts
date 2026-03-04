import { AgentContext } from "./ingestion";

export interface AgentObservation {
  tick: number;
  psp_live?: string;
  telemetry: Record<string, unknown>;
}

export interface AgentAction {
  tick: number;
  commands: Record<string, unknown>;
}

export interface CieV2Agent {
  init(ctx: AgentContext): void;
  sense(obs: AgentObservation): void;
  decide(): AgentAction | null;
  act(action: AgentAction): void;
}

export class SimpleCieV2Agent implements CieV2Agent {
  private ctx!: AgentContext;
  private lastObs: AgentObservation | null = null;

  init(ctx: AgentContext): void {
    this.ctx = ctx;
  }

  sense(obs: AgentObservation): void {
    this.lastObs = obs;
  }

  decide(): AgentAction | null {
    if (!this.lastObs) return null;

    const stability = this.ctx.invariants.invariants.stability.stability_score;
    const risk = 1 - stability;

    if (risk > 0.3) {
      return {
        tick: this.lastObs.tick,
        commands: { mode: "conservative", target_speed_scale: 0.8 },
      };
    }

    return {
      tick: this.lastObs.tick,
      commands: { mode: "normal" },
    };
  }

  act(action: AgentAction): void {
    // In a real system, this would enqueue InputDelta or high-level commands.
    console.log("Agent action at tick", action.tick, action.commands);
  }
}
