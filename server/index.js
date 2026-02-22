'use strict';

const fs = require('fs');
const path = require('path');
const express = require('express');
const qbusGateGuard = require('../lib/qbusGates');
const { loadManifest, buildHudState, getManifestHealth } = require('../lib/bindings');
const { createLedgerClient } = require('./ledger');

const MANIFEST_PATH = path.join(__dirname, '..', 'governance', 'authority_map.v1.json');
const DEFAULT_POLICY_TAG = 'pilot-alpha';
const MANIFEST_CACHE_TTL_MS = 30 * 1000;

function createManifestManager(manifestPath, options = {}) {
  let cache = null;
  let lastLoaded = 0;
  let lastArtifactSignature = '';
  const ttl = options.ttlMs || MANIFEST_CACHE_TTL_MS;

  const parsed = path.parse(manifestPath);
  const artifactPaths = [
    manifestPath,
    path.join(parsed.dir, `${parsed.name}.canonical.json`),
    path.join(parsed.dir, `${parsed.name}.hash`),
    path.join(parsed.dir, `${parsed.name}.sig`)
  ];

  const computeArtifactSignature = () => {
    const segments = [];
    for (const artifact of artifactPaths) {
      try {
        const stat = fs.statSync(artifact);
        segments.push(`${artifact}:${stat.size}:${stat.mtimeMs}`);
      } catch (err) {
        segments.push(`${artifact}:missing`);
      }
    }
    return segments.join('|');
  };

  async function load(force = false) {
    const now = Date.now();
    const artifactSignature = computeArtifactSignature();
    const cacheExpired = now - lastLoaded > ttl;
    const artifactsChanged = artifactSignature !== lastArtifactSignature;

    if (!cache || force || cacheExpired || artifactsChanged) {
      cache = await loadManifest(manifestPath, options);
      lastLoaded = now;
      lastArtifactSignature = artifactSignature;
    }
    return cache;
  }

  return {
    getAuthorityMap(force = false) {
      return load(force);
    },
    getCached() {
      return cache;
    },
    getLastLoaded() {
      return lastLoaded;
    }
  };
}

const manifestManager = createManifestManager(MANIFEST_PATH);
const ledgerClient = createLedgerClient(manifestManager, process.env.HUD_POLICY_TAG || DEFAULT_POLICY_TAG, { logger: console });

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, '..', 'public')));

const manifestProvider = () => manifestManager.getAuthorityMap();

const gateMiddleware = qbusGateGuard(manifestProvider, ledgerClient, {
  logger: console,
  skew_seconds: Number(process.env.QBUS_SKEW_SECONDS || 30)
});

app.get('/health', async (req, res) => {
  try {
    const manifestInfo = await manifestManager.getAuthorityMap();
    const health = getManifestHealth();
    res.json({
      status: manifestInfo.verified ? 'ok' : 'warning',
      manifest: {
        hash: manifestInfo.hash,
        expected_hash: manifestInfo.expectedHash,
        hash_matches: manifestInfo.hashMatches,
        signature_file_present: manifestInfo.hasSignatureFile,
        duo: manifestInfo.duo,
        loaded_at: manifestInfo.loadedAt
      },
      ledger: {
        recent_events: ledgerClient.getEvents()
      },
      manifest_health_snapshot: health
    });
  } catch (err) {
    res.status(500).json({
      status: 'error',
      message: err.message
    });
  }
});

app.get('/hud/state.json', async (req, res) => {
  try {
    if (req.query && req.query.force === 'true') {
      await manifestManager.getAuthorityMap(true);
    }
    const state = await buildHudState(ledgerClient, {
      force: req.query && req.query.force,
      cacheTTL: req.query && req.query.ttl,
      query: req.query
    });
    res.json(state);
  } catch (err) {
    res.status(500).json({
      error_code: 'HUD_STATE_ERROR',
      message: err.message
    });
  }
});

app.get('/qbit/proof.latest.v1', async (req, res) => {
  try {
    const forceReload = req.query && req.query.force === 'true';
    const manifestInfo = await manifestManager.getAuthorityMap(forceReload);
    const proof = await ledgerClient.getLatestProof(manifestInfo);
    proof.canonical_endpoint = '/governance/authority_map.v1.canonical.json';
    res.json(proof);
  } catch (err) {
    res.status(500).json({
      error_code: 'PROOF_FETCH_ERROR',
      message: err.message
    });
  }
});

app.get('/governance/authority_map.v1.canonical.json', async (req, res) => {
  try {
    const manifestInfo = await manifestManager.getAuthorityMap(req.query && req.query.force === 'true');
    res.type('application/json').send(manifestInfo.canonical);
  } catch (err) {
    res.status(500).json({
      error_code: 'CANONICAL_FETCH_ERROR',
      message: err.message
    });
  }
});

app.post('/ledger/freeze', async (req, res) => {
  const payload = req.body || {};
  if (!payload.name || !payload.hash || !payload.signature || !payload.canonical) {
    res.status(400).json({
      error_code: 'INVALID_FREEZE_ARTIFACT',
      message: 'name, hash, signature, and canonical fields are required'
    });
    return;
  }
  try {
    const stored = await ledgerClient.storeFreezeArtifact(payload);
    res.status(201).json({ stored });
  } catch (err) {
    res.status(500).json({
      error_code: 'LEDGER_STORE_ERROR',
      message: err.message
    });
  }
});

app.get('/ledger/snapshot', async (req, res) => {
  try {
    const manifestInfo = await manifestManager.getAuthorityMap(req.query && req.query.force === 'true');
    const snapshot = await ledgerClient.getSnapshot(manifestInfo);
    res.json(snapshot);
  } catch (err) {
    res.status(500).json({
      error_code: 'LEDGER_SNAPSHOT_ERROR',
      message: err.message
    });
  }
});

app.get('/scrollstream/ledger', (req, res) => {
  try {
    res.json({
      ledger: ledgerClient.getScrollstreamLedger()
    });
  } catch (err) {
    res.status(500).json({
      error_code: 'SCROLLSTREAM_LEDGER_ERROR',
      message: err.message
    });
  }
});

app.post('/scrollstream/rehearsal', async (req, res) => {
  try {
    const options = {};
    if (req.body && typeof req.body.cycle_id === 'string') {
      options.cycleId = req.body.cycle_id;
    }
    if (req.body && typeof req.body.now === 'string') {
      options.now = req.body.now;
    }
    if (req.body && typeof req.body.cadence_ms !== 'undefined') {
      options.cadenceMs = req.body.cadence_ms;
    }
    const events = await ledgerClient.runRehearsalLoop(options);
    res.status(201).json({
      status: 'ok',
      events
    });
  } catch (err) {
    res.status(500).json({
      error_code: 'REHEARSAL_LOOP_ERROR',
      message: err.message
    });
  }
});

app.post('/capsule/execute', gateMiddleware, async (req, res) => {
  const binding = req.qbus && req.qbus.binding ? req.qbus.binding.normalized : null;
  const manifestInfo = req.qbus ? req.qbus.manifest : null;
  res.json({
    status: 'ok',
    binding,
    manifest_hash: manifestInfo ? manifestInfo.hash : null
  });
});

app.use((req, res) => {
  res.status(404).json({
    error_code: 'NOT_FOUND',
    message: 'Resource not found'
  });
});

async function start(port = Number(process.env.PORT || 3000)) {
  try {
    await manifestManager.getAuthorityMap(true);
  } catch (err) {
    console.error('Initial manifest load failed:', err);
  }
  return new Promise((resolve) => {
    const server = app.listen(port, () => {
      console.log(`core orchestrator listening on port ${port}`);
      resolve(server);
    });
  });
}

if (require.main === module) {
  start();
}

module.exports = {
  app,
  start,
  manifestManager,
  ledgerClient
};
