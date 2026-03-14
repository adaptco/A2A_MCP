'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const {
  CAPSULE_ID,
  DEFAULT_BASE_TIMESTAMP,
  DEFAULT_INTERVAL_SECONDS,
  REHEARSAL_SEQUENCE,
  createLedgerEntries,
  emitRehearsalLedger,
  writeScrollstreamLedger
} = require('../utils/scrollstreamRehearsal');

const TEMP_DIR_PREFIX = 'scrollstream-ledger-test-';

function withTempFile(callback) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), TEMP_DIR_PREFIX));
  const filePath = path.join(directory, 'ledger.json');
  try {
    return callback(filePath);
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

test('createLedgerEntries returns deterministic rehearsal cycle', () => {
  const entries = createLedgerEntries();
  assert.equal(entries.length, REHEARSAL_SEQUENCE.length);

  entries.forEach((entry, index) => {
    assert.equal(entry.capsuleId, CAPSULE_ID);
    assert.equal(entry.capsuleCycle.position, index + 1);
    assert.equal(entry.capsuleCycle.total, REHEARSAL_SEQUENCE.length);
    assert.ok(entry.timestamp.endsWith('Z'));
    assert.deepEqual(entry.agent, REHEARSAL_SEQUENCE[index].agent);
    assert.deepEqual(entry.output, REHEARSAL_SEQUENCE[index].output);
    assert.equal(entry.training.deterministic, true);
    assert.equal(entry.training.mode, 'rehearsal');
    assert.equal(entry.training.sabrinaSparkTest, 'pass');
  });

  assert.equal(entries[entries.length - 1].visual.replayGlyphPulse, true);
  assert.equal(entries[0].visual.replayGlyphPulse, false);
});

test('createLedgerEntries allows overriding base timestamp and interval', () => {
  const baseTimestamp = '2025-04-01T00:00:00.000Z';
  const intervalSeconds = 60;
  const entries = createLedgerEntries({ baseTimestamp, intervalSeconds });

  const expectedTimestamps = entries.map((entry, index) =>
    new Date(Date.parse(baseTimestamp) + index * intervalSeconds * 1000).toISOString()
  );
  const actualTimestamps = entries.map((entry) => entry.timestamp);
  assert.deepEqual(actualTimestamps, expectedTimestamps);
});

test('createLedgerEntries throws on invalid options', () => {
  assert.throws(() => createLedgerEntries({ baseTimestamp: 'not-a-date' }), /Invalid base timestamp/);
  assert.throws(() => createLedgerEntries({ intervalSeconds: -1 }), /Invalid intervalSeconds/);
  assert.throws(() => createLedgerEntries({ intervalSeconds: 'abc' }), /Invalid intervalSeconds/);
});

test('writeScrollstreamLedger writes JSON payload', () => {
  withTempFile((filePath) => {
    const entries = createLedgerEntries();
    writeScrollstreamLedger(filePath, entries);
    const content = fs.readFileSync(filePath, 'utf8');
    assert.ok(content.includes(CAPSULE_ID));
    const parsed = JSON.parse(content);
    assert.equal(parsed.length, entries.length);
  });
});

test('emitRehearsalLedger writes to disk and returns entries', () => {
  withTempFile((filePath) => {
    const entries = emitRehearsalLedger({
      outputPath: filePath,
      baseTimestamp: DEFAULT_BASE_TIMESTAMP,
      intervalSeconds: DEFAULT_INTERVAL_SECONDS
    });
    assert.ok(fs.existsSync(filePath));
    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    assert.equal(parsed.length, entries.length);
    assert.deepEqual(parsed[0].agent, entries[0].agent);
  });
});
