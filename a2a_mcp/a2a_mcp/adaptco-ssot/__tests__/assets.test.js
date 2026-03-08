// adaptco-ssot/__tests__/assets.test.js
'use strict';

const fs = require('fs');
const request = require('supertest');
const app = require('../src/index');
const store = require('../src/store');

const originalCatalog = fs.readFileSync(store.catalogPath, 'utf8');

function buildRegistryPacket({
  artifactId,
  type,
  author,
  parent = null,
  forks = []
}) {
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
      canonical_sha256: 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      merkle_root: 'merkle:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
      council_attestation: {
        signatures: ['sig:queen_boo', 'sig:cici'],
        quorum_rule: '2-of-3'
      }
    },
    lineage: {
      parent,
      forks,
      immutable: true
    },
    replay: {
      authorized: true,
      conditions: ['capsule.integrity == valid', 'council.attestation == quorum'],
      override_protocol: 'maker_checker'
    }
  };
}

describe('Assets API', () => {
  beforeEach(() => {
    fs.writeFileSync(store.catalogPath, originalCatalog);
    store.reload();
  });

  afterAll(() => {
    fs.writeFileSync(store.catalogPath, originalCatalog);
    store.reload();
  });

  it('returns the asset catalog', async () => {
    const response = await request(app).get('/assets');
    expect(response.status).toBe(200);
    expect(Array.isArray(response.body)).toBe(true);
    expect(response.body.length).toBeGreaterThan(0);
  });

  it('does not leak internal catalog references', async () => {
    const response = await request(app).get('/assets');
    expect(response.status).toBe(200);
    const asset = response.body[0];
    expect(asset).toBeDefined();

    asset.tags.push('mutated-from-test');
    asset.meta.injected = true;

    const freshCatalog = store.getAll();
    const original = freshCatalog.find((entry) => entry.id === asset.id);

    expect(original.tags).not.toContain('mutated-from-test');
    expect(original.meta.injected).toBeUndefined();
  });

  it('rejects invalid payloads on POST', async () => {
    const response = await request(app)
      .post('/assets')
      .send({ id: 'asset-x' })
      .set('Accept', 'application/json');

    expect(response.status).toBe(400);
    expect(response.body.status).toBe('error');
  });

  it('creates a valid asset', async () => {
    const payload = {
      id: 'asset-999',
      name: 'Integration Fixture',
      kind: 'image',
      uri: 'https://cdn.adaptco.io/assets/integration.png',
      tags: ['test'],
      meta: { owner: 'qa@adaptco.io' },
      registry: buildRegistryPacket({ artifactId: 'asset-999', type: 'image', author: 'qa@adaptco.io' })
    };

    const response = await request(app)
      .post('/assets')
      .send(payload)
      .set('Accept', 'application/json');

    expect(response.status).toBe(201);
    expect(response.body.status).toBe('created');
    expect(response.body.asset).toMatchObject(payload);

    const catalog = store.getAll();
    expect(catalog.some((asset) => asset.id === 'asset-999')).toBe(true);
  });

  it('rejects updates that would introduce duplicate asset ids', async () => {
    const payload = {
      id: 'asset-002',
      name: 'Conflicting Asset',
      kind: 'image',
      uri: 'https://cdn.adaptco.io/assets/conflict.png',
      tags: ['conflict'],
      meta: { owner: 'qa@adaptco.io' }
    };

    const response = await request(app)
      .put('/assets/asset-001')
      .send(payload)
      .set('Accept', 'application/json');

    expect(response.status).toBe(409);
    expect(response.body).toEqual({
      status: 'error',
      message: 'Asset with id asset-002 already exists'
    });

    const catalog = store.getAll();
    const duplicates = catalog.filter((asset) => asset.id === 'asset-002');
    expect(duplicates).toHaveLength(1);
  });
});
