export class PetState {
  constructor() {
    this.t = 0;

    this.hunger = 10;
    this.energy = 90;
    this.cleanliness = 80;
    this.joy = 70;

    this.alive = true;
    this.causeOfDeath = null;

    this.mood = "ok";
    this.lastMood = this.mood;
  }

  tick(dt) {
    if (!this.alive) return;

    this.t += dt;

    this.hunger = clamp(this.hunger + dt * 0.9, 0, 100);
    this.energy = clamp(this.energy - dt * 0.6, 0, 100);
    this.cleanliness = clamp(this.cleanliness - dt * 0.25, 0, 100);
    this.joy = clamp(this.joy - dt * 0.15, 0, 100);

    if (this.hunger > 75) this.joy = clamp(this.joy - dt * 0.35, 0, 100);
    if (this.energy < 25) this.joy = clamp(this.joy - dt * 0.25, 0, 100);
    if (this.cleanliness < 35) this.joy = clamp(this.joy - dt * 0.2, 0, 100);

    this.lastMood = this.mood;
    this.mood = this.deriveMood();

    if (this.hunger >= 100) this.die("starvation");
    if (this.energy <= 0) this.die("exhaustion");
    if (this.cleanliness <= 0 && this.joy < 10) this.die("neglect");
  }

  feed(amount = 25) {
    if (!this.alive) return;
    this.hunger = clamp(this.hunger - amount, 0, 100);
    this.joy = clamp(this.joy + amount * 0.12, 0, 100);
  }

  rest(amount = 25) {
    if (!this.alive) return;
    this.energy = clamp(this.energy + amount, 0, 100);
    this.joy = clamp(this.joy + amount * 0.06, 0, 100);
  }

  clean(amount = 25) {
    if (!this.alive) return;
    this.cleanliness = clamp(this.cleanliness + amount, 0, 100);
    this.joy = clamp(this.joy + amount * 0.08, 0, 100);
  }

  play(amount = 20) {
    if (!this.alive) return;
    this.joy = clamp(this.joy + amount * 0.9, 0, 100);
    this.energy = clamp(this.energy - amount * 0.5, 0, 100);
    this.cleanliness = clamp(this.cleanliness - amount * 0.2, 0, 100);
    this.hunger = clamp(this.hunger + amount * 0.15, 0, 100);
  }

  die(cause) {
    this.alive = false;
    this.causeOfDeath = cause;
    this.lastMood = this.mood;
    this.mood = "dead";
  }

  deriveMood() {
    if (!this.alive) return "dead";

    const flags = {
      starving: this.hunger >= 85,
      sleepy: this.energy <= 20,
      filthy: this.cleanliness <= 25,
      sad: this.joy <= 25,
    };

    const criticalCount = Object.values(flags).filter(Boolean).length;
    if (criticalCount >= 2) return "distressed";
    if (flags.starving) return "starving";
    if (flags.sleepy) return "sleepy";
    if (flags.filthy) return "filthy";
    if (flags.sad) return "sad";
    if (
      this.joy >= 70 &&
      this.hunger < 40 &&
      this.energy > 50 &&
      this.cleanliness > 50
    ) {
      return "happy";
    }
    return "ok";
  }

  snapshot() {
    return {
      t: round3(this.t),
      alive: this.alive,
      causeOfDeath: this.causeOfDeath,
      hunger: round3(this.hunger),
      energy: round3(this.energy),
      cleanliness: round3(this.cleanliness),
      joy: round3(this.joy),
      mood: this.mood,
    };
  }
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function round3(value) {
  return Math.round(value * 1000) / 1000;
}
