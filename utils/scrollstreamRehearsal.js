'use strict';

const fs = require('fs');
const path = require('path');

const CAPSULE_ID = 'capsule.rehearsal.scrollstream.v1';
const DEFAULT_BASE_TIMESTAMP = '2025-03-07T19:00:00.000Z';
const DEFAULT_INTERVAL_SECONDS = 23;

const REHEARSAL_SEQUENCE = [
  {
    stage: 'audit.summary',
    agent: {
      name: 'Celine',
      callSign: 'Architect',
      role: 'Architect'
    },
    output: {
      headline: 'Celine threads rehearsal summary for the scrollstream braid.',
      body: [
        'Cycle seeded for capsule.rehearsal.scrollstream.v1.',
        'HUD shimmer primed so contributors see the capsule ignite.'
      ],
      emotionalPayload: {
        tone: 'anticipatory',
        color: 'cobalt',
        intensity: 0.42,
        affirmation: 'The braid is listening.'
      },
      sabrinaSparkTest: 'pass'
    },
    training: {
      cue: 'celine-architect::audit.summary',
      rehearsalBeat: 'architect-brief'
    }
  },
  {
    stage: 'audit.proof',
    agent: {
      name: 'Luma',
      callSign: 'Sentinel',
      role: 'Sentinel'
    },
    output: {
      headline: 'Luma confirms proof lattice and steadies the rail.',
      body: [
        'Ledger anchors verified across rehearsal lattice.',
        'Replay glyph telemetry warmed for imminent pulse.'
      ],
      emotionalPayload: {
        tone: 'assured',
        color: 'emerald',
        intensity: 0.37,
        affirmation: 'Hold fast. Proof threads are aligned.'
      },
      sabrinaSparkTest: 'pass'
    },
    training: {
      cue: 'luma-sentinel::audit.proof',
      rehearsalBeat: 'sentinel-proof'
    }
  },
  {
    stage: 'audit.execution',
    agent: {
      name: 'Dot',
      callSign: 'Guardian',
      role: 'Guardian'
    },
    output: {
      headline: 'Dot executes the braid and releases the replay glyph.',
      body: [
        'Cycle sealed. Scrollstream ledger updated for contributor replay.',
        'Replay glyph pulses so the lifecycle can be relived on demand.'
      ],
      emotionalPayload: {
        tone: 'triumphant',
        color: 'ember',
        intensity: 0.58,
        affirmation: 'Exhale. The capsule is sealed.'
      },
      sabrinaSparkTest: 'pass'
    },
    training: {
      cue: 'dot-guardian::audit.execution',
      rehearsalBeat: 'guardian-execute'
    }
  }
];

function deepClone(value) {
  if (Array.isArray(value)) {
    return value.map(deepClone);
  }
  if (value && typeof value === 'object') {
    const clone = {};
    for (const key of Object.keys(value)) {
      clone[key] = deepClone(value[key]);
    }
    return clone;
  }
  return value;
}

function createLedgerEntries(options = {}) {
  const baseTimestamp = options.baseTimestamp || DEFAULT_BASE_TIMESTAMP;
  const baseTime = Date.parse(baseTimestamp);
  if (Number.isNaN(baseTime)) {
    throw new Error(`Invalid base timestamp: ${baseTimestamp}`);
  }

  const intervalSeconds = Object.prototype.hasOwnProperty.call(options, 'intervalSeconds')
    ? options.intervalSeconds
    : DEFAULT_INTERVAL_SECONDS;
  if (typeof intervalSeconds !== 'number' || !Number.isFinite(intervalSeconds) || intervalSeconds < 0) {
    throw new Error(`Invalid intervalSeconds: ${intervalSeconds}`);
  }

  const entries = REHEARSAL_SEQUENCE.map((event, index, arr) => {
    const timestamp = new Date(baseTime + index * intervalSeconds * 1000).toISOString();
    return {
      capsuleId: CAPSULE_ID,
      capsuleCycle: {
        position: index + 1,
        total: arr.length,
        stage: event.stage
      },
      stage: event.stage,
      agent: deepClone(event.agent),
      timestamp,
      output: deepClone(event.output),
      visual: {
        hudShimmer: true,
        replayGlyphPulse: index === arr.length - 1,
        replayGlyphId: 'scrollstream-replay'
      },
      training: Object.assign(
        {
          deterministic: true,
          mode: 'rehearsal',
          sabrinaSparkTest: 'pass'
        },
        deepClone(event.training)
      )
    };
  });

  return entries;
}

function ensureDirectoryForFile(filePath) {
  const directory = path.dirname(filePath);
  fs.mkdirSync(directory, { recursive: true });
}

function writeScrollstreamLedger(filePath, entries, options = {}) {
  const pretty = options.pretty !== false;
  ensureDirectoryForFile(filePath);
  const payload = pretty ? JSON.stringify(entries, null, 2) + '\n' : JSON.stringify(entries);
  fs.writeFileSync(filePath, payload, 'utf8');
  return filePath;
}

function emitRehearsalLedger(options = {}) {
  const { outputPath, ...rest } = options;
  const entries = createLedgerEntries(rest);
  if (outputPath) {
    writeScrollstreamLedger(outputPath, entries, options);
  }
  return entries;
}

module.exports = {
  CAPSULE_ID,
  DEFAULT_BASE_TIMESTAMP,
  DEFAULT_INTERVAL_SECONDS,
  REHEARSAL_SEQUENCE: REHEARSAL_SEQUENCE.map(deepClone),
  createLedgerEntries,
  writeScrollstreamLedger,
  emitRehearsalLedger
};
