// adaptco-core-orchestrator/src/sentinel.js
'use strict';

const { spawn } = require('child_process');
const { promises: fsp } = require('fs');
const os = require('os');
const path = require('path');
const { randomUUID } = require('crypto');
const logger = require('./log');

const REQUIRED_DESCRIPTOR_FIELDS = ['id', 'name', 'type', 'sourcePath', 'params'];
const REQUIRED_ASSET_FIELDS = ['id', 'name', 'kind', 'uri'];

class SentinelAgent {
  constructor(options = {}) {
    this.nodePath = options.nodePath || process.execPath;
    this.previzCli = options.previzCli || path.resolve(__dirname, '..', '..', 'adaptco-previz', 'src', 'cli.js');
    this.previzOutDir = options.previzOutDir || path.resolve(process.cwd(), 'previews');
    this.ssotBaseUrl = options.ssotBaseUrl || 'http://localhost:3000';
    this.runCommand = options.runCommand || defaultRunCommand;
    this.fetchImpl = options.fetch || globalThis.fetch;
    this.descriptorDir = options.descriptorDir || path.join(os.tmpdir(), 'core-orchestrator', 'previz-descriptors');
    this.descriptorWriter = options.descriptorWriter || createDescriptorWriter(this.descriptorDir);

    if (typeof this.runCommand !== 'function') {
      throw new TypeError('runCommand must be a function');
    }

    if (typeof this.fetchImpl !== 'function') {
      throw new TypeError('fetch implementation must be provided');
    }

    if (typeof this.descriptorWriter !== 'function') {
      throw new TypeError('descriptorWriter must be a function');
    }
  }

  async renderPreview(descriptor, options = {}) {
    const outDir = options.outDir || this.previzOutDir;
    let descriptorPath;
    let shouldCleanup = false;

    if (typeof descriptor === 'string') {
      descriptorPath = descriptor;
    } else if (descriptor && typeof descriptor === 'object') {
      const validationOptions = {
        allowMissingParams: Boolean(options.descriptorPath)
      };
      this.#validateDescriptor(descriptor, validationOptions);
      descriptorPath = await this.descriptorWriter(descriptor, options.descriptorPath);
      shouldCleanup = !options.descriptorPath;
    } else {
      throw new TypeError('descriptor must be a string path or object payload');
    }

    const command = this.#buildPrevizCommand(descriptorPath, outDir);

    const commandOptions = {
      signal: options.signal,
      cwd: options.cwd,
      env: options.env
    };

    logger.debug({ command, outDir }, 'Dispatching PreViz render request');

    let result;
    try {
      result = await this.runCommand(command, commandOptions);
    } finally {
      if (shouldCleanup && !options.persistDescriptor) {
        await safeUnlink(descriptorPath);
      }
    }

    if (result.exitCode !== 0) {
      const error = new Error(`PreViz command failed with exit code ${result.exitCode}`);
      error.command = command;
      error.stdout = result.stdout;
      error.stderr = result.stderr;
      throw error;
    }

    return {
      command,
      outDir,
      stdout: (result.stdout || '').trim(),
      stderr: (result.stderr || '').trim()
    };
  }

  async registerAsset(asset, options = {}) {
    this.#validateAsset(asset);

    const targetPath = options.path || '/assets';
    const method = options.method || 'POST';
    const url = new URL(targetPath, this.ssotBaseUrl);
    const headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});

    logger.debug({ url: url.toString(), method }, 'Dispatching SSoT request');
    const response = await this.fetchImpl(url, {
      method,
      headers,
      body: JSON.stringify(asset),
      signal: options.signal
    });

    const text = await response.text();
    let body = null;
    if (text) {
      try {
        body = JSON.parse(text);
      } catch (error) {
        logger.warn({ err: error }, 'Failed to parse SSoT response JSON');
        body = text;
      }
    }

    if (!response.ok) {
      const error = new Error(`SSOT request failed with status ${response.status}`);
      error.status = response.status;
      error.body = body;
      throw error;
    }

    return {
      status: response.status,
      body
    };
  }

  #buildPrevizCommand(descriptorPath, outDir) {
    return [
      this.nodePath,
      this.previzCli,
      'render',
      path.resolve(descriptorPath),
      '--out',
      path.resolve(outDir)
    ];
  }

  #validateDescriptor(descriptor, options = {}) {
    const missing = REQUIRED_DESCRIPTOR_FIELDS.filter((key) => {
      if (key === 'params') {
        if (descriptor.params === undefined) {
          return !options.allowMissingParams;
        }

        return (
          typeof descriptor.params !== 'object' ||
          descriptor.params === null ||
          Array.isArray(descriptor.params)
        );
      }

      return !descriptor[key];
    });
    if (missing.length > 0) {
      throw new Error(`Descriptor missing required fields: ${missing.join(', ')}`);
    }
  }

  #validateAsset(asset) {
    if (!asset || typeof asset !== 'object') {
      throw new TypeError('Asset payload must be an object');
    }

    const missing = REQUIRED_ASSET_FIELDS.filter((key) => !asset[key]);

    if (!Array.isArray(asset.tags)) {
      missing.push('tags');
    }

    if (typeof asset.meta !== 'object' || asset.meta === null) {
      missing.push('meta');
    }

    const registry = asset.registry;
    if (!registry || typeof registry !== 'object') {
      missing.push('registry');
    } else {
      if (registry.capsule_id !== 'ssot.registry.v1') {
        missing.push('registry.capsule_id');
      }

      const entry = registry.entry;
      if (!entry || typeof entry !== 'object') {
        missing.push('registry.entry');
      } else {
        if (!entry.canonical_sha256) {
          missing.push('registry.entry.canonical_sha256');
        }
        if (!entry.merkle_root) {
          missing.push('registry.entry.merkle_root');
        }
        const attestation = entry.council_attestation;
        if (!attestation || !Array.isArray(attestation.signatures) || attestation.signatures.length === 0) {
          missing.push('registry.entry.council_attestation.signatures');
        }
      }

      const lineage = registry.lineage;
      if (!lineage || typeof lineage !== 'object') {
        missing.push('registry.lineage');
      } else if (typeof lineage.immutable !== 'boolean') {
        missing.push('registry.lineage.immutable');
      }

      const replay = registry.replay;
      if (!replay || typeof replay !== 'object') {
        missing.push('registry.replay');
      } else if (!Array.isArray(replay.conditions) || replay.conditions.length === 0) {
        missing.push('registry.replay.conditions');
      }
    }

    if (missing.length > 0) {
      throw new Error(`Asset payload missing or invalid fields: ${missing.join(', ')}`);
    }
  }
}

function defaultRunCommand(command, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command[0], command.slice(1), {
      cwd: options.cwd,
      env: options.env,
      signal: options.signal,
      stdio: ['ignore', 'pipe', 'pipe']
    });

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

    child.on('close', (exitCode) => {
      resolve({ stdout, stderr, exitCode });
    });
  });
}

function createDescriptorWriter(baseDir) {
  return async (descriptor, explicitPath) => {
    const targetPath = explicitPath ? path.resolve(explicitPath) : await createDescriptorPath(baseDir, descriptor);
    const payload = JSON.stringify(descriptor, null, 2);

    await fsp.mkdir(path.dirname(targetPath), { recursive: true });

    await fsp.writeFile(targetPath, payload, 'utf8');
    return targetPath;
  };
}

async function createDescriptorPath(baseDir, descriptor) {
  const slugSource = typeof descriptor.id === 'string' && descriptor.id.trim().length > 0 ? descriptor.id : 'descriptor';
  const slug = slugify(slugSource);
  const fileName = `${slug}-${randomUUID()}.json`;
  return path.join(baseDir, fileName);
}

function slugify(value) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-')
    || 'descriptor';
}

async function safeUnlink(filePath) {
  try {
    await fsp.unlink(filePath);
  } catch (error) {
    if (error && error.code !== 'ENOENT') {
      logger.warn({ err: error, filePath }, 'Failed to clean up descriptor file');
    }
  }
}

module.exports = SentinelAgent;
