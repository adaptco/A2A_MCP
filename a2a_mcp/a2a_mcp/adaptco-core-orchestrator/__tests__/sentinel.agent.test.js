// adaptco-core-orchestrator/__tests__/sentinel.agent.test.js
"use strict";

const path = require('path');
const os = require('os');
const { promises: fsp } = require('fs');
const SentinelAgent = require('../src/sentinel');

function createFetchStub(response = {}) {
  return async () => ({
    ok: true,
    status: 200,
    text: async () => '',
    ...response
  });
}

function createRegistryPacket(overrides = {}) {
  const {
    artifactId = 'asset-999',
    type = 'image',
    author = 'qa@adaptco.io',
    canonical = 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    merkle = 'merkle:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
  } = overrides;

  return {
    capsule_id: 'ssot.registry.v1',
    registry: {
      name: 'Qube Sovereign Archive',
      version: '1.0.0',
      maintainer: 'Q.Enterprise Council'
    },
    entry: {
      artifact_id: artifactId,
      type,
      author,
      created_at: '2024-09-04T12:00:00Z',
      canonical_sha256: canonical,
      merkle_root: merkle,
      council_attestation: {
        signatures: ['sig:queen_boo', 'sig:cici'],
        quorum_rule: '2-of-3'
      }
    },
    lineage: {
      parent: null,
      forks: [],
      immutable: true
    },
    replay: {
      authorized: true,
      conditions: ['capsule.integrity == valid', 'council.attestation == quorum'],
      override_protocol: 'maker_checker'
    }
  };
}

describe('SentinelAgent', () => {
  const noopFetch = createFetchStub();

  it('invokes PreViz CLI with expected arguments', async () => {
    const captured = [];
    const sentinel = new SentinelAgent({
      nodePath: '/usr/local/bin/node',
      previzCli: '/workspace/adaptco-previz/src/cli.js',
      runCommand: async (command) => {
        captured.push(command);
        return { stdout: '/tmp/previews/asset.png\n', stderr: '', exitCode: 0 };
      },
      fetch: noopFetch
    });

    const descriptorPath = '/tmp/descriptor.json';
    const outDir = '/tmp/previews';

    const result = await sentinel.renderPreview(descriptorPath, { outDir });

    expect(captured).toHaveLength(1);
    expect(captured[0]).toEqual([
      '/usr/local/bin/node',
      '/workspace/adaptco-previz/src/cli.js',
      'render',
      path.resolve(descriptorPath),
      '--out',
      path.resolve(outDir)
    ]);
    expect(result.stdout).toBe('/tmp/previews/asset.png');
    expect(result.stderr).toBe('');
  });

  it('uses the configured default preview directory when none is provided', async () => {
    let command;
    const sentinel = new SentinelAgent({
      nodePath: '/usr/bin/node',
      previzCli: '/srv/cli.js',
      previzOutDir: '/var/previews',
      runCommand: async (args) => {
        command = args;
        return { stdout: '', stderr: '', exitCode: 0 };
      },
      fetch: noopFetch
    });

    await sentinel.renderPreview('/tmp/descriptor.json');

    expect(command[5]).toBe(path.resolve('/var/previews'));
  });

  it('validates descriptor payloads before dispatching', async () => {
    const descriptorWriter = jest.fn(async () => '/tmp/generated.json');
    const sentinel = new SentinelAgent({
      runCommand: async () => ({ stdout: '', stderr: '', exitCode: 0 }),
      descriptorWriter,
      fetch: noopFetch
    });

    const descriptor = {
      id: 'asset-123',
      name: 'Sample Asset',
      type: 'image',
      sourcePath: 'assets/sample.gltf',
      params: {}
    };

    await sentinel.renderPreview(descriptor);

    expect(descriptorWriter).toHaveBeenCalledTimes(1);
    expect(descriptorWriter).toHaveBeenCalledWith(descriptor, undefined);

    await expect(sentinel.renderPreview({ id: 'missing-fields' })).rejects.toThrow(
      'Descriptor missing required fields: name, type, sourcePath, params'
    );

    await expect(
      sentinel.renderPreview({
        id: 'bad-params',
        name: 'Invalid Params',
        type: 'image',
        sourcePath: 'assets/sample.gltf',
        params: []
      })
    ).rejects.toThrow('Descriptor missing required fields: params');
  });

  it('writes descriptor payloads to explicit nested paths', async () => {
    const tmpRoot = await fsp.mkdtemp(path.join(os.tmpdir(), 'sentinel-explicit-'));
    const explicitPath = path.join(tmpRoot, 'nested', 'descriptors', 'custom.json');
    const sentinel = new SentinelAgent({
      runCommand: async () => ({ stdout: '', stderr: '', exitCode: 0 }),
      fetch: noopFetch
    });

    const descriptor = {
      id: 'asset-321',
      name: 'Nested Descriptor',
      type: 'image',
      sourcePath: 'assets/nested.gltf'
    };

    try {
      const result = await sentinel.renderPreview(descriptor, {
        descriptorPath: explicitPath,
        persistDescriptor: true
      });

      expect(result.stdout).toBe('');
      const stored = await fsp.readFile(explicitPath, 'utf8');
      expect(JSON.parse(stored)).toEqual(descriptor);
    } finally {
      await fsp.rm(tmpRoot, { recursive: true, force: true });
    }
  });

  it('surfaces non-zero exit codes from the PreViz command', async () => {
    const sentinel = new SentinelAgent({
      runCommand: async () => ({ stdout: '', stderr: 'boom', exitCode: 2 }),
      fetch: noopFetch
    });

    await expect(sentinel.renderPreview('/tmp/descriptor.json')).rejects.toThrow(
      'PreViz command failed with exit code 2'
    );
  });

  it('sends asset payloads to the SSoT service', async () => {
    let captured;
    const fetchStub = async (url, init) => {
      captured = { url: url.toString(), init };
      return {
        ok: true,
        status: 201,
        text: async () => JSON.stringify({ status: 'created' })
      };
    };

    const sentinel = new SentinelAgent({
      ssotBaseUrl: 'https://ssot.adaptco',
      runCommand: async () => ({ stdout: '', stderr: '', exitCode: 0 }),
      fetch: fetchStub
    });

    const asset = {
      id: 'asset-999',
      name: 'Integration Fixture',
      kind: 'image',
      uri: 'https://cdn.adaptco.io/assets/integration.png',
      tags: ['test'],
      meta: { owner: 'qa@adaptco.io' },
      registry: createRegistryPacket({ artifactId: 'asset-999', type: 'image' })
    };

    const response = await sentinel.registerAsset(asset);

    expect(captured.url).toBe('https://ssot.adaptco/assets');
    expect(captured.init.method).toBe('POST');
    expect(captured.init.headers['Content-Type']).toBe('application/json');
    expect(captured.init.body).toBe(JSON.stringify(asset));
    expect(response).toEqual({ status: 201, body: { status: 'created' } });
  });

  it('validates asset payloads', async () => {
    const sentinel = new SentinelAgent({
      runCommand: async () => ({ stdout: '', stderr: '', exitCode: 0 }),
      fetch: noopFetch
    });

    await expect(sentinel.registerAsset({ id: 'asset-1' })).rejects.toThrow(
      'Asset payload missing or invalid fields: name, kind, uri, tags, meta, registry'
    );
  });

  it('raises on non-OK responses from the SSoT service', async () => {
    const fetchStub = async () => ({
      ok: false,
      status: 409,
      text: async () => JSON.stringify({ status: 'error', message: 'duplicate' })
    });

    const sentinel = new SentinelAgent({
      runCommand: async () => ({ stdout: '', stderr: '', exitCode: 0 }),
      fetch: fetchStub
    });

    const asset = {
      id: 'asset-100',
      name: 'Duplicate',
      kind: 'image',
      uri: 'https://cdn.adaptco.io/assets/duplicate.png',
      tags: ['test'],
      meta: { owner: 'qa@adaptco.io' },
      registry: createRegistryPacket({ artifactId: 'asset-100', type: 'image' })
    };

    await expect(sentinel.registerAsset(asset)).rejects.toMatchObject({
      message: 'SSOT request failed with status 409',
      status: 409,
      body: { status: 'error', message: 'duplicate' }
    });
  });
});
