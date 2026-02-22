// adaptco-previz/src/render.js
'use strict';

const fs = require('fs');
const path = require('path');

async function renderPreview(descriptor, outDir) {
  if (!descriptor || !descriptor.id) {
    throw new Error('Descriptor id is required');
  }

  const outputDirectory = path.resolve(outDir);
  await fs.promises.mkdir(outputDirectory, { recursive: true });
  const filename = `${descriptor.id}_preview.png`;
  const outputPath = path.join(outputDirectory, filename);
  const stub = [
    'ADAPTCO PREVIZ PLACEHOLDER',
    `id=${descriptor.id}`,
    `name=${descriptor.name || 'unknown'}`,
    `type=${descriptor.type || 'unknown'}`,
    `source=${descriptor.sourcePath || 'n/a'}`,
    `generated_at=${new Date().toISOString()}`
  ].join('\n');

  await fs.promises.writeFile(outputPath, stub, 'utf8');
  return outputPath;
}

module.exports = renderPreview;
