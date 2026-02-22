import { interpretState } from "./interpreter.js";
import { computeReward } from "./reward.js";

export class RAGBridge {
  constructor(eventBus, petRef, opts = {}) {
    this.bus = eventBus;
    this.petRef = petRef;

    this.lastEventId = 0;
    this.chapter = null;
    this.lastClosedChapter = null;

    this.maxChapterSeconds = opts.maxChapterSeconds ?? 20;
    this.thresholds = {
      hungerBands: [40, 70, 85, 100],
      energyBands: [70, 30, 20, 0],
      cleanBands: [70, 40, 25, 0],
      joyBands: [70, 35, 25, 0],
    };

    this.bus.subscribe((evt) => this.onEvent(evt));
  }

  onEvent(evt) {
    if (evt.sim_t == null) return;

    const snapshot = this.petRef.snapshot();
    if (!snapshot) return;

    if (!this.chapter) this.startChapter(snapshot, evt.sim_t, "init");

    this.chapter.events.push(minEvent(evt));

    if (isAction(evt.type)) {
      this.closeChapter(snapshot, evt.sim_t, `action:${evt.type}`);
      this.startChapter(snapshot, evt.sim_t, `post:${evt.type}`);
    }
  }

  pulse(sim_t) {
    const snapshot = this.petRef.snapshot();
    if (!snapshot) return null;

    if (!this.chapter) this.startChapter(snapshot, sim_t, "pulse");

    const prev = this.chapter.lastSnapshot;
    const prevInterp = interpretState(prev);
    const nextInterp = interpretState(snapshot);

    const timeExceeded =
      sim_t - this.chapter.startSimT >= this.maxChapterSeconds;
    const moodChanged = prev.mood !== snapshot.mood;
    const urgencyChanged = prevInterp.urgency !== nextInterp.urgency;
    const crossed = this.crossedThreshold(prev, snapshot);
    const died = prev.alive && !snapshot.alive;

    if (died || moodChanged || urgencyChanged || crossed || timeExceeded) {
      const reason = died
        ? "death"
        : moodChanged
          ? "mood"
          : urgencyChanged
            ? "urgency"
            : crossed
              ? "threshold"
              : "time";
      this.closeChapter(snapshot, sim_t, reason);
      this.startChapter(snapshot, sim_t, "continue");
      return this.lastClosedChapter ?? null;
    }

    this.chapter.lastSnapshot = snapshot;
    return null;
  }

  exportBatchForEmbedding() {
    const out = this.lastClosedChapter ?? null;
    this.lastClosedChapter = null;
    return out;
  }

  startChapter(snapshot, sim_t, reason) {
    this.chapter = {
      chapter_id: cryptoUUID(),
      startSimT: sim_t,
      startSnapshot: snapshot,
      lastSnapshot: snapshot,
      startReason: reason,
      events: [],
    };
  }

  closeChapter(endSnapshot, sim_t, reason) {
    const ch = this.chapter;
    if (!ch) return;

    ch.lastSnapshot = endSnapshot;
    const start = ch.startSnapshot;
    const end = endSnapshot;
    const startInterp = interpretState(start);
    const endInterp = interpretState(end);

    const reward = computeReward(start, end);

    const embedding_text = interpretChapterText(
      ch,
      startInterp,
      endInterp,
      reward,
      reason
    );

    this.lastClosedChapter = {
      chapter_id: ch.chapter_id,
      window: {
        start_t: start.t,
        end_t: end.t,
        duration_s: round3(end.t - start.t),
        boundary_reason: reason,
        start_reason: ch.startReason,
      },
      sar: {
        state: start,
        actions: ch.events.filter(
          (e) => isAction(e.type) || e.type === "agent_command"
        ),
        reward,
        next_state: end,
      },
      trajectory: {
        start_mood: start.mood,
        end_mood: end.mood,
        start_urgency: startInterp.urgency,
        end_urgency: endInterp.urgency,
        priorities_end: endInterp.priorities,
        alive_end: end.alive,
        cause_of_death: end.causeOfDeath,
      },
      summary: endInterp.text,
      embedding_text,
      metadata: {
        context_role: "petsim_kernel",
        lora_tags: ["physicspetcorerank8"],
        sim_time: { start: start.t, end: end.t },
      },
    };

    this.chapter = null;
  }

  crossedThreshold(a, b) {
    return (
      band(a.hunger, this.thresholds.hungerBands) !==
        band(b.hunger, this.thresholds.hungerBands) ||
      band(a.energy, this.thresholds.energyBands) !==
        band(b.energy, this.thresholds.energyBands) ||
      band(a.cleanliness, this.thresholds.cleanBands) !==
        band(b.cleanliness, this.thresholds.cleanBands) ||
      band(a.joy, this.thresholds.joyBands) !==
        band(b.joy, this.thresholds.joyBands)
    );
  }
}

function isAction(type) {
  return type === "player_action" || type === "agent_action";
}

function minEvent(evt) {
  return {
    id: evt.id,
    sim_t: evt.sim_t,
    type: evt.type,
    payload: evt.payload,
    meta: evt.meta,
  };
}

function interpretChapterText(ch, startInterp, endInterp, reward, reason) {
  const actions = ch.events
    .filter(
      (e) =>
        e.type === "player_action" ||
        e.type === "agent_action" ||
        e.type === "agent_command"
    )
    .map((e) => `${e.type}:${JSON.stringify(e.payload)}`)
    .slice(0, 8);

  return [
    `Life Chapter ${ch.chapter_id}`,
    `Window: t=${ch.startSnapshot.t}s → t=${ch.lastSnapshot.t}s (boundary=${reason})`,
    `Start: ${startInterp.text}`,
    `End: ${endInterp.text}`,
    `Actions: ${actions.length ? actions.join(" | ") : "none"}`,
    `Reward: ${reward}`,
  ].join("\n");
}

function band(value, bands) {
  for (let i = 0; i < bands.length; i += 1) {
    if (value <= bands[i]) return i;
  }
  return bands.length;
}

function round3(value) {
  return Math.round(value * 1000) / 1000;
}

function cryptoUUID() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return "xxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
