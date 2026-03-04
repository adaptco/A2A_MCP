'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');
const assert = require('assert');

const scriptPath = path.join(__dirname, 'fixtures', 'scripts', 'mock_seal_root.sh');
const logPath = path.join(os.tmpdir(), `seal-root-log-${process.pid}-${Date.now()}.log`);

process.env.SEAL_ROOT_SCRIPT = scriptPath;
process.env.SEAL_ROOT_LOG = logPath;

const { createLedgerClient } = require('../server/ledger');

const manifestManager = {
  async getAuthorityMap() {
    return {
      hash: 'test-hash',
      expectedHash: 'test-hash',
      hashMatches: true,
      duo: {
        ok: true,
        maker: { verified: true },
        checker: { verified: true }
      },
      hasSignatureFile: true
    };
  }
};

const ledgerClient = createLedgerClient(manifestManager, 'test-policy', { logger: console });

function readLogEntries() {
  if (!fs.existsSync(logPath)) {
    return [];
  }
  const raw = fs.readFileSync(logPath, 'utf8');
  return raw
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .reduce((acc, line) => {
      if (line.startsWith('MERKLE_ROOT=')) {
        acc.push(line.slice('MERKLE_ROOT='.length));
      }
      return acc;
    }, []);
}

(async () => {
  try {
    if (fs.existsSync(logPath)) {
      fs.unlinkSync(logPath);
    }

    await ledgerClient.storeFreezeArtifact({
      name: 'authority_map.v1',
      hash: 'hash-a',
      signature: 'sig-a',
      canonical: '{}'
    });

    let entries = readLogEntries();
    assert.strictEqual(entries.length, 1, 'expected seal script to run once after first artifact');

    await ledgerClient.storeFreezeArtifact({
      name: 'authority_map.v1',
      hash: 'hash-a',
      signature: 'sig-a',
      canonical: '{}'
    });

    entries = readLogEntries();
    assert.strictEqual(entries.length, 1, 'expected seal script not to rerun when Merkle root unchanged');

    await ledgerClient.storeFreezeArtifact({
      name: 'capsule_remap.v1',
      hash: 'hash-b',
      signature: 'sig-b',
      canonical: '{}'
    });

    entries = readLogEntries();
    assert.strictEqual(entries.length, 2, 'expected seal script to run when Merkle root changes');

    console.log('PASS: ledger auto seal invoked on Merkle updates');
    process.exit(0);
  } catch (err) {
    console.error('FAIL: ledger auto seal regression', err);
    process.exit(1);
  }
})();
