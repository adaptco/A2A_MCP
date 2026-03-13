#!/usr/bin/env node
// adaptco-core-orchestrator/src/bin/audit.js
'use strict';

const path = require('path');
const { readLedger, buildTrace } = require('../audit');

function printUsage(stream = process.stdout) {
  stream.write(
    ['Usage: audit [options]',
      '',
      'Options:',
      '  --id <artifact-id>            Full artifact identifier (e.g. capsule-caps-123-1.0.0)',
      '  --capsule-id <capsule-id>     Capsule identifier (e.g. caps-123)',
      '  --version <version>           Capsule version when used with --capsule-id',
      '  --ledger <path>               Override ledger file location',
      '  --format <json|text>          Output format (default: json)',
      '  --pretty                      Pretty-print JSON output',
      '  --help                        Show this help message'
    ].join('\n') + '\n'
  );
}

function parseArgs(argv) {
  const options = {
    format: 'json',
    pretty: false
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    switch (arg) {
      case '--id':
      case '-i':
        if (index + 1 >= argv.length) {
          throw new Error('--id requires a value');
        }
        options.id = argv[++index];
        break;
      case '--capsule-id':
      case '-c':
        if (index + 1 >= argv.length) {
          throw new Error('--capsule-id requires a value');
        }
        options.capsuleId = argv[++index];
        break;
      case '--version':
      case '-v':
        if (index + 1 >= argv.length) {
          throw new Error('--version requires a value');
        }
        options.version = argv[++index];
        break;
      case '--ledger':
        if (index + 1 >= argv.length) {
          throw new Error('--ledger requires a value');
        }
        options.ledger = argv[++index];
        break;
      case '--format':
      case '-f':
        if (index + 1 >= argv.length) {
          throw new Error('--format requires a value');
        }
        options.format = argv[++index];
        break;
      case '--pretty':
        options.pretty = true;
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

function ensureIdentifier(options) {
  if (!options.id && !options.capsuleId) {
    throw new Error('Please supply --id or --capsule-id to trace an artifact.');
  }
}

function formatTraceAsText(trace) {
  const lines = [];
  lines.push(`Artifact: ${trace.artifactId}`);
  const criteriaParts = [];
  if (trace.criteria?.capsuleId) {
    criteriaParts.push(`capsule=${trace.criteria.capsuleId}`);
  }
  if (trace.criteria?.version) {
    criteriaParts.push(`version=${trace.criteria.version}`);
  }
  if (trace.criteria?.id) {
    criteriaParts.push(`id=${trace.criteria.id}`);
  }
  if (criteriaParts.length) {
    lines.push(`Criteria: ${criteriaParts.join(', ')}`);
  }
  lines.push(`Total Events: ${trace.totalEvents}`);
  lines.push(`First Seen: ${trace.firstSeen}`);
  lines.push(`Last Seen: ${trace.lastSeen}`);

  if (trace.capsule) {
    const capsule = trace.capsule;
    const capsuleSummary = [capsule.capsule_id, capsule.version]
      .filter(Boolean)
      .join(' v');
    if (capsuleSummary) {
      lines.push(`Capsule: ${capsuleSummary}`);
    }
    if (capsule.author) {
      lines.push(`Author: ${capsule.author}`);
    }
  }

  lines.push('');
  lines.push('Events:');
  for (const event of trace.events) {
    lines.push(`- [${event.at}] ${event.type} — ${event.summary}`);
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

    ensureIdentifier(options);

    const ledgerPath = options.ledger
      ? path.resolve(process.cwd(), options.ledger)
      : undefined;

    const entries = await readLedger(ledgerPath);
    const trace = buildTrace(entries, {
      id: options.id,
      capsuleId: options.capsuleId,
      version: options.version
    });

    if (!trace) {
      process.stderr.write('No ledger events found for the requested artifact.\n');
      process.exitCode = 1;
      return;
    }

    if (options.format === 'text') {
      process.stdout.write(`${formatTraceAsText(trace)}\n`);
      return;
    }

    if (options.format && options.format !== 'json') {
      throw new Error(`Unsupported format: ${options.format}`);
    }

    const spacing = options.pretty ? 2 : 0;
    process.stdout.write(`${JSON.stringify(trace, null, spacing)}\n`);
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
  parseArgs,
  ensureIdentifier,
  formatTraceAsText,
  printUsage
};
