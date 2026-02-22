#!/usr/bin/env node
// adaptco-previz/src/cli.js
'use strict';

const fs = require('fs');
const path = require('path');
const { Command } = require('commander');
const renderPreview = require('./render');
const { validateDescriptor } = require('./validator');

const program = new Command();

program
  .name('adaptco-previz')
  .description('Generate deterministic preview stubs for Adaptco assets')
  .version('0.1.0');

program
  .command('render <descriptor>')
  .option('--out <directory>', 'Output directory for previews', 'previews')
  .description('Render a preview for the provided descriptor file')
  .action(async (descriptor, options) => {
    try {
      const descriptorPath = path.resolve(descriptor);
      const raw = await fs.promises.readFile(descriptorPath, 'utf8');
      const parsed = JSON.parse(raw);
      validateDescriptor(parsed);
      const outputDir = path.resolve(options.out || 'previews');
      const outputPath = await renderPreview(parsed, outputDir);
      console.log(outputPath);
    } catch (error) {
      console.error(`[adaptco-previz] ${error.message}`);
      process.exitCode = 1;
    }
  });

program.parseAsync(process.argv);
