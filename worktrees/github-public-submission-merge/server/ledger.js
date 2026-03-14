'use strict';

const fs = require('fs');
const path = require('path');
const { createHash } = require('crypto');
const { execFile } = require('child_process');
const { promisify } = require('util');

const execFileAsync = promisify(execFile);

const REHEARSAL_CAPSULE_ID = 'capsule.rehearsal.scrollstream.v1';

const DEFAULT_REHEARSAL_STAGES = [
  {
    stage: 'audit.summary',
    agent: { name: 'Celine', role: 'Architect' },
    output: 'Celine threads the capsule brief into the braid summary.',
    emotive: ['irony shimmer', 'spark trace'],
    glyph: 'hud.shimmer'
  },
  {
    stage: 'audit.proof',
    agent: { name: 'Luma', role: 'Sentinel' },
    output: 'Luma validates proof lattice continuity for rehearsal replay.',
    emotive: ['spark trace', 'glyph fidelity'],
    glyph: 'sentinel.pulse'
  },
  {
    stage: 'audit.execution',
    agent: { name: 'Dot', role: 'Guardian' },
    output: 'Dot confirms execution trace and primes replay glyph.',
    emotive: ['glyph fidelity', 'empathy shimmer'],
    glyph: 'guardian.echo'
  }
];

function stageCount(stages) {
  if (!Array.isArray(stages) || !stages.length) {
    return 0;
  }
  return stages.length;
}

function computeMerkleRootFromArtifacts(artifacts) {
  if (!artifacts || artifacts.length === 0) {
    return null;
  }

  const leaves = artifacts
    .map((artifact) => {
      const name = artifact.name || '';
      const hash = artifact.hash || '';
      const signature = artifact.signature || '';
      return createHash('sha256').update(`${name}:${hash}:${signature}`).digest('hex');
    })
    .sort();

  let level = leaves;
  while (level.length > 1) {
    const nextLevel = [];
    for (let i = 0; i < level.length; i += 2) {
      const left = level[i];
      const right = level[i + 1] || level[i];
      nextLevel.push(createHash('sha256').update(left + right).digest('hex'));
    }
    level = nextLevel;
  }

  return level[0];
}

async function runSealScript(scriptPath, payload, logger, cache) {
  const info = cache || { missingWarned: false };
  if (!scriptPath) {
    if (!info.missingWarned && logger && typeof logger.warn === 'function') {
      logger.warn('Seal script not configured; skipping automatic sealing.');
      info.missingWarned = true;
    }
    return { status: 'skipped', reason: 'missing_script' };
  }

  try {
    await fs.promises.access(scriptPath, fs.constants.X_OK);
  } catch (err) {
    if (!info.missingWarned && logger && typeof logger.warn === 'function') {
      logger.warn(`Seal script ${scriptPath} is not accessible or executable: ${err.message}`);
      info.missingWarned = true;
    }
    return { status: 'skipped', reason: 'inaccessible_script', error: err };
  }

  info.missingWarned = false;

  const env = {
    ...process.env,
    MERKLE_ROOT: payload.merkle_root,
    MERKLE_PAYLOAD: JSON.stringify(payload)
  };

  try {
    const { stdout, stderr } = await execFileAsync(scriptPath, [payload.merkle_root], { env });
    if (stdout && stdout.length && logger && typeof logger.debug === 'function') {
      logger.debug(`[seal] ${stdout.trim()}`);
    }
    if (stderr && stderr.length && logger && typeof logger.warn === 'function') {
      logger.warn(`[seal][stderr] ${stderr.trim()}`);
    }
    return { status: 'ok', stdout, stderr };
  } catch (err) {
    if (logger && typeof logger.error === 'function') {
      logger.error(`Seal script failed for ${payload.merkle_root}: ${err.message}`);
    }
    return { status: 'error', error: err };
  }
}

function createLedgerClient(manifestManager, policyTag, options = {}) {
  const logger = options.logger || console;
  const sealScriptPath = options.sealScriptPath || process.env.SEAL_ROOT_SCRIPT || path.join(__dirname, '..', 'ops', 'v7_seal_root.sh');
  const sealHistory = [];
  const sealHistoryLimit = 25;
  const sealCache = { missingWarned: false };
  const gateEvents = [];
  const scrollstreamLedger = [];
  const scrollstreamLimit = options.scrollstreamLimit || 90;
  const freezeArtifacts = new Map();
  const maxEvents = 50;
  let lastMerkleRoot = null;

  function appendScrollstreamEvent(event) {
    const safeAgent = event.agent && typeof event.agent === 'object' ? event.agent : {};
    const entry = {
      capsule_id: event.capsule_id || REHEARSAL_CAPSULE_ID,
      cycle_id: event.cycle_id,
      stage: event.stage,
      agent: {
        name: safeAgent.name || 'Unknown',
        role: safeAgent.role || 'Unknown'
      },
      output: event.output,
      emotive: Array.isArray(event.emotive) ? event.emotive.slice() : [],
      glyph: event.glyph || null,
      timestamp: event.timestamp || new Date().toISOString()
    };

    scrollstreamLedger.push(entry);
    if (scrollstreamLedger.length > scrollstreamLimit) {
      scrollstreamLedger.splice(0, scrollstreamLedger.length - scrollstreamLimit);
    }

    return entry;
  }

  async function runRehearsalLoop(options = {}) {
    const stageDefinitions = Array.isArray(options.stages) && options.stages.length ? options.stages : DEFAULT_REHEARSAL_STAGES;

    const now = options.now ? new Date(options.now) : new Date();
    if (Number.isNaN(now.getTime())) {
      throw new Error('Invalid rehearsal loop timestamp');
    }

    const cadenceMs = Number(options.cadenceMs || 275);
    const cycleId = options.cycleId || `cycle-${now.toISOString()}`;
    const events = [];

    for (let index = 0; index < stageDefinitions.length; index += 1) {
      const definition = stageDefinitions[index];
      const timestamp = new Date(now.getTime() + cadenceMs * index).toISOString();
      const event = appendScrollstreamEvent({
        capsule_id: REHEARSAL_CAPSULE_ID,
        cycle_id: cycleId,
        stage: definition.stage,
        agent: definition.agent,
        output: definition.output,
        emotive: definition.emotive,
        glyph: definition.glyph,
        timestamp
      });
      events.push(event);
    }

    return events;
  }

  async function maybeSeal() {
    const artifacts = Array.from(freezeArtifacts.values()).sort((a, b) => a.name.localeCompare(b.name));
    const merkleRoot = computeMerkleRootFromArtifacts(artifacts);
    if (!merkleRoot || merkleRoot === lastMerkleRoot) {
      return merkleRoot;
    }

    const payload = {
      merkle_root: merkleRoot,
      artifacts,
      generated_at: new Date().toISOString()
    };

    const result = await runSealScript(sealScriptPath, payload, logger, sealCache);
    sealHistory.push({
      merkle_root: merkleRoot,
      invoked_at: new Date().toISOString(),
      status: result.status,
      error: result.error ? String(result.error.message || result.error) : undefined
    });
    if (sealHistory.length > sealHistoryLimit) {
      sealHistory.shift();
    }

    lastMerkleRoot = merkleRoot;
    return merkleRoot;
  }

  const client = {
    async recordGateCheck(event) {
      const enriched = {
        ...event,
        recorded_at: new Date().toISOString()
      };
      gateEvents.push(enriched);
      if (gateEvents.length > maxEvents) {
        gateEvents.shift();
      }
      return { recorded: true };
    },
    async getLatestProof(manifestInfo) {
      const info = manifestInfo || (await manifestManager.getAuthorityMap());
      const recentScrollstream = scrollstreamLedger.slice(-stageCount(DEFAULT_REHEARSAL_STAGES));
      return {
        manifest_hash: info.hash,
        expected_hash: info.expectedHash || null,
        hash_matches: info.hashMatches,
        duo: {
          maker: info.duo && info.duo.maker ? info.duo.maker.verified : false,
          checker: info.duo && info.duo.checker ? info.duo.checker.verified : false,
          ok: info.duo ? info.duo.ok : false
        },
        signature_artifact_present: Boolean(info.hasSignatureFile),
        policy_tag: policyTag,
        generated_at: new Date().toISOString(),
        events: gateEvents.slice(-10),
        scrollstream: {
          events: recentScrollstream,
          shimmer: recentScrollstream.length ? 'engaged' : 'idle',
          replay_glyph: recentScrollstream.length ? 'pulse' : 'idle'
        }
      };
    },
    getEvents() {
      return gateEvents.slice(-10);
    },
    async storeFreezeArtifact(artifact) {
      const payload = {
        name: artifact.name || 'unknown',
        hash: artifact.hash || null,
        signature: artifact.signature || null,
        canonical: artifact.canonical || null,
        stored_at: new Date().toISOString()
      };
      freezeArtifacts.set(payload.name, payload);
      await maybeSeal();
      return payload;
    },
    getFreezeArtifacts() {
      return Array.from(freezeArtifacts.values());
    },
    async getSnapshot(manifestInfo) {
      const proof = await client.getLatestProof(manifestInfo);
      return {
        proof,
        freeze_artifacts: client.getFreezeArtifacts(),
        merkle_root: lastMerkleRoot,
        seal_history: sealHistory.slice(-5),
        scrollstream_ledger: scrollstreamLedger.slice()
      };
    },
    getMerkleRoot() {
      return lastMerkleRoot;
    },
    getSealHistory() {
      return sealHistory.slice();
    },
    getScrollstreamLedger() {
      return scrollstreamLedger.slice();
    },
    runRehearsalLoop
  };

  return client;
}

module.exports = {
  computeMerkleRootFromArtifacts,
  createLedgerClient,
  REHEARSAL_CAPSULE_ID,
  DEFAULT_REHEARSAL_STAGES
};
