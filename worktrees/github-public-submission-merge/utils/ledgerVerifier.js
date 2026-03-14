'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

/**
 * Recursively sort object keys to provide a canonical representation.
 *
 * This avoids discrepancies in JSON stringification ordering when
 * computing hashes for ledger entries.
 *
 * @param {unknown} value - Arbitrary JSON value.
 * @returns {unknown} Canonicalised clone with sorted object keys.
 */
function canonicalise(value) {
  if (Array.isArray(value)) {
    return value.map(canonicalise);
  }

  if (value && typeof value === 'object') {
    const sortedKeys = Object.keys(value)
      .filter((key) => value[key] !== undefined)
      .sort();
    const result = {};
    for (const key of sortedKeys) {
      result[key] = canonicalise(value[key]);
    }
    return result;
  }

  return value;
}

/**
 * Produce a canonical JSON string for a given value.
 *
 * @param {unknown} value - Arbitrary JSON value.
 * @returns {string} Deterministic JSON string with sorted object keys.
 */
function canonicalStringify(value) {
  return JSON.stringify(canonicalise(value));
}

/**
 * Compute the expected SHA-256 hash for a ledger entry.
 * The hash covers all fields other than `hash` and `signature`.
 *
 * @param {object} entry - Ledger entry to hash.
 * @returns {string} Hex-encoded SHA-256 digest.
 */
function computeEntryHash(entry) {
  if (!entry || typeof entry !== 'object') {
    throw new TypeError('Ledger entry must be an object');
  }

  const { hash: _hash, signature: _signature, ...content } = entry;
  const canonical = canonicalStringify(content);
  return crypto.createHash('sha256').update(canonical).digest('hex');
}

/**
 * Verify the signature for a ledger entry.
 *
 * @param {object} entry - Ledger entry with `hash` and `signature` fields.
 * @param {string} publicKeyPem - PEM encoded public key.
 * @returns {boolean} True if the signature validates.
 */
function verifyEntrySignature(entry, publicKeyPem) {
  if (!entry.hash || !entry.signature) {
    return false;
  }

  if (!publicKeyPem) {
    throw new Error('Public key is required to verify signatures');
  }

  const verifier = crypto.createVerify('SHA256');
  verifier.update(entry.hash);
  verifier.end();

  try {
    return verifier.verify(publicKeyPem, entry.signature, 'base64');
  } catch (error) {
    return false;
  }
}

/**
 * Verify a ledger in-memory.
 *
 * @param {Array<object>} ledger - Parsed ledger entries.
 * @param {string} publicKeyPem - PEM encoded public key.
 * @returns {{ok: boolean, errors: string[]}} Verification result.
 */
function verifyLedger(ledger, publicKeyPem) {
  if (!Array.isArray(ledger)) {
    throw new TypeError('Ledger data must be an array of entries');
  }

  const errors = [];

  for (let i = 0; i < ledger.length; i += 1) {
    const entry = ledger[i];

    if (!entry || typeof entry !== 'object') {
      errors.push(`Entry at index ${i} is not a valid object`);
      continue;
    }

    if (!('hash' in entry)) {
      errors.push(`Missing hash field at index ${i}`);
    } else {
      const expectedHash = computeEntryHash(entry);
      if (entry.hash !== expectedHash) {
        errors.push(`Hash mismatch at index ${i}: expected ${expectedHash} but found ${entry.hash}`);
      }
    }

    if (i > 0) {
      const prevHash = ledger[i - 1] && ledger[i - 1].hash;
      if (entry.prevHash !== prevHash) {
        errors.push(
          `Chain broken at index ${i}: prevHash ${entry.prevHash ?? 'null'} does not match previous hash ${prevHash ?? 'null'}`
        );
      }
    }

    if (!('signature' in entry)) {
      errors.push(`Missing signature field at index ${i}`);
    } else if (!verifyEntrySignature(entry, publicKeyPem)) {
      errors.push(`Invalid signature at index ${i}`);
    }
  }

  return {
    ok: errors.length === 0,
    errors
  };
}

/**
 * Parse ledger data from a file.
 *
 * @param {string} filePath - Path to ledger file (JSON array or JSONL).
 * @returns {Array<object>} Parsed ledger entries.
 */
function loadLedger(filePath) {
  const contents = fs.readFileSync(filePath, 'utf8');
  const ext = path.extname(filePath).toLowerCase();

  if (ext === '.jsonl' || ext === '.ndjson') {
    return contents
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0)
      .map((line, index) => {
        try {
          return JSON.parse(line);
        } catch (error) {
          throw new SyntaxError(`Invalid JSON on line ${index + 1}: ${error.message}`);
        }
      });
  }

  const data = JSON.parse(contents);
  if (!Array.isArray(data)) {
    throw new TypeError('Ledger JSON must be an array of entries');
  }
  return data;
}

/**
 * Verify a ledger file against a public key.
 *
 * @param {string} ledgerPath - Path to ledger JSON/JSONL file.
 * @param {string} publicKeyPath - Path to PEM encoded public key.
 * @returns {{ok: boolean, errors: string[], ledger: Array<object>}} Result object.
 */
function verifyLedgerFile(ledgerPath, publicKeyPath) {
  const ledger = loadLedger(ledgerPath);
  const publicKeyPem = fs.readFileSync(publicKeyPath, 'utf8');
  const result = verifyLedger(ledger, publicKeyPem);
  return { ...result, ledger };
}

module.exports = {
  canonicalise,
  canonicalStringify,
  computeEntryHash,
  verifyEntrySignature,
  verifyLedger,
  loadLedger,
  verifyLedgerFile
};
