#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DEFAULT_SECONDS = 10;
const DEFAULT_OUT_PATH = path.resolve(process.cwd(), '.out', 'hud_rehearsal.jsonl');
const HZ = 30;
const FRAME_INTERVAL_MS = 1000 / HZ;

function parseArgs(argv) {
  const options = {
    seconds: DEFAULT_SECONDS,
    out: DEFAULT_OUT_PATH,
    seed: 'hud-rehearsal'
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--seconds' || arg === '-s') {
      const next = argv[++i];
      if (!next) throw new Error('Missing value for --seconds');
      const value = Number(next);
      if (Number.isNaN(value) || value <= 0) {
        throw new Error(`Invalid seconds value: ${next}`);
      }
      options.seconds = value;
    } else if (arg === '--out' || arg === '-o') {
      const next = argv[++i];
      if (!next) throw new Error('Missing value for --out');
      options.out = path.resolve(process.cwd(), next);
    } else if (arg === '--seed') {
      const next = argv[++i];
      if (!next) throw new Error('Missing value for --seed');
      options.seed = next;
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return options;
}

function printHelp() {
  console.log(`Usage: node scripts/emit_hud_rehearsal_log.js [options]\n\n` +
    `Options:\n` +
    `  -s, --seconds <n>   Duration of rehearsal in seconds (default: ${DEFAULT_SECONDS})\n` +
    `  -o, --out <path>    Output file path (default: ${DEFAULT_OUT_PATH})\n` +
    `      --seed <value>  Seed for deterministic generation (default: hud-rehearsal)\n` +
    `  -h, --help          Show this help message\n`);
}

function createRng(seed) {
  const seedBuffer = crypto.createHash('sha256').update(String(seed)).digest();
  let counter = 0;
  return () => {
    const hash = crypto
      .createHash('sha256')
      .update(seedBuffer)
      .update(Buffer.from(String(counter++)))
      .digest();
    return hash.readUInt32BE(0) / 0xffffffff;
  };
}

function toFixed(num, digits = 3) {
  return Number(num.toFixed(digits));
}

function buildEvents(rng) {
  const state = {
    glyph: 1,
    aura: 0.85,
    phase: 0,
    promptIndex: 0
  };

  const prompts = ['Δ0', 'Δ1', 'Δ2', 'Δ3'];

  const builders = [
    (frame) => {
      const wobble = (rng() - 0.5) * 0.1;
      state.glyph = Math.max(0, Math.min(1, state.glyph + wobble));
      const drift = toFixed((rng() * 0.004) + 0.001, 3);
      return {
        event: 'glyph.pulse',
        frame,
        pose_lock: 'ok',
        val: toFixed(state.glyph, 3),
        drift
      };
    },
    (frame) => {
      const decay = (rng() - 0.4) * 0.05;
      state.aura = Math.max(0, Math.min(1.2, state.aura + decay));
      const drift = toFixed((rng() * 0.003) + 0.001, 3);
      return {
        event: 'aura.gold',
        frame,
        pose_lock: 'ok',
        val: toFixed(state.aura, 3),
        drift
      };
    },
    (frame) => {
      state.phase = (state.phase + 1) % 90;
      return {
        event: 'qlock.tick',
        frame,
        pose_lock: 'ok',
        phase: state.phase,
        drift: 0
      };
    },
    (frame) => {
      if (rng() > 0.7) {
        state.promptIndex = (state.promptIndex + 1) % prompts.length;
      }
      const label = prompts[state.promptIndex];
      const drift = toFixed((rng() * 0.005), 3);
      return {
        event: 'hud.qdot.delta',
        frame,
        pose_lock: 'ok',
        diff: {
          prompt: label,
          lora: label,
          seed: label,
          sampler: label
        },
        drift
      };
    }
  ];

  return builders;
}

function main() {
  try {
    const options = parseArgs(process.argv.slice(2));
    const rng = createRng(options.seed);
    const builders = buildEvents(rng);

    const totalFrames = Math.round(options.seconds * HZ);
    if (totalFrames <= 0) {
      throw new Error('Duration must produce at least one frame.');
    }

    const outDir = path.dirname(options.out);
    fs.mkdirSync(outDir, { recursive: true });

    const start = Date.now();
    const lines = [];

    for (let i = 0; i < totalFrames; i += 1) {
      const builder = builders[i % builders.length];
      const eventPayload = builder(i);
      const timestamp = new Date(start + Math.round(i * FRAME_INTERVAL_MS)).toISOString();
      const entry = {
        t: timestamp,
        hz: HZ,
        ...eventPayload
      };

      const hashInput = { ...entry };
      delete hashInput.hash;
      const digest = crypto.createHash('sha256').update(JSON.stringify(hashInput)).digest('hex');
      entry.hash = `sha256:${digest}`;

      lines.push(JSON.stringify(entry));
    }

    fs.writeFileSync(options.out, lines.join('\n') + '\n', 'utf8');
    console.log(`✅ HUD rehearsal log written to ${options.out} (${totalFrames} frames @ ${HZ}Hz)`);
  } catch (error) {
    console.error(`❌ ${error.message}`);
    process.exitCode = 1;
  }
}

if (require.main === module) {
  main();
}

module.exports = { parseArgs, createRng, buildEvents };
