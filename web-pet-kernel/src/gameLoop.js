import { PetState } from "./petState.js";

export class GameLoop {
  constructor(canvas, eventBus) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.bus = eventBus;

    this.pet = new PetState();
    this.lastNow = performance.now();
    this.running = false;

    this.registerInput();
  }

  registerInput() {
    this.canvas.addEventListener("click", (event) => {
      this.pet.feed(15);
      this.bus.emit(
        "player_action",
        { action: "feed", amount: 15, x: event.offsetX, y: event.offsetY },
        { sim_t: this.pet.snapshot().t, source: "player" }
      );
    });

    window.addEventListener("keydown", (event) => {
      if (event.key === "p") {
        this.pet.play(20);
        this.bus.emit(
          "player_action",
          { action: "play", amount: 20 },
          { sim_t: this.pet.snapshot().t, source: "player" }
        );
      }
      if (event.key === "c") {
        this.pet.clean(25);
        this.bus.emit(
          "player_action",
          { action: "clean", amount: 25 },
          { sim_t: this.pet.snapshot().t, source: "player" }
        );
      }
      if (event.key === "r") {
        this.pet.rest(25);
        this.bus.emit(
          "player_action",
          { action: "rest", amount: 25 },
          { sim_t: this.pet.snapshot().t, source: "player" }
        );
      }
    });
  }

  start() {
    this.running = true;
    requestAnimationFrame(this.step.bind(this));
  }

  step(now) {
    if (!this.running) return;

    const dt = (now - this.lastNow) / 1000;
    this.lastNow = now;

    this.pet.tick(dt);

    this.render();
    requestAnimationFrame(this.step.bind(this));
  }

  render() {
    const ctx = this.ctx;
    const { width: canvasWidth, height: canvasHeight } = this.canvas;
    ctx.clearRect(0, 0, canvasWidth, canvasHeight);

    ctx.fillStyle = "#222";
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    const snapshot = this.pet.snapshot();
    ctx.fillStyle = snapshot.alive ? "#c58b4e" : "#555";
    ctx.beginPath();
    ctx.arc(canvasWidth / 2, canvasHeight / 2, 40, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#fff";
    ctx.font = "14px sans-serif";
    ctx.fillText(`t: ${snapshot.t.toFixed(1)}s`, 16, 22);
    ctx.fillText(`mood: ${snapshot.mood}`, 16, 42);
    ctx.fillText(`hunger: ${snapshot.hunger.toFixed(1)}`, 16, 62);
    ctx.fillText(`energy: ${snapshot.energy.toFixed(1)}`, 16, 82);
    ctx.fillText(`clean: ${snapshot.cleanliness.toFixed(1)}`, 16, 102);
    ctx.fillText(`joy: ${snapshot.joy.toFixed(1)}`, 16, 122);

    ctx.fillStyle = "#bbb";
    ctx.fillText(
      "Controls: click=feed, p=play, c=clean, r=rest",
      16,
      canvasHeight - 16
    );

    if (!snapshot.alive) {
      ctx.fillStyle = "#ffb3b3";
      ctx.font = "16px sans-serif";
      ctx.fillText(
        `DEAD (${snapshot.causeOfDeath})`,
        canvasWidth / 2 - 70,
        canvasHeight / 2 + 70
      );
    }
  }
}
