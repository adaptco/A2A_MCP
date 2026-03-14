// adaptco-core-orchestrator/src/scrollstream-ledger.js
'use strict';

const fs = require('fs');
const path = require('path');
const logger = require('./log');

const storageDir = path.join(__dirname, '..', 'storage');
const defaultLedgerFile = path.join(storageDir, 'scrollstream_ledger.jsonl');

function validateEntry(entry) {
  if (!entry || typeof entry !== 'object') {
    throw new TypeError('Scrollstream ledger entry must be an object');
  }

  const requiredKeys = ['ts', 'capsule_id', 'event', 'agent', 'output'];
  const missing = requiredKeys.filter((key) => entry[key] === undefined || entry[key] === null);
  if (missing.length > 0) {
    throw new Error(`Scrollstream ledger entry missing required fields: ${missing.join(', ')}`);
  }

  if (typeof entry.ts !== 'string') {
    throw new TypeError('Scrollstream ledger entry ts must be a string');
  }

  if (typeof entry.capsule_id !== 'string') {
    throw new TypeError('Scrollstream ledger entry capsule_id must be a string');
  }

  if (typeof entry.event !== 'string') {
    throw new TypeError('Scrollstream ledger entry event must be a string');
  }

  if (!entry.agent || typeof entry.agent !== 'object') {
    throw new TypeError('Scrollstream ledger entry agent must be an object');
  }

  if (!entry.output || typeof entry.output !== 'object') {
    throw new TypeError('Scrollstream ledger entry output must be an object');
  }
}

function createScrollstreamWriter(targetPath = defaultLedgerFile) {
  const resolvedPath = path.resolve(targetPath);

  return async (entry) => {
    validateEntry(entry);

    await fs.promises.mkdir(path.dirname(resolvedPath), { recursive: true });
    const line = `${JSON.stringify(entry)}\n`;
    await fs.promises.appendFile(resolvedPath, line, 'utf8');
    logger.debug(
      { event: entry.event, capsule: entry.capsule_id },
      'Scrollstream ledger event appended'
    );
    return entry;
  };
}

const appendScrollstreamEvent = createScrollstreamWriter();

module.exports = {
  appendScrollstreamEvent,
  createScrollstreamWriter,
  scrollstreamLedgerFile: defaultLedgerFile
};
