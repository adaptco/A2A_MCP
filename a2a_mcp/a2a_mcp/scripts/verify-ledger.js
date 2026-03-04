#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const process = require('process');

const {
  verifyLedgerFile
} = require('../utils/ledgerVerifier');

function printUsage() {
  const scriptName = path.basename(process.argv[1] || 'verify-ledger');
  console.log(`Usage: ${scriptName} --ledger <ledger.json> --pub-key <public.pem>`);
  console.log('');
  console.log('Verifies that each ledger entry hash, chain linkage, and signature are valid.');
}

function parseArgs(argv) {
  const options = {
    ledger: null,
    pubKey: null
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    switch (arg) {
      case '--ledger':
        options.ledger = argv[++i];
        break;
      case '--pub-key':
        options.pubKey = argv[++i];
        break;
      case '--help':
      case '-h':
        options.help = true;
        break;
      default:
        if (!options.ledger) {
          options.ledger = arg;
        } else if (!options.pubKey) {
          options.pubKey = arg;
        } else {
          throw new Error(`Unexpected argument: ${arg}`);
        }
        break;
    }
  }

  return options;
}

function ensureFileExists(filePath, description) {
  if (!filePath) {
    throw new Error(`Missing ${description} path`);
  }
  if (!fs.existsSync(filePath)) {
    throw new Error(`${description} not found: ${filePath}`);
  }
  return path.resolve(filePath);
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

  try {
    const ledgerPath = ensureFileExists(options.ledger, 'Ledger file');
    const pubKeyPath = ensureFileExists(options.pubKey, 'Public key');
    const result = verifyLedgerFile(ledgerPath, pubKeyPath);

    if (result.ok) {
      console.log(`✅ Ledger verified successfully. ${result.ledger.length} entries intact.`);
      process.exit(0);
    }

    for (const error of result.errors) {
      console.error(`❌ ${error}`);
    }
    console.error('❌ Ledger verification failed.');
    process.exit(1);
  } catch (error) {
    console.error(`❌ ${error.message}`);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}
