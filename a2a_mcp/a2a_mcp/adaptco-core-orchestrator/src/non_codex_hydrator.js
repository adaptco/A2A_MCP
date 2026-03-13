'use strict';

/**
 * Normalize legacy/non-Codex orchestration payloads so they satisfy the runtime
 * expectations of the unified orchestrator deployer.
 *
 * Historically, human-authored ("non Codex") capsule registrations would omit
 * optional fields that downstream modules now rely on. This hydrator performs
 * a best-effort fixup so that preview descriptors, asset payloads, and hash
 * jobs always contain the minimum structure required by the modern pipeline.
 *
 * The function never mutates the original `operations` object – callers receive
 * a deep clone with any inferred defaults applied.
 *
 * @param {object|undefined|null} operations
 * @returns {object} Normalized operations payload.
 */
function hydrateNonCodexOperations(operations) {
  if (!operations || typeof operations !== 'object') {
    return {};
  }

  const normalized = {};

  if (operations.preview && typeof operations.preview === 'object') {
    normalized.preview = normalizePreview(operations.preview);
  }

  if (operations.asset && typeof operations.asset === 'object') {
    normalized.asset = normalizeAsset(operations.asset);
  }

  if (operations.hash && typeof operations.hash === 'object') {
    normalized.hash = normalizeHash(operations.hash);
  }

  return normalized;
}

function normalizePreview(preview) {
  const normalized = { ...preview };
  const descriptor = normalized.descriptor;

  if (descriptor && typeof descriptor === 'object' && !Array.isArray(descriptor)) {
    normalized.descriptor = {
      params: {},
      ...descriptor
    };

    if (typeof normalized.descriptor.params !== 'object' || Array.isArray(normalized.descriptor.params)) {
      normalized.descriptor.params = {};
    }
  }

  return normalized;
}

function normalizeAsset(asset) {
  const normalized = { ...asset };
  const payload = normalized.payload;

  if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
    normalized.payload = { ...payload };

    if (!Array.isArray(normalized.payload.tags)) {
      if (typeof normalized.payload.tags === 'string' && normalized.payload.tags.length > 0) {
        normalized.payload.tags = [normalized.payload.tags];
      } else {
        normalized.payload.tags = [];
      }
    }

    if (typeof normalized.payload.meta !== 'object' || normalized.payload.meta === null) {
      normalized.payload.meta = {};
    }
  }

  return normalized;
}

function normalizeHash(hash) {
  const normalized = { ...hash };

  if (typeof normalized.inputs === 'string' && normalized.inputs.trim().length > 0) {
    normalized.inputs = [normalized.inputs];
  } else if (Array.isArray(normalized.inputs)) {
    normalized.inputs = normalized.inputs.filter((entry) => typeof entry === 'string' && entry.length > 0);
  }

  return normalized;
}

module.exports = hydrateNonCodexOperations;

