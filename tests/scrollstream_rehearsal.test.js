'use strict';

const assert = require('assert');

const { createLedgerClient, REHEARSAL_CAPSULE_ID, DEFAULT_REHEARSAL_STAGES } = require('../server/ledger');
const { buildHudState, __dangerousResetHudCache } = require('../lib/bindings');

const manifestManager = {
  async getAuthorityMap() {
    return {
      hash: 'stub-hash',
      expectedHash: 'stub-hash',
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

(async () => {
  try {
    __dangerousResetHudCache();

    const fixedNow = '2024-03-11T12:00:00.000Z';
    const cycleId = 'cycle-test-scrollstream';
    const events = await ledgerClient.runRehearsalLoop({ now: fixedNow, cycleId, cadenceMs: 333 });

    assert.strictEqual(events.length, DEFAULT_REHEARSAL_STAGES.length, 'expected deterministic stage count');
    assert.deepStrictEqual(
      events.map((e) => e.stage),
      DEFAULT_REHEARSAL_STAGES.map((stage) => stage.stage),
      'stages should follow rehearsal manifest order'
    );
    assert.deepStrictEqual(
      events.map((e) => e.agent.name),
      ['Celine', 'Luma', 'Dot'],
      'expected agent sequence Celine -> Luma -> Dot'
    );

    const timestamps = events.map((e) => Date.parse(e.timestamp));
    for (let i = 1; i < timestamps.length; i += 1) {
      assert.ok(timestamps[i] > timestamps[i - 1], 'timestamps should increase monotonically');
    }

    const ledger = ledgerClient.getScrollstreamLedger();
    assert.strictEqual(ledger.length, events.length, 'ledger should retain emitted events');
    assert.ok(ledger.every((entry) => entry.capsule_id === REHEARSAL_CAPSULE_ID), 'ledger entries should reference rehearsal capsule');
    assert.strictEqual(ledger[0].cycle_id, cycleId, 'cycle id should propagate to ledger entries');

    const proof = await ledgerClient.getLatestProof();
    assert.strictEqual(proof.scrollstream.shimmer, 'engaged', 'shimmer should be engaged after loop');
    assert.strictEqual(proof.scrollstream.events.length, events.length, 'proof should include recent scrollstream events');

    __dangerousResetHudCache();
    const hudState = await buildHudState(ledgerClient, { force: true });
    assert.strictEqual(hudState.scrollstream.shimmer, 'engaged', 'HUD shimmer should register emission');
    assert.strictEqual(hudState.scrollstream.last_cycle_id, cycleId, 'HUD should expose last cycle id');

    console.log('PASS: scrollstream rehearsal loop emits deterministic cycle');
    process.exit(0);
  } catch (err) {
    console.error('FAIL: scrollstream rehearsal loop', err);
    process.exit(1);
  }
})();
