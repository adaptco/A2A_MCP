export function computeReward(prev, next) {
  if (prev?.alive && next?.alive === false) return -100;

  const dh = prev.hunger - next.hunger;
  const de = next.energy - prev.energy;
  const dc = next.cleanliness - prev.cleanliness;
  const dj = next.joy - prev.joy;

  let reward = 0.25 * dh + 0.2 * de + 0.15 * dc + 0.4 * dj;

  if (next.hunger >= 85) reward -= 3;
  if (next.energy <= 20) reward -= 3;
  if (next.cleanliness <= 25) reward -= 2;
  if (next.joy <= 25) reward -= 2;

  if (prev.mood !== next.mood) {
    if (next.mood === "happy") reward += 2;
    if (next.mood === "distressed") reward -= 2;
  }

  return round3(reward);
}

function round3(value) {
  return Math.round(value * 1000) / 1000;
}
