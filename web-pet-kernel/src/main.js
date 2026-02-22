import { EventBus } from "./eventBus.js";
import { GameLoop } from "./gameLoop.js";
import { RAGBridge } from "./ragBridge.js";

const canvas = document.getElementById("game-canvas");
const terminalLog = document.getElementById("terminal-log");
const terminalInput = document.getElementById("terminal-input");

const bus = new EventBus();
const game = new GameLoop(canvas, bus);

const rag = new RAGBridge(bus, { snapshot: () => game.pet.snapshot() }, {
  maxChapterSeconds: 20,
});

bus.subscribe((evt) => {
  const line = document.createElement("div");
  const timestamp =
    evt.sim_t != null
      ? `t=${evt.sim_t.toFixed(2)}s`
      : new Date(evt.wall_ts).toISOString();
  line.textContent = `[${timestamp}] ${evt.type} :: ${JSON.stringify(
    evt.payload
  )}`;
  terminalLog.appendChild(line);
  terminalLog.scrollTop = terminalLog.scrollHeight;
});

setInterval(() => {
  const snapshot = game.pet.snapshot();
  const closed = rag.pulse(snapshot.t);
  if (closed) {
    bus.emit(
      "telemetry_chapter",
      { chapter_id: closed.chapter_id },
      { sim_t: snapshot.t, source: "telemetry" }
    );
    console.log("Closed chapter:", closed);
  }
}, 500);

terminalInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") return;

  const cmd = terminalInput.value.trim();
  if (!cmd) return;
  terminalInput.value = "";

  const snapshot = game.pet.snapshot();

  bus.emit(
    "agent_command",
    { cmd },
    { sim_t: snapshot.t, source: "terminal", tags: { agent_id: "human_terminal" } }
  );

  if (cmd === "feed") act("feed", () => game.pet.feed(25));
  else if (cmd === "rest") act("rest", () => game.pet.rest(25));
  else if (cmd === "clean") act("clean", () => game.pet.clean(25));
  else if (cmd === "play") act("play", () => game.pet.play(20));
  else if (cmd === "export_chapter") {
    const chapter = rag.exportBatchForEmbedding();
    bus.emit("rag_export", { chapter }, { sim_t: snapshot.t, source: "rag" });
    console.log("RAG export:", chapter);
  } else {
    bus.emit(
      "agent_error",
      { error: "Unknown command", cmd },
      { sim_t: snapshot.t, source: "terminal" }
    );
  }

  function act(action, fn) {
    fn();
    const updated = game.pet.snapshot();
    bus.emit(
      "agent_action",
      { action },
      {
        sim_t: updated.t,
        source: "terminal",
        tags: { agent_id: "human_terminal" },
      }
    );
  }
});

window.bus = bus;
window.game = {
  loop: game,
  rag,
  get state() {
    return game.pet.snapshot();
  },
  exportChapter: () => rag.exportBatchForEmbedding(),
  tama: {
    feed: (amt = 25, meta = {}) => {
      game.pet.feed(amt);
      const snapshot = game.pet.snapshot();
      bus.emit(
        "agent_action",
        { action: "feed", amount: amt },
        {
          sim_t: snapshot.t,
          source: meta.source ?? "portal",
          tags: meta.tags ?? {},
        }
      );
      return snapshot;
    },
    rest: (amt = 25, meta = {}) => {
      game.pet.rest(amt);
      const snapshot = game.pet.snapshot();
      bus.emit(
        "agent_action",
        { action: "rest", amount: amt },
        {
          sim_t: snapshot.t,
          source: meta.source ?? "portal",
          tags: meta.tags ?? {},
        }
      );
      return snapshot;
    },
    clean: (amt = 25, meta = {}) => {
      game.pet.clean(amt);
      const snapshot = game.pet.snapshot();
      bus.emit(
        "agent_action",
        { action: "clean", amount: amt },
        {
          sim_t: snapshot.t,
          source: meta.source ?? "portal",
          tags: meta.tags ?? {},
        }
      );
      return snapshot;
    },
    play: (amt = 20, meta = {}) => {
      game.pet.play(amt);
      const snapshot = game.pet.snapshot();
      bus.emit(
        "agent_action",
        { action: "play", amount: amt },
        {
          sim_t: snapshot.t,
          source: meta.source ?? "portal",
          tags: meta.tags ?? {},
        }
      );
      return snapshot;
    },
  },
};

game.start();
