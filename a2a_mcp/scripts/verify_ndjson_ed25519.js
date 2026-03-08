#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const LEDGER_PATH = path.resolve(process.cwd(), '.out', 'viewer_annotations.jsonl');
const REGISTRY_PATH = path.resolve(process.cwd(), 'capsule.registry.runtime.v1.json');
const GLYPHS_PATH = path.resolve(process.cwd(), 'glyph.registry.qube.v1.json');
const REPORT_PATH = path.resolve(process.cwd(), '.out', 'annotation_verification_report.json');

function readLines(filePath) {
  if (!fs.existsSync(filePath)) {
    const error = new Error(`Required ledger not found at ${filePath}`);
    error.code = 'ENOLEDGER';
    throw error;
  }

  const content = fs.readFileSync(filePath, 'utf8');
  return content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function readJson(filePath, fallback = {}) {
  if (!fs.existsSync(filePath)) {
    return fallback;
  }

  try {
    const data = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    throw new Error(`Failed to parse JSON from ${filePath}: ${error.message}`);
  }
}

function canonicalize(value) {
  if (Array.isArray(value)) {
    const canonicalItems = value.map((item) => canonicalize(item));
    return canonicalItems.sort((a, b) => {
      const left = JSON.stringify(a);
      const right = JSON.stringify(b);
      if (left < right) return -1;
      if (left > right) return 1;
      return 0;
    });
  }

  if (value && typeof value === 'object' && !(value instanceof Date)) {
    const sorted = {};
    for (const key of Object.keys(value).sort()) {
      sorted[key] = canonicalize(value[key]);
    }
    return sorted;
  }

  return value;
}

function canonicalStringify(value) {
  const canonical = canonicalize(value);
  return JSON.stringify(canonical);
}

function decodeSignature(signature) {
  if (typeof signature !== 'string' || signature.length === 0) {
    return null;
  }

  const attempts = [];

  try {
    attempts.push(Buffer.from(signature, 'base64'));
  } catch {}

  if (/^[A-Za-z0-9_-]+$/.test(signature)) {
    const normalized = signature.replace(/-/g, '+').replace(/_/g, '/');
    const padding = normalized.length % 4 === 0 ? '' : '='.repeat(4 - (normalized.length % 4));
    try {
      attempts.push(Buffer.from(normalized + padding, 'base64'));
    } catch {}
  }

  if (/^[0-9a-fA-F]+$/.test(signature) && signature.length % 2 === 0) {
    try {
      attempts.push(Buffer.from(signature, 'hex'));
    } catch {}
  }

  for (const candidate of attempts) {
    if (candidate && candidate.length > 0) {
      return candidate;
    }
  }

  return null;
}

function createEd25519Key(publicKey) {
  if (typeof publicKey !== 'string' || publicKey.length === 0) {
    return null;
  }

  try {
    if (publicKey.includes('BEGIN PUBLIC KEY')) {
      return crypto.createPublicKey(publicKey);
    }
  } catch {}

  let raw;
  try {
    raw = Buffer.from(publicKey, 'base64');
  } catch {
    raw = null;
  }

  if (!raw && /^[1-9A-HJ-NP-Za-km-z]+$/.test(publicKey)) {
    const alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
    const base = BigInt(58);
    let value = 0n;
    for (const char of publicKey) {
      const index = alphabet.indexOf(char);
      if (index < 0) {
        value = -1n;
        break;
      }
      value = value * base + BigInt(index);
    }
    if (value >= 0) {
      const bytes = [];
      while (value > 0n) {
        bytes.push(Number(value & 0xffn));
        value >>= 8n;
      }
      bytes.reverse();
      const leadingZeros = publicKey.match(/^1+/);
      if (leadingZeros) {
        bytes.unshift(...new Array(leadingZeros[0].length).fill(0));
      }
      raw = Buffer.from(bytes.length > 0 ? bytes : [0]);
    }
  }

  if (raw && raw.length > 0) {
    const attempts = [
      { format: 'der', type: 'spki', key: raw },
      { format: 'der', type: 'pkcs1', key: raw }
    ];

    for (const attempt of attempts) {
      try {
        return crypto.createPublicKey({ key: attempt.key, format: attempt.format, type: attempt.type });
      } catch {}
    }

    if (raw.length === 32) {
      const header = Buffer.from('302a300506032b6570032100', 'hex');
      const wrapped = Buffer.concat([header, raw]);
      try {
        return crypto.createPublicKey({ key: wrapped, format: 'der', type: 'spki' });
      } catch {}
    }
  }

  return null;
}

function verifySignature(entry) {
  if (!entry || !entry.signature || !entry.public_key) {
    return { status: 'SKIPPED' };
  }

  const keyObject = createEd25519Key(entry.public_key);
  if (!keyObject) {
    return { status: 'INVALID_KEY' };
  }

  const signature = decodeSignature(entry.signature);
  if (!signature) {
    return { status: 'INVALID_SIGNATURE' };
  }

  const payload = { ...entry };
  delete payload.signature;
  delete payload.public_key;

  const serialized = canonicalStringify(payload);

  try {
    const valid = crypto.verify(null, Buffer.from(serialized, 'utf8'), keyObject, signature);
    return { status: valid ? 'VALID' : 'INVALID' };
  } catch (error) {
    return { status: 'ERROR', error: error.message };
  }
}

function getGlyphIndex(glyphs) {
  if (Array.isArray(glyphs)) {
    const lookup = new Map();
    for (const glyph of glyphs) {
      if (glyph && typeof glyph.id === 'string') {
        lookup.set(glyph.id, glyph);
      }
    }
    return lookup;
  }

  if (glyphs && typeof glyphs === 'object') {
    return new Map(Object.entries(glyphs));
  }

  return new Map();
}

function verifyGlyph(entry, glyphLookup) {
  if (!entry || !entry.glyph_id) {
    return { status: 'MISSING' };
  }

  return glyphLookup.has(entry.glyph_id) ? { status: 'FOUND' } : { status: 'UNKNOWN' };
}

function verifyReplayToken(entry, registry) {
  if (!registry || typeof registry !== 'object') {
    return { status: 'NO_REGISTRY' };
  }

  const capsules = registry.capsules || registry;
  if (!capsules || typeof capsules !== 'object') {
    return { status: 'NO_CAPSULES' };
  }

  const capsuleKey = entry.scene || entry.capsule || entry.capsule_id;
  if (!capsuleKey) {
    return { status: 'MISSING_SCENE' };
  }

  const capsule = capsules[capsuleKey];
  if (!capsule) {
    return { status: 'NOT_FOUND' };
  }

  if (!entry.replay_token) {
    return { status: 'MISSING' };
  }

  const expected = capsule.replay || capsule.replay_token || capsule.replayToken;
  if (!expected) {
    return { status: 'NO_REFERENCE' };
  }

  return { status: entry.replay_token === expected ? 'MATCH' : 'MISMATCH', expected };
}

function main() {
  const lines = readLines(LEDGER_PATH);
  const registry = readJson(REGISTRY_PATH, {});
  const glyphRegistry = readJson(GLYPHS_PATH, {});
  const glyphLookup = getGlyphIndex(glyphRegistry.glyphs || glyphRegistry);

  const annotations = [];
  const errors = [];

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    try {
      const entry = JSON.parse(line);
      const signature = verifySignature(entry);
      const replayToken = verifyReplayToken(entry, registry);
      const glyph = verifyGlyph(entry, glyphLookup);

      annotations.push({
        index,
        scene: entry.scene || null,
        frame: entry.frame || null,
        signature: signature.status,
        replay_token: replayToken.status,
        glyph: glyph.status,
        severity: entry.severity || null,
        tag: entry.tag || null,
        ...(signature.error ? { signature_error: signature.error } : {}),
        ...(replayToken.expected ? { expected_replay_token: replayToken.expected } : {})
      });
    } catch (error) {
      errors.push({ index, error: error.message, line });
    }
  }

  const report = { annotations };
  if (errors.length > 0) {
    report.errors = errors;
  }

  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2));
  console.log(`✅ Verification complete → ${path.relative(process.cwd(), REPORT_PATH)}`);
}

try {
  main();
} catch (error) {
  console.error(`❌ Verification failed: ${error.message}`);
  process.exitCode = 1;
}
