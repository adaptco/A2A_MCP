'use strict';

const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const {
  computeEntryHash,
  loadLedger,
  verifyLedger,
  verifyLedgerFile
} = require('../utils/ledgerVerifier');

const fixturesDir = path.join(__dirname, 'fixtures');
const ledgerJsonPath = path.join(fixturesDir, 'sample-ledger.json');
const ledgerJsonlPath = path.join(fixturesDir, 'sample-ledger.jsonl');
const publicKeyPath = path.join(fixturesDir, 'sample-ledger.pub');

test('computeEntryHash reproduces stored hashes', () => {
  const ledger = loadLedger(ledgerJsonPath);
  for (const [index, entry] of ledger.entries()) {
    const hash = computeEntryHash(entry);
    assert.strictEqual(hash, entry.hash, `hash mismatch for entry ${index}`);
  }
});

test('verifyLedger validates a well-formed ledger', () => {
  const ledger = loadLedger(ledgerJsonPath);
  const publicKey = fs.readFileSync(publicKeyPath, 'utf8');
  const result = verifyLedger(ledger, publicKey);
  assert.ok(result.ok, 'ledger should verify successfully');
  assert.deepStrictEqual(result.errors, []);
});

test('verifyLedger detects tampering', () => {
  const ledger = loadLedger(ledgerJsonPath);
  const publicKey = fs.readFileSync(publicKeyPath, 'utf8');
  const tampered = JSON.parse(JSON.stringify(ledger));
  tampered[1].event.version = '2.0.0';

  const result = verifyLedger(tampered, publicKey);
  assert.strictEqual(result.ok, false);
  assert(result.errors.some((message) => message.includes('Hash mismatch at index 1')));
});

test('verifyLedger detects invalid signatures', () => {
  const ledger = loadLedger(ledgerJsonPath);
  const publicKey = fs.readFileSync(publicKeyPath, 'utf8');
  const tampered = JSON.parse(JSON.stringify(ledger));
  tampered[1].signature = 'not-a-real-signature';

  const result = verifyLedger(tampered, publicKey);
  assert.strictEqual(result.ok, false);
  assert(result.errors.some((message) => message.includes('Invalid signature at index 1')));
});

test('verifyLedgerFile handles JSONL ledgers', () => {
  const result = verifyLedgerFile(ledgerJsonlPath, publicKeyPath);
  assert.ok(result.ok);
  assert.strictEqual(result.ledger.length, 3);
});

test('loadLedger throws when JSON content is not an array', async (t) => {
  const tempPath = path.join(fixturesDir, 'not-array.json');
  fs.writeFileSync(tempPath, '{"foo": "bar"}');
  t.after(() => fs.unlinkSync(tempPath));
  assert.throws(() => loadLedger(tempPath), /must be an array/);
});
