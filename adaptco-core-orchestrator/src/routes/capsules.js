// adaptco-core-orchestrator/src/routes/capsules.js
'use strict';

const express = require('express');
const { validateOrThrow } = require('../validator');
const defaultLedger = require('../ledger');
const logger = require('../log');
const SentinelAgent = require('../sentinel');
const defaultHashRunner = require('../hash_scroll');
const hydrateNonCodexOperations = require('../non_codex_hydrator');
const capsuleSchema = require('../../schemas/capsule.schema.json');

function createCapsuleRouter(options = {}) {
  const router = express.Router();
  const ledger = options.ledger || defaultLedger;
  const sentinel = options.sentinel || new SentinelAgent(options.sentinelOptions || {});
  const hashRunner = options.hashRunner || defaultHashRunner;

  router.post('/register', async (req, res, next) => {
    try {
      const capsule = validateOrThrow(capsuleSchema, req.body);
      const id = `capsule-${capsule.capsule_id}-${capsule.version}`;
      const { operations = {}, ...capsuleRecord } = capsule;
      const hydratedOperations = hydrateNonCodexOperations(operations);

      const previewConfig = hydratedOperations.preview || operations.preview;
      const assetConfig = hydratedOperations.asset || operations.asset;
      const hashConfig = hydratedOperations.hash || operations.hash;

      let previewResult = null;
      if (previewConfig) {
        assertSentinelCapability(sentinel, 'renderPreview');
        const previewOptions = buildPreviewOptions(previewConfig);
        previewResult = await sentinel.renderPreview(previewConfig.descriptor, previewOptions);
      }

      let assetResult = null;
      if (assetConfig) {
        assertSentinelCapability(sentinel, 'registerAsset');
        const assetOptions = buildAssetOptions(assetConfig);
        assetResult = await sentinel.registerAsset(assetConfig.payload, assetOptions);
      }

      let hashResult = null;
      if (hashConfig) {
        if (typeof hashRunner !== 'function') {
          throw new Error('hash runner is not available');
        }
        const inputs = buildHashInputs(hashConfig, previewResult);
        if (inputs.length > 0) {
          const hashOptions = buildHashOptions(hashConfig);
          hashResult = await hashRunner(inputs, hashOptions);
        }
      }

      const previewSummary = summarizePreview(previewResult);
      const hashSummary = summarizeHash(hashResult);

      await ledger.appendEvent('capsule.registered', {
        id,
        capsule: capsuleRecord,
        preview: previewSummary,
        asset: assetResult || null,
        hash: hashSummary
      });

      logger.info(
        {
          id,
          preview: previewSummary,
          asset_status: assetResult?.status,
          merkle_root: hashSummary?.merkle_root
        },
        'Capsule registered'
      );

      res.json({
        status: 'ok',
        id,
        received: {
          capsule_id: capsule.capsule_id,
          version: capsule.version
        },
        preview: previewSummary,
        asset: assetResult || null,
        hash: hashSummary
      });
    } catch (error) {
      if (error.statusCode === 400) {
        res.status(400).json({
          status: 'error',
          errors: error.errors || []
        });
        return;
      }
      next(error);
    }
  });

  return router;
}

function assertSentinelCapability(sentinel, method) {
  if (!sentinel || typeof sentinel[method] !== 'function') {
    throw new Error(`Sentinel is missing ${method} implementation`);
  }
}

function buildPreviewOptions(config) {
  const options = {};
  if (config.out_dir) {
    options.outDir = config.out_dir;
  }
  if (config.descriptor_path) {
    options.descriptorPath = config.descriptor_path;
  }
  if (typeof config.persist_descriptor === 'boolean') {
    options.persistDescriptor = config.persist_descriptor;
  }
  return options;
}

function buildAssetOptions(config) {
  const options = {};
  if (config.path) {
    options.path = config.path;
  }
  if (config.method) {
    options.method = config.method;
  }
  if (config.headers) {
    options.headers = config.headers;
  }
  return options;
}

function buildHashInputs(config, previewResult) {
  const inputs = [];
  if (Array.isArray(config.inputs)) {
    for (const entry of config.inputs) {
      if (typeof entry === 'string' && entry.length > 0) {
        inputs.push(entry);
      }
    }
  }
  const previewPath = extractPreviewPath(previewResult);
  if (previewPath) {
    inputs.push(previewPath);
  }
  return inputs;
}

function buildHashOptions(config = {}) {
  const options = {};
  if (config.out_dir) {
    options.outDir = config.out_dir;
  }
  if (config.events_path) {
    options.events = config.events_path;
  }
  if (config.capsule_id) {
    options.capsuleId = config.capsule_id;
  }
  if (config.actor) {
    options.actor = config.actor;
  }
  if (config.commit) {
    options.commit = config.commit;
  }
  if (config.run_id) {
    options.runId = config.run_id;
  }
  if (config.sign_key) {
    options.signKey = config.sign_key;
  }
  return options;
}

function extractPreviewPath(previewResult) {
  if (!previewResult || typeof previewResult.stdout !== 'string') {
    return null;
  }
  const firstLine = previewResult.stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => line.length > 0);
  return firstLine || null;
}

function summarizePreview(previewResult) {
  if (!previewResult) {
    return null;
  }
  return {
    out_dir: previewResult.outDir || null,
    stdout: previewResult.stdout || '',
    stderr: previewResult.stderr || ''
  };
}

function summarizeHash(hashResult) {
  if (!hashResult) {
    return null;
  }
  return {
    merkle_root: hashResult.merkleRoot,
    batch_dir: hashResult.batchDir,
    stdout: hashResult.stdout || '',
    stderr: hashResult.stderr || ''
  };
}

module.exports = createCapsuleRouter;
