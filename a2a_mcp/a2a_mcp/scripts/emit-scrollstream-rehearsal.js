#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const process = require('process');

const {
  CAPSULE_ID,
  DEFAULT_BASE_TIMESTAMP,
  DEFAULT_INTERVAL_SECONDS,
  emitRehearsalLedger,
  writeScrollstreamLedger
} = require('../utils/scrollstreamRehearsal');

function printUsage() {
  const scriptName = path.basename(process.argv[1] || 'emit-scrollstream-rehearsal');
  console.log(`Usage: ${scriptName} [--output <path>] [--base-timestamp <iso>] [--interval-seconds <number>] [--compact]`);
  console.log('');
  console.log('Stages the capsule.rehearsal.scrollstream.v1 cycle and writes deterministic ledger entries.');
}

function parseArgs(argv) {
  const options = {
    pretty: true
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    switch (arg) {
      case '--output':
        options.outputPath = argv[++index];
        break;
      case '--base-timestamp':
        options.baseTimestamp = argv[++index];
        break;
      case '--interval-seconds':
        options.intervalSeconds = Number(argv[++index]);
        break;
      case '--compact':
        options.pretty = false;
        break;
      case '--help':
      case '-h':
        options.help = true;
        break;
      default:
        throw new Error(`Unexpected argument: ${arg}`);
    }
  }

  return options;
}

function resolveOutputPath(outputPath) {
  if (!outputPath) {
    return path.resolve('public/data/scrollstream_ledger.json');
  }
  return path.resolve(outputPath);
}

function logEmissionSummary(outputPath, entries) {
  console.log(`✨ Emitted ${entries.length} rehearsal events for ${CAPSULE_ID}.`);
  console.log(`📜 Ledger path: ${outputPath}`);

  entries.forEach((entry) => {
    const stage = entry.stage.padEnd(16, ' ');
    const agent = `${entry.agent.name}/${entry.agent.callSign}`;
    console.log(`  • ${stage} :: ${agent} @ ${entry.timestamp}`);
    if (entry.visual.replayGlyphPulse) {
      console.log('    ↺ Replay glyph pulse armed.');
    }
  });
}

function main() {
  let options;
  try {
    options = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`❌ ${error.message}`);
    printUsage();
    process.exit(1);
  }

  if (options.help) {
    printUsage();
    process.exit(0);
  }

  const resolvedOutput = resolveOutputPath(options.outputPath);
  try {
    const entries = emitRehearsalLedger({
      outputPath: resolvedOutput,
      baseTimestamp: options.baseTimestamp || DEFAULT_BASE_TIMESTAMP,
      intervalSeconds: options.intervalSeconds !== undefined
        ? options.intervalSeconds
        : DEFAULT_INTERVAL_SECONDS,
      pretty: options.pretty
    });

    if (!fs.existsSync(resolvedOutput)) {
      writeScrollstreamLedger(resolvedOutput, entries, options);
    }

    logEmissionSummary(resolvedOutput, entries);
  } catch (error) {
    console.error(`❌ ${error.message}`);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}
