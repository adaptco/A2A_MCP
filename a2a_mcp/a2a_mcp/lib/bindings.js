'use strict';

const fs = require('fs');
const path = require('path');
const http = require('http');
const https = require('https');
const { URL } = require('url');
const { createHash, createPublicKey, verify } = require('crypto');

const DEFAULT_MAX_BYTES = 5 * 1024 * 1024;
const DEFAULT_CACHE_TTL = 7000;
const MIN_CACHE_TTL = 5000;
const MAX_CACHE_TTL = 10000;

let lastManifestMeta = null;
let hudCache = { value: null, expiresAt: 0 };

function sortKeys(value) {
  if (Array.isArray(value)) {
    return value.map(sortKeys);
  }
  if (value && typeof value === 'object') {
    const keys = Object.keys(value).sort();
    const sorted = {};
    for (const key of keys) {
      sorted[key] = sortKeys(value[key]);
    }
    return sorted;
  }
  return value;
}

function canonicalizeManifest(value) {
  return JSON.stringify(sortKeys(value), null, 2);
}

function manifestSignaturePayload(manifest) {
  if (!manifest || typeof manifest !== 'object') {
    return '';
  }
  const payload = { ...manifest };
  if (Object.prototype.hasOwnProperty.call(payload, 'signatures')) {
    delete payload.signatures;
  }
  return canonicalizeManifest(payload);
}

function decodePublicKey(base64Key) {
  if (!base64Key) {
    return null;
  }
  try {
    const keyBuffer = Buffer.from(String(base64Key).trim(), 'base64');
    if (!keyBuffer.length) {
      return null;
    }
    return createPublicKey({ key: keyBuffer, format: 'der', type: 'spki' });
  } catch (err) {
    return { error: err };
  }
}

function verifyDuoSig(payload, makerSig, checkerSig, keys) {
  const payloadBuffer = Buffer.isBuffer(payload) ? payload : Buffer.from(String(payload));
  const makerKey = decodePublicKey(keys && keys.maker);
  const checkerKey = decodePublicKey(keys && keys.checker);

  const result = {
    ok: false,
    maker: { verified: false, present: Boolean(makerSig) },
    checker: { verified: false, present: Boolean(checkerSig) },
    errors: []
  };

  if (!makerSig || !checkerSig) {
    result.errors.push('Missing maker and/or checker signature payloads');
    return result;
  }
  if (!makerKey || makerKey.error) {
    result.errors.push('Invalid maker public key');
  }
  if (!checkerKey || checkerKey.error) {
    result.errors.push('Invalid checker public key');
  }

  if (result.errors.length) {
    return result;
  }

  try {
    const makerVerified = verify(null, payloadBuffer, makerKey, Buffer.from(makerSig, 'base64'));
    result.maker.verified = makerVerified;
  } catch (err) {
    result.errors.push(`Maker signature verification failed: ${err.message}`);
  }

  try {
    const checkerVerified = verify(null, payloadBuffer, checkerKey, Buffer.from(checkerSig, 'base64'));
    result.checker.verified = checkerVerified;
  } catch (err) {
    result.errors.push(`Checker signature verification failed: ${err.message}`);
  }

  result.ok = result.maker.verified && result.checker.verified && result.errors.length === 0;
  return result;
}

function isHttpUrl(resource) {
  if (typeof resource !== 'string') {
    return false;
  }
  if (!/^https?:\/\//i.test(resource)) {
    return false;
  }
  try {
    const parsed = new URL(resource);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch (err) {
    return false;
  }
}

function readStream(stream, maxBytes) {
  return new Promise((resolve, reject) => {
    let total = 0;
    const chunks = [];
    stream.setEncoding('utf8');
    stream.on('data', (chunk) => {
      total += Buffer.byteLength(chunk);
      if (total > maxBytes) {
        stream.destroy();
        reject(new Error(`Resource exceeds maxBytes limit (${maxBytes})`));
        return;
      }
      chunks.push(chunk);
    });
    stream.on('end', () => {
      resolve(chunks.join(''));
    });
    stream.on('error', (err) => {
      reject(err);
    });
  });
}

function fetchHttpResource(resourceUrl, maxBytes) {
  const agent = resourceUrl.startsWith('https://') ? https : http;
  return new Promise((resolve, reject) => {
    const request = agent.get(resourceUrl, (response) => {
      if (response.statusCode && response.statusCode >= 400) {
        reject(new Error(`Failed to load ${resourceUrl} (status ${response.statusCode})`));
        response.resume();
        return;
      }
      readStream(response, maxBytes).then(resolve).catch(reject);
    });
    request.on('error', reject);
    request.setTimeout(5000, () => {
      request.destroy(new Error(`Timeout loading ${resourceUrl}`));
    });
  });
}

async function readResource(resource, maxBytes) {
  if (isHttpUrl(resource)) {
    return fetchHttpResource(resource, maxBytes);
  }
  return readStream(fs.createReadStream(resource, { encoding: 'utf8' }), maxBytes);
}

async function safeReadResource(resource, maxBytes) {
  try {
    return await readResource(resource, maxBytes);
  } catch (err) {
    return null;
  }
}

function siblingResource(resource, extension) {
  if (isHttpUrl(resource)) {
    return resource.replace(/\.json($|\?)/, `${extension}$1`);
  }
  const parsed = path.parse(resource);
  return path.join(parsed.dir, `${parsed.name}${extension}`);
}

function normalizeBinding(tuple) {
  if (!tuple || typeof tuple !== 'object') {
    return null;
  }
  const normalized = {
    avatar: tuple.avatar != null ? String(tuple.avatar).trim() : '',
    vessel: tuple.vessel != null ? String(tuple.vessel).trim().toLowerCase() : '',
    capsule: tuple.capsule != null ? String(tuple.capsule).trim().toLowerCase() : '',
    gate: tuple.gate != null ? String(tuple.gate).trim().toUpperCase() : ''
  };
  return normalized;
}

function verifyBinding(manifest, tuple) {
  const normalizedRequest = normalizeBinding(tuple);
  if (!normalizedRequest || !normalizedRequest.avatar || !normalizedRequest.vessel || !normalizedRequest.capsule || !normalizedRequest.gate) {
    return {
      ok: false,
      error: 'INVALID_BINDING_TUPLE',
      details: { requested: normalizedRequest }
    };
  }
  const table = Array.isArray(manifest && manifest.binding_table) ? manifest.binding_table : [];
  for (const entry of table) {
    const normalizedEntry = normalizeBinding(entry);
    if (!normalizedEntry) {
      continue;
    }
    if (
      normalizedEntry.avatar === normalizedRequest.avatar &&
      normalizedEntry.vessel === normalizedRequest.vessel &&
      normalizedEntry.capsule === normalizedRequest.capsule &&
      normalizedEntry.gate === normalizedRequest.gate
    ) {
      return {
        ok: true,
        binding: entry,
        normalized: normalizedRequest
      };
    }
  }
  return {
    ok: false,
    error: 'G1_SCOPE_VIOLATION',
    details: { requested: normalizedRequest }
  };
}

function sanitizeTTL(value) {
  const ttl = Number(value);
  if (!Number.isFinite(ttl)) {
    return DEFAULT_CACHE_TTL;
  }
  if (ttl < MIN_CACHE_TTL) {
    return MIN_CACHE_TTL;
  }
  if (ttl > MAX_CACHE_TTL) {
    return MAX_CACHE_TTL;
  }
  return ttl;
}

async function buildHudState(ledgerClient, opts = {}) {
  if (!ledgerClient || typeof ledgerClient.getLatestProof !== 'function') {
    throw new Error('ledgerClient.getLatestProof is required');
  }
  const force = opts.force === true || opts.force === 'true' || (opts.query && (opts.query.force === 'true' || opts.query.force === true));
  const ttl = sanitizeTTL(opts.cacheTTL);
  const now = Date.now();
  if (!force && hudCache.value && hudCache.expiresAt > now) {
    return hudCache.value;
  }
  const proof = await ledgerClient.getLatestProof();
  const scrollstreamEvents = typeof ledgerClient.getScrollstreamLedger === 'function'
    ? ledgerClient.getScrollstreamLedger()
    : [];
  const shimmerState = scrollstreamEvents.length ? 'engaged' : 'idle';
  const replayGlyph = scrollstreamEvents.length ? 'pulse' : 'idle';
  const lastCycleId = scrollstreamEvents.length ? scrollstreamEvents[scrollstreamEvents.length - 1].cycle_id : null;

  if (proof && !proof.scrollstream) {
    proof.scrollstream = {
      events: scrollstreamEvents.slice(-3),
      shimmer: shimmerState,
      replay_glyph: replayGlyph
    };
  }

  const state = {
    refreshed_at: new Date().toISOString(),
    proof,
    manifest_hash: lastManifestMeta ? lastManifestMeta.hash : null,
    scrollstream: {
      events: scrollstreamEvents,
      shimmer: shimmerState,
      replay_glyph: replayGlyph,
      last_cycle_id: lastCycleId
    }
  };
  hudCache = {
    value: state,
    expiresAt: now + ttl
  };
  return state;
}

async function loadManifest(resource, options = {}) {
  const maxBytes = options.maxBytes || DEFAULT_MAX_BYTES;
  const raw = await readResource(resource, maxBytes);
  let manifest;
  try {
    manifest = JSON.parse(raw);
  } catch (err) {
    const error = new Error(`Failed to parse manifest JSON from ${resource}: ${err.message}`);
    error.cause = err;
    throw error;
  }
  const canonicalRaw = canonicalizeManifest(manifest);
  const canonicalWithNewline = canonicalRaw.endsWith('\n') ? canonicalRaw : `${canonicalRaw}\n`;
  const hash = createHash('sha256').update(canonicalWithNewline).digest('hex');

  const hashResource = siblingResource(resource, '.hash');
  const sigResource = siblingResource(resource, '.sig');

  const expectedHashRaw = await safeReadResource(hashResource, 4096);
  const signatureBlob = await safeReadResource(sigResource, maxBytes);
  const expectedHash = expectedHashRaw ? expectedHashRaw.trim() : null;
  const hashMatches = Boolean(expectedHash && expectedHash === hash);
  const hasSignatureFile = Boolean(signatureBlob && signatureBlob.trim().length > 0);

  const makerSig = manifest && manifest.signatures && manifest.signatures.maker;
  const checkerSig = manifest && manifest.signatures && manifest.signatures.checker;
  const keys = {
    maker: manifest && manifest.maker && manifest.maker.public_key,
    checker: manifest && manifest.checker && manifest.checker.public_key
  };
  let duo = { ok: false, maker: { verified: false, present: false }, checker: { verified: false, present: false }, errors: ['Missing duo signatures'] };
  if (makerSig && checkerSig && keys.maker && keys.checker) {
    duo = verifyDuoSig(manifestSignaturePayload(manifest), makerSig, checkerSig, keys);
  } else {
    duo = {
      ok: false,
      maker: { verified: false, present: Boolean(makerSig) },
      checker: { verified: false, present: Boolean(checkerSig) },
      errors: ['Missing maker/checker signatures or keys']
    };
  }

  const verified = Boolean(hashMatches && hasSignatureFile && duo.ok);
  lastManifestMeta = {
    hash,
    source: resource,
    loaded_at: new Date().toISOString(),
    verified
  };

  return {
    manifest,
    canonical: canonicalWithNewline,
    signaturePayload: manifestSignaturePayload(manifest),
    hash,
    expectedHash,
    hashMatches,
    hasHashFile: Boolean(expectedHash),
    hasSignatureFile,
    signatureBlob: signatureBlob || null,
    duo,
    verified,
    loadedAt: lastManifestMeta.loaded_at,
    source: resource
  };
}

function getManifestHealth() {
  if (!lastManifestMeta) {
    return null;
  }
  return { ...lastManifestMeta };
}

function __dangerousResetHudCache() {
  hudCache = { value: null, expiresAt: 0 };
}

module.exports = {
  loadManifest,
  verifyBinding,
  buildHudState,
  verifyDuoSig,
  canonicalizeManifest,
  manifestSignaturePayload,
  normalizeBinding,
  getManifestHealth,
  __dangerousResetHudCache
};
