#!/usr/bin/env node
// adaptco-core-orchestrator/src/bin/rehearsal.js
'use strict';

const path = require('path');
const { emitScrollstreamRehearsal, CAPSULE_ID } = require('../rehearsal');
const { createScrollstreamWriter } = require('../scrollstream-ledger');

function printUsage(stream = process.stdout) {
  stream.write(
    [
      'Usage: rehearsal [options]',
      '',
      'Options:',
      '  --ledger <path>        Override scrollstream ledger output path',
      '  --format <json|text>   Output format (default: json)',
      '  --help                 Show this help message'
    ].join('\n') + '\n'
  );
}

function parseArgs(argv) {
  const options = {
    format: 'json'
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    switch (arg) {
      case '--ledger':
        if (index + 1 >= argv.length) {
          throw new Error('--ledger requires a value');
        }
        options.ledger = argv[++index];
        break;
      case '--format':
        if (index + 1 >= argv.length) {
          throw new Error('--format requires a value');
        }
        options.format = argv[++index];
        break;
      case '--help':
      case '-h':
        options.help = true;
        break;
      default:
        if (arg.startsWith('-')) {
          throw new Error(`Unknown argument: ${arg}`);
        }
        break;
    }
  }

  return options;
}

function formatAsText(result) {
  const lines = [];
  lines.push(`Capsule: ${result.capsule_id}`);
  lines.push(`Cycle: ${result.cycle}`);
  lines.push(`Total Events: ${result.total_events}`);
  lines.push(`HUD Status: ${result.hud_status}`);
  lines.push('');
  lines.push('Sequence:');

  for (const event of result.events) {
    const agentSummary = `${event.agent.name} (${event.agent.role})`;
    lines.push(`- [${event.ts}] ${event.event} — ${agentSummary}`);
    if (event.output?.payload?.emotion) {
      lines.push(
        `  Emotion: ${event.output.payload.emotion} (resonance ${event.output.payload.resonance})`
      );
    }
    if (event.output?.hud?.shimmer) {
      lines.push(`  HUD shimmer: ${event.output.hud.shimmer}`);
    }
    if (event.output?.replay?.glyph) {
      lines.push(`  Replay glyph: ${event.output.replay.glyph}`);
    }
  }

  return lines.join('\n');
}

async function main() {
  try {
    const options = parseArgs(process.argv.slice(2));

    if (options.help) {
      printUsage();
      return;
    }

    let appendEvent;
    if (options.ledger) {
      const ledgerPath = path.resolve(process.cwd(), options.ledger);
      appendEvent = createScrollstreamWriter(ledgerPath);
    }

    const result = await emitScrollstreamRehearsal({ appendEvent });

    if (options.format === 'text') {
      process.stdout.write(`${formatAsText(result)}\n`);
      return;
    }

    if (options.format && options.format !== 'json') {
      throw new Error(`Unsupported format: ${options.format}`);
    }

    process.stdout.write(`${JSON.stringify(result)}\n`);
  } catch (error) {
    if (error.message) {
      process.stderr.write(`${error.message}\n`);
    } else {
      process.stderr.write('An unexpected error occurred.\n');
    }
    process.exitCode = 1;
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  CAPSULE_ID,
  parseArgs,
  printUsage,
  formatAsText
};
