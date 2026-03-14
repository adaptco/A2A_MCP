// adaptco-core-orchestrator/src/hash_scroll.js
'use strict';

const { spawn } = require('child_process');
const path = require('path');

const HASH_SCROLL_SCRIPT = path.resolve(__dirname, '..', '..', 'hash_gen_scroll.py');

/**
 * Invoke the hash_gen_scroll.py helper to compute Merkle metadata for artifacts.
 *
 * @param {string[]} inputs - File paths that should be hashed by the scroll script.
 * @param {object} [options] - Execution configuration.
 * @param {string} [options.pythonPath] - Python executable to invoke (defaults to python3).
 * @param {string} [options.scriptPath] - Override for the hash_gen_scroll.py location.
 * @param {string} [options.outDir] - Output directory passed to the scroll script.
 * @param {string} [options.events] - events.ndjson path passed to the scroll script.
 * @param {string} [options.capsuleId] - Capsule identifier for the emitted manifest.
 * @param {string} [options.actor] - Actor recorded in the manifest metadata.
 * @param {string} [options.commit] - Commit hash propagated to the manifest.
 * @param {string} [options.runId] - CI run identifier propagated to the manifest.
 * @param {string} [options.signKey] - Optional Ed25519 signing key (base64) for the manifest.
 * @param {object} [options.env] - Additional environment variables for the child process.
 * @param {string} [options.cwd] - Working directory for the child process.
 * @returns {Promise<object>} Metadata describing the generated manifest.
 */
async function runHashScroll(inputs, options = {}) {
  if (!Array.isArray(inputs) || inputs.length === 0) {
    throw new TypeError('hash scroll requires at least one input file');
  }

  const python = options.pythonPath || 'python3';
  const script = options.scriptPath || HASH_SCROLL_SCRIPT;
  const args = [script, ...inputs];

  if (options.outDir) {
    args.push('--out-dir', options.outDir);
  }
  if (options.events) {
    args.push('--events', options.events);
  }
  if (options.capsuleId) {
    args.push('--capsule-id', options.capsuleId);
  }
  if (options.actor) {
    args.push('--actor', options.actor);
  }
  if (options.commit) {
    args.push('--commit', options.commit);
  }
  if (options.runId) {
    args.push('--run-id', options.runId);
  }
  if (options.signKey) {
    args.push('--sign-key', options.signKey);
  }

  const spawnOptions = {
    cwd: options.cwd || process.cwd(),
    env: { ...process.env, ...(options.env || {}) },
    stdio: ['ignore', 'pipe', 'pipe']
  };

  const result = await spawnAndCapture(python, args, spawnOptions);
  const parsed = parseHashScrollOutput(result.stdout);
  if (!parsed.merkleRoot || !parsed.batchDir) {
    const error = new Error('Failed to parse hash_gen_scroll output');
    error.stdout = result.stdout;
    error.stderr = result.stderr;
    throw error;
  }

  return {
    merkleRoot: parsed.merkleRoot,
    batchDir: parsed.batchDir,
    stdout: result.stdout,
    stderr: result.stderr,
    command: [python, ...args]
  };
}

function spawnAndCapture(command, args, options) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, options);
    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk;
    });

    child.stderr.on('data', (chunk) => {
      stderr += chunk;
    });

    child.on('error', (error) => {
      reject(error);
    });

    child.on('close', (code) => {
      if (code !== 0) {
        const error = new Error(`hash_gen_scroll exited with code ${code}`);
        error.exitCode = code;
        error.stdout = stdout;
        error.stderr = stderr;
        reject(error);
        return;
      }

      resolve({
        stdout: stdout.trim(),
        stderr: stderr.trim()
      });
    });
  });
}

function parseHashScrollOutput(output) {
  const parsed = {};
  for (const line of output.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    const [key, value] = trimmed.split('=', 2);
    if (key === 'root') {
      parsed.merkleRoot = value;
    } else if (key === 'batch_dir') {
      parsed.batchDir = value;
    }
  }
  return parsed;
}

module.exports = runHashScroll;

