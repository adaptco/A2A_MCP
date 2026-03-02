#!/usr/bin/env node

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function usage() {
  const script = path.basename(process.argv[1] || 'generate-fossil-receipts');
  console.log(`Usage: ${script} --input <payloads.ndjson> --output <receipts.ndjson>`);
}

function parseArgs(argv) {
  const args = { input: null, output: null };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--input') {
      args.input = argv[i + 1];
      i += 1;
    } else if (arg === '--output') {
      args.output = argv[i + 1];
      i += 1;
    } else if (arg === '--help' || arg === '-h') {
      usage();
      process.exit(0);
    }
  }
  return args;
}

function sortKeys(value) {
  if (Array.isArray(value)) {
    return value.map(sortKeys);
  }
  if (value && typeof value === 'object') {
    return Object.keys(value)
      .sort()
      .reduce((acc, key) => {
        acc[key] = sortKeys(value[key]);
        return acc;
      }, {});
  }
  return value;
}

function canonicalize(value) {
  return JSON.stringify(sortKeys(value));
}

function readJsonLines(filePath) {
  const data = fs.readFileSync(filePath, 'utf8');
  return data
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, idx) => {
      try {
        return JSON.parse(line);
      } catch (error) {
        throw new Error(`Invalid JSON on line ${idx + 1}: ${error.message}`);
      }
    });
}

function writeJsonLines(filePath, records) {
  const payload = records.map((record) => JSON.stringify(record)).join('\n') + '\n';
  fs.writeFileSync(filePath, payload, 'utf8');
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input || !args.output) {
    usage();
    process.exit(1);
  }

  const records = readJsonLines(args.input);
  const receipts = records.map((record, idx) => {
    const payload = record.payload || record;

    // GUARD: Ensure the identity surface is defined before fossilization.
    if (!payload.run_id || !payload.vehicle_id) {
      throw new Error('Identity Breach: Attempted to anchor frame with empty Identity Metadata.');
    }

    const digest = crypto.createHash('sha256').update(canonicalize(payload)).digest('hex');

    return {
      run_id: payload.run_id,
      vehicle_id: payload.vehicle_id,
      sequence_id: payload.sequence_id ?? idx + 1,
      created_at: new Date().toISOString(),
      sha256_payload: `sha256:${digest}`,
      payload,
    };
  });

  writeJsonLines(args.output, receipts);
  console.log(`Generated ${receipts.length} fossil receipts → ${args.output}`);
}

if (require.main === module) {
  main();
}
