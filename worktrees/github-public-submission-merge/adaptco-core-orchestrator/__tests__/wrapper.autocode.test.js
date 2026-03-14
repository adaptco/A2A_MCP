// adaptco-core-orchestrator/__tests__/wrapper.autocode.test.js
'use strict';

const path = require('path');
const {
  loadWrapperCapsule,
  loadRuntimeRegistry,
  createAnchorBindings,
  inspectWrapperEnvironment
} = require('../src/wrapper');

const repoRoot = path.resolve(__dirname, '..', '..');
const wrapperPath = path.join(repoRoot, 'capsules', 'doctrine', 'capsule.wrapper.adaptco_os.v1.json');
const registryPath = path.join(repoRoot, 'runtime', 'capsule.registry.runtime.v1.json');
const runtimeDir = path.join(repoRoot, 'runtime');

describe('wrapper autocode binder', () => {
  it('loads the wrapper capsule and honors Queen CiCi as stabilizer', async () => {
    const capsule = await loadWrapperCapsule({ wrapperPath });
    expect(capsule.capsule_id).toBe('capsule.wrapper.adaptco_os.v1');
    expect(capsule.governance.stabilizer).toBe('Queen CiCi');
    expect(Array.isArray(capsule.lineage.anchors)).toBe(true);
  });

  it('binds wrapper anchors against the runtime registry', async () => {
    const registry = await loadRuntimeRegistry({ registryPath });
    const capsule = await loadWrapperCapsule({ wrapperPath });
    const bindings = createAnchorBindings(capsule, registry);

    const anchorIds = bindings.map((binding) => binding.capsule_id);
    expect(anchorIds).toEqual(
      expect.arrayContaining(['ssot.registry.v1', 'qube.orchestrator.v1', 'sol.f1.previz.v1', 'relay.artifacts.v1'])
    );
    expect(bindings.every((binding) => binding.binding === 'bound')).toBe(true);
    const rehearsalAnchor = bindings.find((binding) => binding.capsule_id === 'sol.f1.previz.v1');
    expect(rehearsalAnchor.sticky).toBe(false);
  });

  it('produces a sticky vessel report with ledger presence', async () => {
    const report = await inspectWrapperEnvironment({ wrapperPath, registryPath, runtimeDir });

    expect(report.wrapper).toMatchObject({
      capsule_id: 'capsule.wrapper.adaptco_os.v1',
      version: '1.0.0'
    });
    expect(report.governance.stabilizer).toBe('Queen CiCi');
    expect(report.sticky.bound).toBeGreaterThanOrEqual(4);
    expect(report.sticky.sticky).toBe(3);
    expect(report.runtime.ledger.exists).toBe(true);
    expect(Array.isArray(report.runtime.hud)).toBe(true);
  });
});
