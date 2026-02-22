// adaptco-core-orchestrator/src/ledger.js
'use strict';

const fs = require('fs');
const path = require('path');
const { createHash, createSign } = require('crypto');
const logger = require('./log');

const ZERO_HASH = '0'.repeat(64);
const storageDir = path.join(__dirname, '..', 'storage');
const ledgerFile = path.join(storageDir, 'ledger.jsonl');
const ledgerAnchorFile = `${ledgerFile}.anchor.json`;
const ledgerDir = path.dirname(ledgerFile);

let currentOffset = 0;
let lastHash = ZERO_HASH;
let appendQueueTail = Promise.resolve();

function runSerialized(operation) {
  const run = appendQueueTail.then(() => operation());
  appendQueueTail = run.then(
    () => undefined,
    () => undefined
  );
  return run;
}

function waitForPendingAppends() {
  return appendQueueTail.then(() => undefined);
}

function ensureStorage() {
  fs.mkdirSync(ledgerDir, { recursive: true });
}

function getLedgerDirectory() {
  return ledgerDir;
}

function getCurrentLedgerFile() {
  ensureStorage();
  return ledgerFile;
}

function canonicalize(value) {
  if (Array.isArray(value)) {
    return value.map((item) => canonicalize(item));
  }
  if (value && typeof value === 'object' && !(value instanceof Date)) {
    const sortedKeys = Object.keys(value).sort();
    return sortedKeys.reduce((acc, key) => {
      acc[key] = canonicalize(value[key]);
      return acc;
    }, {});
  }
  return value;
}

function canonJson(value) {
  return JSON.stringify(canonicalize(value));
}

function computeHash(prevHash, recordWithoutHash) {
  const canonical = canonJson(recordWithoutHash);
  return createHash('sha256').update(`${prevHash}${canonical}`).digest('hex');
}

function signAnchor(anchorPayload) {
  const privateKey = process.env.ECDSA_SERVER_PRIV;
  if (!privateKey) {
    return null;
  }

  try {
    const signer = createSign('SHA256');
    signer.update(anchorPayload);
    signer.end();
    return signer.sign(privateKey, 'base64');
  } catch (error) {
    logger.warn({ err: error }, 'Failed to sign ledger anchor payload');
    return null;
  }
}

function readExistingLedgerState() {
  if (!fs.existsSync(ledgerFile)) {
    lastHash = ZERO_HASH;
    currentOffset = 0;
    return;
  }

  const raw = fs.readFileSync(ledgerFile, 'utf8');
  const lines = raw.split('\n').filter((line) => line.trim().length > 0);

  let expectedPrev = ZERO_HASH;
  for (const line of lines) {
    const parsed = JSON.parse(line);
    const { hash: storedHash, ...rest } = parsed;
    const prev = rest.prev_hash || ZERO_HASH;

    if (prev !== expectedPrev) {
      throw new Error('Ledger continuity check failed: prev_hash mismatch');
    }

    const computedHash = computeHash(prev, rest);
    if (storedHash !== computedHash) {
      throw new Error('Ledger continuity check failed: hash mismatch');
    }

    if (rest.type !== 'file_genesis') {
      expectedPrev = storedHash;
    }
  }

  lastHash = expectedPrev;
  currentOffset = fs.statSync(ledgerFile).size;
}

function ensureLedgerState() {
  ensureStorage();
  if (!fs.existsSync(ledgerFile)) {
    if (currentOffset !== 0 || lastHash !== ZERO_HASH) {
      lastHash = ZERO_HASH;
      currentOffset = 0;
    }
    return;
  }

  const stats = fs.statSync(ledgerFile);
  if (stats.size !== currentOffset) {
    readExistingLedgerState();
  }
}

async function ensureGenesis() {
  ensureStorage();
  const stats = await fs.promises.stat(ledgerFile).catch(() => null);
  if (stats && stats.size > 0) {
    return;
  }

  const recordedAt = new Date().toISOString();
  const recordWithoutHash = {
    at: recordedAt,
    payload: { previous_anchor: null },
    prev_hash: ZERO_HASH,
    type: 'file_genesis'
  };

  const hash = computeHash(ZERO_HASH, recordWithoutHash);
  const entry = { ...recordWithoutHash, hash };
  const line = `${canonJson(entry)}\n`;

  await fs.promises.writeFile(ledgerFile, line, 'utf8');
  lastHash = ZERO_HASH;
  currentOffset = Buffer.byteLength(line, 'utf8');
}

async function writeAnchor() {
  const baseAnchor = {
    file: ledgerFile,
    last_offset: currentOffset,
    last_hash: lastHash,
    updated_at: new Date().toISOString()
  };

  const payloadToSign = canonJson(baseAnchor);
  const signature = signAnchor(payloadToSign);
  const anchor = {
    ...baseAnchor,
    signature
  };

  const tmpPath = `${ledgerAnchorFile}.tmp`;
  await fs.promises.writeFile(tmpPath, `${canonJson(anchor)}\n`, 'utf8');
  await fs.promises.rename(tmpPath, ledgerAnchorFile);
}

async function appendEvent(type, payload) {
  return runSerialized(async () => {
    await ensureGenesis();
    ensureLedgerState();

    const recordedAt = new Date().toISOString();
    const recordWithoutHash = {
      at: recordedAt,
      payload,
      prev_hash: lastHash,
      type
    };

    const hash = computeHash(lastHash, recordWithoutHash);
    const entry = {
      ...recordWithoutHash,
      hash
    };

    const line = `${canonJson(entry)}\n`;

    const handle = await fs.promises.open(ledgerFile, 'a');
    try {
      await handle.write(line, 'utf8');
      await handle.sync();
    } finally {
      await handle.close();
    }

    const lineSize = Buffer.byteLength(line, 'utf8');
    currentOffset += lineSize;
    lastHash = hash;

    await writeAnchor();
    logger.info({ type, hash }, 'Ledger event appended');
    return entry;
  });
}

ensureStorage();
readExistingLedgerState();

module.exports = {
  appendEvent,
  ledgerFile,
  ledgerAnchorFile,
  getLedgerDirectory,
  getCurrentLedgerFile,
  waitForPendingAppends,
  ZERO_HASH
};
