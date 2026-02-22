'use strict';

const fs = require('fs');
const path = require('path');
const { createHash, createPrivateKey, sign: signPayload } = require('crypto');
const qbusGateGuard = require('../lib/qbusGates');
const { canonicalizeManifest, manifestSignaturePayload, verifyDuoSig } = require('../lib/bindings');

function loadManifestFixture() {
  const manifestPath = path.join(__dirname, '..', 'governance', 'authority_map.v1.json');
  const raw = fs.readFileSync(manifestPath, 'utf8');
  return JSON.parse(raw);
}

const makerPrivateKey = createPrivateKey(
  fs.readFileSync(path.join(__dirname, 'fixtures', 'keys', 'maker_ed25519.pem'))
);
const checkerPrivateKey = createPrivateKey(
  fs.readFileSync(path.join(__dirname, 'fixtures', 'keys', 'checker_ed25519.pem'))
);

function resignManifest(manifest, updates = {}) {
  const updated = JSON.parse(JSON.stringify(manifest));
  Object.assign(updated, updates);
  const payload = manifestSignaturePayload(updated);
  const payloadBuffer = Buffer.from(payload, 'utf8');
  const makerSig = signPayload(null, payloadBuffer, makerPrivateKey).toString('base64');
  const checkerSig = signPayload(null, payloadBuffer, checkerPrivateKey).toString('base64');
  updated.signatures = {
    maker: makerSig,
    checker: checkerSig
  };
  return updated;
}

function createManifestInfo(manifestOverrides) {
  const manifest = manifestOverrides || loadManifestFixture();
  const canonical = canonicalizeManifest(manifest);
  const hash = createHash('sha256').update(canonical).digest('hex');
  const duo = verifyDuoSig(
    manifestSignaturePayload(manifest),
    manifest.signatures && manifest.signatures.maker,
    manifest.signatures && manifest.signatures.checker,
    {
      maker: manifest.maker && manifest.maker.public_key,
      checker: manifest.checker && manifest.checker.public_key
    }
  );
  return {
    manifest,
    hash,
    hashMatches: true,
    hasHashFile: true,
    hasSignatureFile: true,
    duo,
    source: 'fixture',
    loadedAt: new Date().toISOString()
  };
}

function createMockRes() {
  return {
    statusCode: 200,
    sent: false,
    body: null,
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.body = payload;
      this.sent = true;
      return this;
    }
  };
}

async function invokeMiddleware(middleware, req) {
  const res = createMockRes();
  let nextCalled = false;
  const next = () => {
    nextCalled = true;
  };
  await middleware(req, res, next);
  return { res, nextCalled, req };
}

async function runTest(name, fn) {
  try {
    await fn();
    console.log(`PASS: ${name}`);
    return true;
  } catch (err) {
    console.log(`FAIL: ${name} -> ${err.message}`);
    return false;
  }
}

(async () => {
  const results = [];
  const baseInfo = createManifestInfo();

  results.push(await runTest('G1 allows authorized binding (also G2 positive)', async () => {
    const provider = async () => ({ ...baseInfo });
    const ledgerEvents = [];
    const ledgerClient = {
      async recordGateCheck(event) {
        ledgerEvents.push(event);
      }
    };
    const middleware = qbusGateGuard(provider, ledgerClient, { skew_seconds: 0 });
    const req = {
      body: {
        avatar: 'Celine',
        vessel: ' AURORA ',
        capsule: 'LUMA',
        gate: 'thrust_control'
      }
    };
    const { res, nextCalled } = await invokeMiddleware(middleware, req);
    if (res.sent) {
      throw new Error(`Unexpected response ${res.statusCode}`);
    }
    if (!nextCalled) {
      throw new Error('Next was not called for authorized binding');
    }
    if (!req.qbus || !req.qbus.binding || !req.qbus.binding.ok) {
      throw new Error('Binding context missing on request');
    }
    if (!ledgerEvents.length) {
      throw new Error('Ledger client did not record gate check');
    }
  }));

  results.push(await runTest('G1 rejects unknown binding', async () => {
    const provider = async () => ({ ...baseInfo });
    const middleware = qbusGateGuard(provider, null, { skew_seconds: 0 });
    const req = {
      body: {
        avatar: 'Spryte',
        vessel: 'Halcyon',
        capsule: 'dot',
        gate: 'MISSION_PLANNER'
      }
    };
    const { res } = await invokeMiddleware(middleware, req);
    if (!res.sent) {
      throw new Error('Response not sent on scope violation');
    }
    if (res.statusCode !== 403) {
      throw new Error(`Expected 403, received ${res.statusCode}`);
    }
    if (!res.body || res.body.error_code !== 'G1_SCOPE_VIOLATION') {
      throw new Error('Incorrect error code for G1 rejection');
    }
  }));

  results.push(await runTest('G2 rejects manifest with mismatched signatures', async () => {
    const badManifest = loadManifestFixture();
    badManifest.signatures = {
      maker: 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
      checker: badManifest.signatures.checker
    };
    const info = createManifestInfo(badManifest);
    const provider = async () => info;
    const middleware = qbusGateGuard(provider, null, { skew_seconds: 0 });
    const req = {
      body: {
        avatar: 'Celine',
        vessel: 'Aurora',
        capsule: 'luma',
        gate: 'THRUST_CONTROL'
      }
    };
    const { res } = await invokeMiddleware(middleware, req);
    if (!res.sent) {
      throw new Error('Response not sent for G2 failure');
    }
    if (res.statusCode !== 403) {
      throw new Error(`Expected 403, received ${res.statusCode}`);
    }
    if (!res.body || res.body.error_code !== 'G2_DUO_SIG_MISMATCH') {
      throw new Error('Incorrect error code for G2 failure');
    }
  }));

  results.push(await runTest('G3 blocks manifest that is not yet effective', async () => {
    const futureManifest = resignManifest(loadManifestFixture(), {
      effective_after: new Date(Date.now() + 60 * 60 * 1000).toISOString()
    });
    const info = createManifestInfo(futureManifest);
    const provider = async () => info;
    const middleware = qbusGateGuard(provider, null, { skew_seconds: 10 });
    const req = {
      body: {
        avatar: 'Celine',
        vessel: 'Aurora',
        capsule: 'luma',
        gate: 'THRUST_CONTROL'
      }
    };
    const { res } = await invokeMiddleware(middleware, req);
    if (!res.sent) {
      throw new Error('Response not sent for G3 violation');
    }
    if (res.statusCode !== 503) {
      throw new Error(`Expected 503, received ${res.statusCode}`);
    }
    if (!res.body || res.body.error_code !== 'G3_AUTH_MAP_NOT_YET_EFFECTIVE') {
      throw new Error('Incorrect error code for G3 violation');
    }
  }));

  const failed = results.filter((r) => !r);
  if (failed.length) {
    process.exit(1);
  }
})();
