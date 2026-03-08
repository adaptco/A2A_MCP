// adaptco-core-orchestrator/__tests__/ledger.append.test.js
"use strict";

const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');

const storageDir = path.join(__dirname, '..', 'storage');
const ledgerPath = path.join(storageDir, 'ledger.jsonl');
const anchorPath = `${ledgerPath}.anchor.json`;

async function cleanupLedgerFiles() {
  await Promise.all([
    fsp.rm(ledgerPath, { force: true }),
    fsp.rm(anchorPath, { force: true })
  ]);
}

describe('ledger appendEvent serialization', () => {
  beforeEach(async () => {
    await cleanupLedgerFiles();
    jest.resetModules();
  });

  afterEach(async () => {
    await cleanupLedgerFiles();
  });

  it('serializes concurrent appends to preserve hash continuity', async () => {
    const ledger = require('../src/ledger');

    const [first, second, third] = await Promise.all([
      ledger.appendEvent('test.event', { index: 0 }),
      ledger.appendEvent('test.event', { index: 1 }),
      ledger.appendEvent('test.event', { index: 2 })
    ]);

    expect(first.prev_hash).toBe(ledger.ZERO_HASH);
    expect(second.prev_hash).toBe(first.hash);
    expect(third.prev_hash).toBe(second.hash);

    const lines = fs.readFileSync(ledger.ledgerFile, 'utf8')
      .trim()
      .split('\n');
    expect(lines).toHaveLength(4);

    const parsed = lines.map((line) => JSON.parse(line));
    parsed.forEach((entry, index) => {
      const previous = parsed[index - 1];
      const expectedPrev = !previous || previous.type === 'file_genesis' ? ledger.ZERO_HASH : previous.hash;
      expect(entry.prev_hash).toBe(index === 0 ? ledger.ZERO_HASH : expectedPrev);
    });
  });

  it('updates the anchor file with the latest offset and hash', async () => {
    const ledger = require('../src/ledger');

    const entry = await ledger.appendEvent('test.anchor', { foo: 'bar' });

    const anchor = JSON.parse(fs.readFileSync(ledger.ledgerAnchorFile, 'utf8'));
    expect(anchor.file).toBe(ledger.ledgerFile);
    expect(anchor.last_hash).toBe(entry.hash);
    expect(anchor.last_offset).toBeGreaterThan(0);
    expect(new Date(anchor.updated_at).toString()).not.toBe('Invalid Date');
  });

  it('recovers from a failed append and continues serial execution', async () => {
    const ledger = require('../src/ledger');

    const openSpy = jest.spyOn(fs.promises, 'open').mockImplementationOnce(() => {
      return Promise.reject(new Error('disk full'));
    });

    await expect(
      ledger.appendEvent('test.failure', { index: -1 })
    ).rejects.toThrow('disk full');

    openSpy.mockRestore();

    const entry = await ledger.appendEvent('test.event', { index: 0 });

    const lines = fs
      .readFileSync(ledger.ledgerFile, 'utf8')
      .trim()
      .split('\n');
    expect(lines).toHaveLength(2);
    expect(JSON.parse(lines[1]).hash).toBe(entry.hash);
  });

  it('waitForPendingAppends resolves once queued operations settle', async () => {
    const ledger = require('../src/ledger');

    const openSpy = jest.spyOn(fs.promises, 'open').mockImplementationOnce(() => {
      return Promise.reject(new Error('disk full'));
    });

    const failed = ledger
      .appendEvent('test.failure', { index: -1 })
      .catch((error) => error);

    const success = ledger.appendEvent('test.event', { index: 1 });

    await ledger.waitForPendingAppends();
    openSpy.mockRestore();

    const failure = await failed;
    expect(failure).toBeInstanceOf(Error);
    expect(failure.message).toBe('disk full');

    const entry = await success;
    expect(entry.type).toBe('test.event');

    const lines = fs
      .readFileSync(ledger.ledgerFile, 'utf8')
      .trim()
      .split('\n');
    expect(lines).toHaveLength(2);
    expect(JSON.parse(lines[1]).hash).toBe(entry.hash);
  });
});
