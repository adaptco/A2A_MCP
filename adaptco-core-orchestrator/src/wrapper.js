// adaptco-core-orchestrator/src/wrapper.js
'use strict';

const { promises: fsp } = require('fs');
const path = require('path');

async function loadWrapperCapsule(options = {}) {
  const { wrapperPath, cwd = process.cwd() } = options;
  const targetPath = wrapperPath || path.resolve(cwd, 'capsules', 'doctrine', 'capsule.wrapper.adaptco_os.v1.json');
  const capsule = await readJson(targetPath, 'wrapper capsule');
  return validateWrapperCapsule(capsule);
}

async function loadRuntimeRegistry(options = {}) {
  const { registryPath, cwd = process.cwd() } = options;
  const targetPath = registryPath || path.resolve(cwd, 'runtime', 'capsule.registry.runtime.v1.json');
  const registry = await readJson(targetPath, 'runtime registry');
  return registry;
}

function createAnchorBindings(wrapperCapsule, registryCapsule = {}) {
  const anchors = Array.isArray(wrapperCapsule?.lineage?.anchors) ? wrapperCapsule.lineage.anchors : [];
  const entries = Array.isArray(registryCapsule.entries) ? registryCapsule.entries : [];
  const entryMap = new Map(entries.map((entry) => [entry.capsule_id, entry]));

  return anchors.map((capsuleId) => {
    const entry = entryMap.get(capsuleId) || null;
    const binding = entry ? 'bound' : 'missing';
    const status = entry?.status || null;
    const sticky = Boolean(entry && status && status !== 'REHEARSAL');
    return {
      capsule_id: capsuleId,
      binding,
      status,
      sticky,
      governance: entry?.governance || null,
      hash: entry?.hash || null
    };
  });
}

async function inspectWrapperEnvironment(options = {}) {
  const {
    cwd = process.cwd(),
    wrapperPath,
    registryPath,
    runtimeDir = path.resolve(cwd, 'runtime')
  } = options;

  const [wrapperCapsule, registryCapsule] = await Promise.all([
    loadWrapperCapsule({ wrapperPath, cwd }),
    loadRuntimeRegistry({ registryPath, cwd })
  ]);

  const anchorBindings = createAnchorBindings(wrapperCapsule, registryCapsule);
  const ledgerRef = wrapperCapsule?.runtime?.ledger || null;
  const ledgerPath = ledgerRef ? path.resolve(runtimeDir, ledgerRef) : null;
  const ledgerExists = ledgerPath ? await pathExists(ledgerPath) : false;
  const registryExists = await pathExists(
    registryPath || path.resolve(cwd, 'runtime', 'capsule.registry.runtime.v1.json')
  );

  const boundCount = anchorBindings.filter((binding) => binding.binding === 'bound').length;
  const stickyCount = anchorBindings.filter((binding) => binding.sticky).length;

  return {
    wrapper: {
      capsule_id: wrapperCapsule.capsule_id,
      version: wrapperCapsule.version,
      description: wrapperCapsule.description || null
    },
    governance: {
      router: wrapperCapsule?.governance?.router || null,
      stabilizer: wrapperCapsule?.governance?.stabilizer || null,
      oracle: wrapperCapsule?.governance?.oracle || null,
      weaver: wrapperCapsule?.governance?.weaver || null,
      council: wrapperCapsule?.governance?.council || null
    },
    anchors: anchorBindings,
    sticky: {
      total: anchorBindings.length,
      bound: boundCount,
      sticky: stickyCount
    },
    runtime: {
      registry: {
        path: registryPath || path.resolve(cwd, 'runtime', 'capsule.registry.runtime.v1.json'),
        capsule_id: registryCapsule?.capsule_id || null,
        version: registryCapsule?.version || null,
        exists: registryExists
      },
      ledger: {
        path: ledgerPath,
        exists: ledgerExists
      },
      vault: wrapperCapsule?.runtime?.vault || null,
      hud: Array.isArray(wrapperCapsule?.runtime?.hud) ? wrapperCapsule.runtime.hud : []
    }
  };
}

async function readJson(targetPath, label) {
  try {
    const raw = await fsp.readFile(targetPath, 'utf8');
    return JSON.parse(raw);
  } catch (error) {
    const context = label ? `${label} ` : '';
    error.message = `Failed to read ${context}from ${targetPath}: ${error.message}`;
    throw error;
  }
}

function validateWrapperCapsule(capsule) {
  if (!capsule || typeof capsule !== 'object') {
    throw new Error('Wrapper capsule payload must be an object');
  }

  const requiredFields = ['capsule_id', 'version', 'lineage', 'governance', 'runtime'];
  const missing = requiredFields.filter((field) => !(field in capsule));
  if (missing.length > 0) {
    throw new Error(`Wrapper capsule missing fields: ${missing.join(', ')}`);
  }

  const lineage = capsule.lineage || {};
  if (!Array.isArray(lineage.anchors)) {
    throw new Error('Wrapper capsule lineage.anchors must be an array');
  }

  const governance = capsule.governance || {};
  if (!governance.router) {
    throw new Error('Wrapper capsule governance.router is required');
  }
  if (!governance.stabilizer) {
    throw new Error('Wrapper capsule governance.stabilizer is required');
  }

  const runtime = capsule.runtime || {};
  if (!runtime.registry) {
    throw new Error('Wrapper capsule runtime.registry is required');
  }
  if (!runtime.ledger) {
    throw new Error('Wrapper capsule runtime.ledger is required');
  }

  return capsule;
}

async function pathExists(targetPath) {
  try {
    await fsp.access(targetPath);
    return true;
  } catch (error) {
    return false;
  }
}

module.exports = {
  loadWrapperCapsule,
  loadRuntimeRegistry,
  createAnchorBindings,
  inspectWrapperEnvironment
};
