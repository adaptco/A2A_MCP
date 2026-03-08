'use strict';

const hydrateNonCodexOperations = require('../src/non_codex_hydrator');

describe('hydrateNonCodexOperations', () => {
  it('returns empty object when operations are missing', () => {
    expect(hydrateNonCodexOperations(undefined)).toEqual({});
    expect(hydrateNonCodexOperations(null)).toEqual({});
  });

  it('hydrates preview descriptors lacking params', () => {
    const operations = {
      preview: {
        descriptor: {
          id: 'asset-1',
          name: 'Legacy Asset',
          type: 'image',
          sourcePath: 'assets/legacy.glb'
        }
      }
    };

    const result = hydrateNonCodexOperations(operations);
    expect(result.preview.descriptor).toEqual({
      id: 'asset-1',
      name: 'Legacy Asset',
      type: 'image',
      sourcePath: 'assets/legacy.glb',
      params: {}
    });

    // ensure original object is not mutated
    expect(operations.preview.descriptor.params).toBeUndefined();
  });

  it('ensures asset payloads include tags and meta objects', () => {
    const operations = {
      asset: {
        payload: {
          id: 'asset-2',
          name: 'Legacy Asset',
          kind: 'image',
          uri: 'https://cdn.example.com/legacy.png'
        }
      }
    };

    const result = hydrateNonCodexOperations(operations);
    expect(result.asset.payload.tags).toEqual([]);
    expect(result.asset.payload.meta).toEqual({});
  });

  it('coerces hash inputs into an array of strings', () => {
    const operations = {
      hash: {
        inputs: '/tmp/snapshot.bin'
      }
    };

    const result = hydrateNonCodexOperations(operations);
    expect(result.hash.inputs).toEqual(['/tmp/snapshot.bin']);

    const multi = hydrateNonCodexOperations({
      hash: { inputs: ['/tmp/ok.bin', 42, '', null, '/tmp/also-ok.bin'] }
    });
    expect(multi.hash.inputs).toEqual(['/tmp/ok.bin', '/tmp/also-ok.bin']);
  });
});

