#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const minimist = require('minimist');
const { buildVerificationReceipt } = require('./verify');

function loadJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function main() {
  const argv = minimist(process.argv.slice(2));
  const batchPath = argv.batch || argv.b;
  const expectPath = argv.expect || argv.e;

  if (!batchPath) {
    console.error('Usage: collapse-verify --batch <batch.json> [--expect <expected_receipt.json>]');
    process.exit(2);
  }

  const batch = loadJson(path.resolve(batchPath));
  const receipt = buildVerificationReceipt(batch);

  const out = JSON.stringify(receipt, null, 2);
  console.log(out);

  if (expectPath) {
    const expected = loadJson(path.resolve(expectPath));
    const match = JSON.stringify(expected) === JSON.stringify(receipt);
    console.log(`\n== EXPECTED MATCH: ${match ? 'PASS' : 'FAIL'}`);
    process.exit(match ? 0 : 3);
  }
}

if (require.main === module) main();
