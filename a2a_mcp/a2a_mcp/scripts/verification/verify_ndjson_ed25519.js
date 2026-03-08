#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DEFAULT_LEDGER_PATH = path.resolve(process.env.ANNOTATION_LEDGER_PATH || '.out/viewer_annotations.jsonl');
const DEFAULT_REGISTRY_PATH = path.resolve(
  process.env.RUNTIME_REGISTRY_PATH || 'capsules/runtime/capsule.registry.runtime.v1.json'
);
const DEFAULT_GLYPH_REGISTRY_PATH = path.resolve(
  process.env.GLYPH_REGISTRY_PATH || 'capsules/glyphs/glyph.registry.qube.v1.json'
);
const REPORT_PATH = path.resolve(process.env.ANNOTATION_REPORT_PATH || '.out/annotation_verification_report.json');

function readJsonLines(filePath) {
  const payload = fs.readFileSync(filePath, 'utf8');
  return payload
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      try {
        return JSON.parse(line);
      } catch (error) {
        throw new Error(`Unable to parse JSON on line ${index + 1}: ${error.message}`);
      }
    });
}

function canonicalize(value) {
  if (Array.isArray(value)) {
    return value.map((item) => canonicalize(item));
  }
  if (value && typeof value === 'object') {
    return Object.keys(value)
      .sort()
      .reduce((accumulator, key) => {
        const val = value[key];
        if (typeof val === 'undefined') {
          return accumulator;
        }
        accumulator[key] = canonicalize(val);
        return accumulator;
      }, {});
  }
  return value;
}

function canonicalStringify(value) {
  return JSON.stringify(canonicalize(value));
}

function ensureOutDirExists(filePath) {
  const directory = path.dirname(filePath);
  if (!fs.existsSync(directory)) {
    fs.mkdirSync(directory, { recursive: true });
  }
}

function normalizePublicKey(publicKeyValue) {
  if (!publicKeyValue) {
    return { error: 'Missing public key value.' };
  }

  try {
    if (typeof publicKeyValue === 'string' && publicKeyValue.includes('BEGIN')) {
      return crypto.createPublicKey(publicKeyValue);
    }

    const buffer = Buffer.from(publicKeyValue, 'base64');
    if (buffer.length === 0) {
      return { error: 'Public key was empty after decoding.' };
    }

    if (buffer.length === 32) {
      const derPrefix = Buffer.from('302a300506032b6570032100', 'hex');
      return crypto.createPublicKey({ key: Buffer.concat([derPrefix, buffer]), format: 'der', type: 'spki' });
    }

    return crypto.createPublicKey({ key: buffer, format: 'der', type: 'spki' });
  } catch (error) {
    return { error: `Unable to decode public key: ${error.message}` };
  }
}

function decodeSignature(signatureValue) {
  if (!signatureValue) {
    return null;
  }

  if (typeof signatureValue === 'string') {
    try {
      const decoded = Buffer.from(signatureValue, 'base64');
      if (decoded.length === 0) {
        return { error: 'Signature was empty after decoding.' };
      }
      if (decoded.length !== 64) {
        return { error: `Signature length ${decoded.length} bytes does not match Ed25519 requirement of 64 bytes.` };
      }
      return decoded;
    } catch (error) {
      return { error: `Unable to decode signature: ${error.message}` };
    }
  }

  if (Buffer.isBuffer(signatureValue)) {
    if (signatureValue.length !== 64) {
      return { error: `Signature length ${signatureValue.length} bytes does not match Ed25519 requirement of 64 bytes.` };
    }
    return signatureValue;
  }

  return { error: 'Unsupported signature format. Expected base64 string or Buffer.' };
}

function verifySignature(entry) {
  if (!entry.signature || !entry.public_key) {
    return { status: 'SKIPPED', reason: 'MISSING_FIELDS' };
  }

  const signature = decodeSignature(entry.signature);
  if (signature && signature.error) {
    return { status: 'ERROR', reason: signature.error };
  }
  if (!signature) {
    return { status: 'ERROR', reason: 'Signature could not be decoded.' };
  }

  const normalizedKey = normalizePublicKey(entry.public_key);
  if (normalizedKey.error) {
    return { status: 'ERROR', reason: normalizedKey.error };
  }

  const payload = { ...entry };
  delete payload.signature;
  delete payload.public_key;

  const canonicalPayload = canonicalStringify(payload);
  try {
    const verified = crypto.verify(
      null,
      Buffer.from(canonicalPayload),
      normalizedKey,
      signature
    );

    return verified
      ? { status: 'VALID' }
      : { status: 'INVALID', reason: 'Signature mismatch for canonical payload.' };
  } catch (error) {
    return { status: 'ERROR', reason: error.message };
  }
}

function verifyReplayToken(entry, registry) {
  if (!registry || !registry.capsules) {
    return { status: 'REGISTRY_MISSING' };
  }
  if (!entry.scene) {
    return { status: 'INVALID', reason: 'Missing scene identifier on annotation.' };
  }

  const capsule = registry.capsules[entry.scene];
  if (!capsule) {
    return { status: 'UNKNOWN_SCENE' };
  }

  if (!('replay' in capsule)) {
    return { status: 'NO_REPLAY_IN_REGISTRY' };
  }

  if (!entry.replay_token) {
    return { status: 'MISSING', expected: capsule.replay };
  }

  if (capsule.replay === entry.replay_token) {
    return { status: 'MATCH' };
  }

  return { status: 'MISMATCH', expected: capsule.replay, received: entry.replay_token };
}

function loadGlyphRegistry(glyphRegistryPath) {
  if (!fs.existsSync(glyphRegistryPath)) {
    return { glyphs: null, status: 'REGISTRY_NOT_FOUND' };
  }

  try {
    const payload = JSON.parse(fs.readFileSync(glyphRegistryPath, 'utf8'));
    if (payload && typeof payload === 'object' && payload.glyphs && typeof payload.glyphs === 'object') {
      return { glyphs: payload.glyphs, status: 'OK' };
    }
    return { glyphs: {}, status: 'NO_GLYPHS_FIELD' };
  } catch (error) {
    return { glyphs: null, status: `ERROR: ${error.message}` };
  }
}

function verifyGlyph(entry, glyphRegistry) {
  if (!entry.glyph_id) {
    return { status: 'MISSING' };
  }

  if (!glyphRegistry) {
    return { status: 'REGISTRY_UNAVAILABLE' };
  }

  if (glyphRegistry[entry.glyph_id]) {
    return { status: 'FOUND' };
  }

  return { status: 'UNKNOWN', suggestion: 'Ensure glyph registry is up to date.' };
}

function main() {
  try {
    if (!fs.existsSync(DEFAULT_LEDGER_PATH)) {
      console.error(`❌ Annotation ledger not found at ${DEFAULT_LEDGER_PATH}`);
      process.exitCode = 1;
      return;
    }

    const annotations = readJsonLines(DEFAULT_LEDGER_PATH);
    const registry = fs.existsSync(DEFAULT_REGISTRY_PATH)
      ? JSON.parse(fs.readFileSync(DEFAULT_REGISTRY_PATH, 'utf8'))
      : null;
    const glyphRegistryState = loadGlyphRegistry(DEFAULT_GLYPH_REGISTRY_PATH);

    const report = annotations.map((entry, index) => ({
      index,
      scene: entry.scene || null,
      frame: entry.frame || null,
      signature: verifySignature(entry),
      replay_token: verifyReplayToken(entry, registry),
      glyph: verifyGlyph(entry, glyphRegistryState.glyphs),
      severity: entry.severity || null,
      tag: entry.tag || null,
    }));

    ensureOutDirExists(REPORT_PATH);
    fs.writeFileSync(REPORT_PATH, JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        ledger: path.relative(process.cwd(), DEFAULT_LEDGER_PATH),
        runtime_registry: fs.existsSync(DEFAULT_REGISTRY_PATH)
          ? path.relative(process.cwd(), DEFAULT_REGISTRY_PATH)
          : null,
        glyph_registry_state: glyphRegistryState.status,
        entries: report,
      },
      null,
      2
    ));

    console.log(`✅ Verification complete → ${path.relative(process.cwd(), REPORT_PATH)}`);
  } catch (error) {
    console.error(`❌ Verification failed: ${error.message}`);
    process.exitCode = 1;
  }
}

main();
