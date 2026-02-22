// adaptco-core-orchestrator/src/rehearsal.js
'use strict';

const logger = require('./log');
const { appendScrollstreamEvent } = require('./scrollstream-ledger');

const CAPSULE_ID = 'capsule.rehearsal.scrollstream.v1';
const CYCLE_NAME = 'celine-luma-dot';

const REHEARSAL_STEPS = Object.freeze([
  Object.freeze({
    phase: 'Celine',
    event: 'audit.summary',
    agent: Object.freeze({
      id: 'agent.celine.architect.v1',
      name: 'Celine',
      role: 'Architect',
      capsule: 'capsule.agent.celine.v1'
    }),
    output: Object.freeze({
      hud: Object.freeze({
        shimmer: 'ignition',
        palette: 'sovereign-gold',
        rail: 'signal'
      }),
      replay: Object.freeze({ glyph: 'signal', pulse: 'prelude', status: 'primed' }),
      payload: Object.freeze({
        emotion: 'Anticipation',
        resonance: 0.82,
        cue: 'Celine threads the audit summary across the scrollstream.'
      }),
      training: Object.freeze({
        deterministic: true,
        sabrinaSpark: 'PASS',
        scoring: Object.freeze({ clarity: 1.0, alignment: 0.98 })
      })
    })
  }),
  Object.freeze({
    phase: 'Luma',
    event: 'audit.proof',
    agent: Object.freeze({
      id: 'agent.luma.sentinel.v1',
      name: 'Luma',
      role: 'Sentinel',
      capsule: 'capsule.agent.luma.v1'
    }),
    output: Object.freeze({
      hud: Object.freeze({
        shimmer: 'sustain',
        palette: 'sovereign-gold',
        rail: 'luma-proof'
      }),
      replay: Object.freeze({ glyph: 'luma', pulse: 'verification', status: 'sustained' }),
      payload: Object.freeze({
        emotion: 'Resolve',
        resonance: 0.78,
        cue: 'Luma anchors the proof stack and loop integrity checks.'
      }),
      diagnostics: Object.freeze({
        binderDigest: 'sha256:celine-luma-proof',
        loopIntegrity: 'OK',
        sabrinaSpark: 'PASS'
      })
    })
  }),
  Object.freeze({
    phase: 'Dot',
    event: 'audit.execution',
    agent: Object.freeze({
      id: 'agent.dot.guardian.v1',
      name: 'Dot',
      role: 'Guardian',
      capsule: 'capsule.agent.dot.v1'
    }),
    output: Object.freeze({
      hud: Object.freeze({
        shimmer: 'seal-prep',
        palette: 'sovereign-gold',
        rail: 'dot-execution',
        replayGlyph: 'dot'
      }),
      replay: Object.freeze({ glyph: 'dot', pulse: 'commit', status: 'ready' }),
      payload: Object.freeze({
        emotion: 'Sovereignty',
        resonance: 0.94,
        cue: 'Dot locks the execution state and readies the seal window.'
      }),
      training: Object.freeze({
        deterministic: true,
        sabrinaSpark: 'PASS',
        scoring: Object.freeze({ readiness: 1.0, retention: 0.97 })
      }),
      ledger: Object.freeze({
        merkleRootPreview: 'merkle:scrollstream:rehearsal:v1',
        appended: true
      })
    })
  })
]);

function clone(value) {
  if (Array.isArray(value)) {
    return value.map((item) => clone(item));
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, val]) => [key, clone(val)]));
  }
  return value;
}

async function emitScrollstreamRehearsal(options = {}) {
  const appendEvent = typeof options.appendEvent === 'function' ? options.appendEvent : appendScrollstreamEvent;
  const now = typeof options.now === 'function' ? options.now : () => new Date().toISOString();

  const events = [];

  for (let index = 0; index < REHEARSAL_STEPS.length; index += 1) {
    const step = REHEARSAL_STEPS[index];
    const timestamp = now(index, step);

    if (!timestamp || typeof timestamp !== 'string') {
      throw new TypeError('now() must return an ISO timestamp string for each rehearsal step');
    }

    const entry = {
      ts: timestamp,
      capsule_id: CAPSULE_ID,
      cycle: CYCLE_NAME,
      sequence: index + 1,
      phase: step.phase,
      event: step.event,
      agent: Object.assign({}, step.agent),
      output: clone(step.output)
    };

    await appendEvent(entry);
    logger.debug({ event: entry.event, phase: entry.phase }, 'Scrollstream rehearsal event emitted');
    events.push(entry);
  }

  return {
    capsule_id: CAPSULE_ID,
    cycle: CYCLE_NAME,
    total_events: events.length,
    hud_status: 'shimmer-complete',
    replay_ready: true,
    events
  };
}

module.exports = {
  CAPSULE_ID,
  emitScrollstreamRehearsal,
  rehearsalSteps: REHEARSAL_STEPS
};
