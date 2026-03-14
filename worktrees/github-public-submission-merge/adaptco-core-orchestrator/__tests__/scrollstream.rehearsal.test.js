// adaptco-core-orchestrator/__tests__/scrollstream.rehearsal.test.js
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { promisify } = require('util');
const { execFile } = require('child_process');
const { emitScrollstreamRehearsal, CAPSULE_ID } = require('../src/rehearsal');
const { scrollstreamLedgerFile } = require('../src/scrollstream-ledger');

const execFileAsync = promisify(execFile);

function removeFileIfExists(filePath) {
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
  }
}

describe('scrollstream rehearsal capsule', () => {
  beforeEach(() => {
    removeFileIfExists(scrollstreamLedgerFile);
  });

  afterAll(() => {
    removeFileIfExists(scrollstreamLedgerFile);
  });

  it('emits the rehearsal cycle with deterministic payloads', async () => {
    const timestamps = [
      '2025-04-01T12:00:00.000Z',
      '2025-04-01T12:00:01.000Z',
      '2025-04-01T12:00:02.000Z'
    ];
    const entries = [];

    const result = await emitScrollstreamRehearsal({
      now: (index) => timestamps[index],
      appendEvent: async (entry) => {
        entries.push(entry);
      }
    });

    expect(result.capsule_id).toBe(CAPSULE_ID);
    expect(result.cycle).toBe('celine-luma-dot');
    expect(result.total_events).toBe(3);
    expect(result.events).toHaveLength(3);
    expect(entries).toHaveLength(3);

    entries.forEach((entry, index) => {
      expect(entry.ts).toBe(timestamps[index]);
      expect(entry.sequence).toBe(index + 1);
      expect(entry.capsule_id).toBe(CAPSULE_ID);
      expect(entry.cycle).toBe('celine-luma-dot');
      expect(entry.agent).toHaveProperty('name');
      expect(entry.output).toHaveProperty('hud');
      expect(entry.output).toHaveProperty('payload');
      expect(entry.output.payload).toHaveProperty('emotion');
      expect(entry.output.training || entry.output.diagnostics || entry.output.ledger).toBeDefined();
    });

    expect(entries.map((entry) => entry.phase)).toEqual(['Celine', 'Luma', 'Dot']);
    expect(entries.map((entry) => entry.event)).toEqual([
      'audit.summary',
      'audit.proof',
      'audit.execution'
    ]);
    expect(entries[0].output.training.sabrinaSpark).toBe('PASS');
    expect(entries[1].output.diagnostics.sabrinaSpark).toBe('PASS');
    expect(entries[2].output.training.sabrinaSpark).toBe('PASS');
  });

  it('writes the rehearsal cycle to the scrollstream ledger by default', async () => {
    const timestamps = [
      '2025-04-02T10:15:00.000Z',
      '2025-04-02T10:15:01.000Z',
      '2025-04-02T10:15:02.000Z'
    ];
    let callIndex = 0;

    await emitScrollstreamRehearsal({
      now: () => timestamps[callIndex++]
    });

    expect(fs.existsSync(scrollstreamLedgerFile)).toBe(true);
    const raw = fs.readFileSync(scrollstreamLedgerFile, 'utf8').trim();
    const lines = raw.split('\n');
    expect(lines).toHaveLength(3);
    const parsed = lines.map((line) => JSON.parse(line));

    expect(parsed.map((entry) => entry.ts)).toEqual(timestamps);
    expect(parsed.map((entry) => entry.phase)).toEqual(['Celine', 'Luma', 'Dot']);
    expect(parsed[0].output.hud.shimmer).toBe('ignition');
    expect(parsed[1].output.replay.glyph).toBe('luma');
    expect(parsed[2].output.ledger.merkleRootPreview).toBe('merkle:scrollstream:rehearsal:v1');
  });

  it('runs through the CLI and records entries to a specified ledger', async () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'scrollstream-ledger-'));
    const ledgerPath = path.join(tempDir, 'ledger.jsonl');

    const { stdout, stderr } = await execFileAsync('node', ['src/bin/rehearsal.js', '--ledger', ledgerPath], {
      cwd: path.join(__dirname, '..')
    });

    expect(stderr).toBe('');
    const result = JSON.parse(stdout);
    expect(result.capsule_id).toBe(CAPSULE_ID);
    expect(result.events).toHaveLength(3);
    expect(result.hud_status).toBe('shimmer-complete');

    const ledgerLines = fs.readFileSync(ledgerPath, 'utf8').trim().split('\n');
    expect(ledgerLines).toHaveLength(3);
    const ledgerEntries = ledgerLines.map((line) => JSON.parse(line));
    expect(ledgerEntries[0].agent.name).toBe('Celine');
    expect(ledgerEntries[1].agent.name).toBe('Luma');
    expect(ledgerEntries[2].agent.name).toBe('Dot');

    fs.rmSync(tempDir, { recursive: true, force: true });
  });
});
