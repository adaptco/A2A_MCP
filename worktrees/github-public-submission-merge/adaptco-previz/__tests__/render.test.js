// adaptco-previz/__tests__/render.test.js
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const renderPreview = require('../src/render');

describe('renderPreview', () => {
  let tempDir;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'adaptco-previz-'));
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  it('creates a deterministic preview file', async () => {
    const descriptor = {
      id: 'asset-test',
      name: 'Test Asset',
      type: 'model',
      sourcePath: 'assets/test/model.glb',
      params: {}
    };

    const outputPath = await renderPreview(descriptor, tempDir);

    expect(outputPath).toMatch(/asset-test_preview\.png$/);
    expect(fs.existsSync(outputPath)).toBe(true);
    const contents = fs.readFileSync(outputPath, 'utf8');
    expect(contents).toContain('ADAPTCO PREVIZ PLACEHOLDER');
    expect(contents).toContain('id=asset-test');
  });

  it('throws when descriptor is missing an id', async () => {
    await expect(renderPreview({}, tempDir)).rejects.toThrow('Descriptor id is required');
  });
});
