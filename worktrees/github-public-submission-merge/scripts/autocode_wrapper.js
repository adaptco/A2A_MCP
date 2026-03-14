#!/usr/bin/env node
'use strict';

const path = require('path');
const { inspectWrapperEnvironment } = require('../adaptco-core-orchestrator/src/wrapper');

async function main() {
  const cwd = process.cwd();
  const args = process.argv.slice(2);
  const options = { cwd };
  let compact = false;

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    switch (arg) {
      case '--wrapper':
      case '-w': {
        const value = args[index + 1];
        if (!value) {
          throw new Error('Missing value for --wrapper');
        }
        options.wrapperPath = path.resolve(cwd, value);
        index += 1;
        break;
      }
      case '--registry':
      case '-r': {
        const value = args[index + 1];
        if (!value) {
          throw new Error('Missing value for --registry');
        }
        options.registryPath = path.resolve(cwd, value);
        index += 1;
        break;
      }
      case '--runtime-dir':
      case '-d': {
        const value = args[index + 1];
        if (!value) {
          throw new Error('Missing value for --runtime-dir');
        }
        options.runtimeDir = path.resolve(cwd, value);
        index += 1;
        break;
      }
      case '--compact':
        compact = true;
        break;
      case '--help':
      case '-h':
        printHelp();
        return;
      default:
        throw new Error(`Unknown argument: ${arg}`);
    }
  }

  const report = await inspectWrapperEnvironment(options);
  const json = compact ? JSON.stringify(report) : `${JSON.stringify(report, null, 2)}\n`;
  process.stdout.write(json);
}

function printHelp() {
  const message = `Usage: autocode_wrapper [options]\n\n` +
    `Inspect the ADAPTCO OS wrapper capsule bindings and runtime vessels.\n\n` +
    `Options:\n` +
    `  -w, --wrapper <path>      Path to wrapper capsule JSON (default capsules/doctrine/...)\n` +
    `  -r, --registry <path>     Path to runtime registry JSON (default runtime/capsule.registry.runtime.v1.json)\n` +
    `  -d, --runtime-dir <path>  Directory containing runtime assets (default ./runtime)\n` +
    `      --compact             Emit compact JSON (single line)\n` +
    `  -h, --help                Show this help message`; 
  process.stdout.write(`${message}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exit(1);
});
