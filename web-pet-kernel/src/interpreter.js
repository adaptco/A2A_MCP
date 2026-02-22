export function interpretState(state) {
  if (!state) {
    return { urgency: "UNKNOWN", priorities: [], text: "No state available." };
  }
  if (!state.alive) {
    return {
      urgency: "TERMINAL",
      priorities: [],
      text: `The pet is dead (cause: ${state.causeOfDeath}). No further actions are possible.`,
    };
  }

  const priorities = [];
  if (state.hunger >= 70) priorities.push("feed");
  if (state.energy <= 30) priorities.push("rest");
  if (state.cleanliness <= 40) priorities.push("clean");
  if (state.joy <= 35) priorities.push("play");

  const critical = [
    state.hunger >= 85,
    state.energy <= 20,
    state.cleanliness <= 25,
    state.joy <= 25,
  ].filter(Boolean).length;

  const urgency =
    critical >= 2
      ? "CRITICAL"
      : critical === 1
        ? "HIGH"
        : priorities.length >= 2
          ? "ELEVATED"
          : "STABLE";

  const text =
    `t=${state.t}s; mood=${state.mood}; ` +
    `hunger=${state.hunger}, energy=${state.energy}, cleanliness=${state.cleanliness}, joy=${state.joy}. ` +
    `Urgency=${urgency}. Priorities=${
      priorities.length ? priorities.join(", ") : "none"
    }.`;

  return { urgency, priorities, text };
}
