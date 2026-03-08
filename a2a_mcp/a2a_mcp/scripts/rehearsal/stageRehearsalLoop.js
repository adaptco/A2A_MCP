#!/usr/bin/env node
/**
 * Stage the scrollstream rehearsal loop capsule emission.
 *
 * Emits deterministic ledger entries for the audit lifecycle (summary → proof → execution)
 * so contributors can replay the full braid and verify the HUD shimmer / replay glyph cues.
 */

const fs = require('fs');
const path = require('path');

const CAPSULE_ID = 'capsule.rehearsal.scrollstream.v1';
const REPLAY_TOKEN = 'HUD.loop.selfie.dualroot.q.cici.v1.token.002';
const LEDGER_RELATIVE_PATH = path.join('.out', 'scrollstream_ledger.jsonl');

function parseArgs(argv) {
  const args = {
    training: false,
    ledger: LEDGER_RELATIVE_PATH,
  };

  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--training') {
      args.training = true;
    } else if (arg.startsWith('--ledger=')) {
      args.ledger = arg.slice('--ledger='.length);
    } else if (arg === '--ledger' && i + 1 < argv.length) {
      args.ledger = argv[i + 1];
      i += 1;
    } else if (arg === '--help' || arg === '-h') {
      args.help = true;
      break;
    }
  }

  return args;
}

function printHelp() {
  console.log(`Stage the scrollstream rehearsal loop and append deterministic ledger events.\n\n` +
    `Usage:\n  node scripts/rehearsal/stageRehearsalLoop.js [--training] [--ledger <path>]\n\n` +
    `Options:\n  --training       Force deterministic timestamps for CI smoke tests.\n` +
    `  --ledger PATH   Override the target ledger file (defaults to ${LEDGER_RELATIVE_PATH}).\n` +
    `  -h, --help      Show this help message.`);
}

function ensureDirExists(filePath) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function isoTimestamp(baseTime, offsetSeconds) {
  const ts = new Date(baseTime.getTime() + offsetSeconds * 1000);
  return ts.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function buildCyclePayload(training) {
  const emotionalPayloads = {
    celine: {
      tone: 'architectural steadiness',
      spark_resonance: 'baseline harmonic',
      cue: 'CiCi posture check passed',
    },
    luma: {
      tone: 'sentinel vigilance',
      spark_resonance: 'evidence braid aligned',
      cue: 'Aston Martin gleam logged for replay',
    },
    dot: {
      tone: 'guardian resolve',
      spark_resonance: 'execution pulse locked',
      cue: 'Q gaze depth registered',
    },
  };

  const visualFeedback = {
    summary: { hud_shimmer: 'confirm', replay_glyph: 'pulse-primed' },
    proof: { hud_shimmer: 'hold', replay_glyph: 'pulse-sustain' },
    execution: { hud_shimmer: 'seal', replay_glyph: 'pulse-release' },
  };

  return [
    {
      event: 'audit.summary',
      agent: { name: 'Celine', call_sign: 'Architect' },
      emotional_payload: emotionalPayloads.celine,
      output: {
        synopsis: 'Architect ledger synopsis braided across dual roots.',
        overlay_status: 'CiCi overlay stable; shimmer sync confirmed.',
        training_note: 'Deterministic braid stub emitted for summary layer.',
      },
      visual: visualFeedback.summary,
      spark_test: { suite: 'Sabrina Spark Test', status: 'pass', sample: 'summary-glyph' },
    },
    {
      event: 'audit.proof',
      agent: { name: 'Luma', call_sign: 'Sentinel' },
      emotional_payload: emotionalPayloads.luma,
      output: {
        synopsis: 'Sentinel proof lattice threads validated.',
        observability: 'Trace anchor captured; refusal flare dormant.',
        training_note: 'Proof braid deterministically replays ledger assertions.',
      },
      visual: visualFeedback.proof,
      spark_test: { suite: 'Sabrina Spark Test', status: 'pass', sample: 'proof-glyph' },
    },
    {
      event: 'audit.execution',
      agent: { name: 'Dot', call_sign: 'Guardian' },
      emotional_payload: emotionalPayloads.dot,
      output: {
        synopsis: 'Guardian execution path sealed and timestamped.',
        breach_monitor: 'Shimmer breach monitor reports no drift.',
        training_note: 'Execution ledger sample deterministic for CI.',
      },
      visual: visualFeedback.execution,
      spark_test: { suite: 'Sabrina Spark Test', status: 'pass', sample: 'execution-glyph' },
    },
  ].map((stage) => ({
    ...stage,
    capsule: CAPSULE_ID,
    replay_token: REPLAY_TOKEN,
    training_mode: {
      deterministic: training,
      emotional_payload_embedded: true,
      replay_ready: true,
    },
  }));
}

function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    printHelp();
    process.exit(0);
  }

  const trainingMode = args.training || process.env.REHEARSAL_TRAINING === '1';
  const ledgerPath = path.resolve(args.ledger);
  ensureDirExists(ledgerPath);

  const baseTime = trainingMode
    ? new Date('2025-09-25T00:00:00Z')
    : new Date();

  const cyclePayload = buildCyclePayload(trainingMode);

  const ledgerLines = cyclePayload.map((stage, idx) => {
    const timestamp = isoTimestamp(baseTime, idx * 7);
    return JSON.stringify({
      t: timestamp,
      capsule: stage.capsule,
      event: stage.event,
      agent: stage.agent,
      output: stage.output,
      emotional_payload: stage.emotional_payload,
      visual: stage.visual,
      training_mode: stage.training_mode,
      spark_test: stage.spark_test,
      replay_token: stage.replay_token,
      hooks: {
        comment_trace: 'capsule.comment.trace.v1',
        shimmer_breach: 'shimmer.breach.monitor.v1',
        refusal_flare: 'refusal.flare.script.v1',
        overlay_audit: 'delta.overlay.audit.v1',
      },
    });
  });

  fs.appendFileSync(ledgerPath, `${ledgerLines.join('\n')}\n`, 'utf8');

  cyclePayload.forEach((stage, idx) => {
    const timestamp = isoTimestamp(baseTime, idx * 7);
    console.log(`🔁 ${stage.event} | ${stage.agent.name} (${stage.agent.call_sign}) → HUD:${stage.visual.hud_shimmer} | replay:${stage.visual.replay_glyph} | ${timestamp}`);
  });

  console.log(`\nLedger appended → ${ledgerPath}`);
  console.log(`Capsule replay token → ${REPLAY_TOKEN}`);
  if (trainingMode) {
    console.log('Training mode enabled → deterministic timestamps and payloads.');
  }
}

main();
