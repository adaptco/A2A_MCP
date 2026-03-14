#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const CAPSULES_DIR = path.join(__dirname, '..', 'capsules');
const args = process.argv.slice(2);

function printHelp() {
  console.log('Usage: node scripts/previewCapsule.js [capsule-id|file-name]');
  console.log('       npm run preview -- [capsule-id|file-name]');
  console.log('');
  console.log('Without arguments the script lists all capsules discovered in the');
  console.log('capsules directory. Providing a capsule id or filename will render');
  console.log('a focused preview of that capsule.');
}

function ensureCapsuleDir() {
  if (!fs.existsSync(CAPSULES_DIR)) {
    console.error(`Capsules directory not found at ${CAPSULES_DIR}`);
    process.exit(1);
  }
}

function loadCapsuleEntries() {
  return fs
    .readdirSync(CAPSULES_DIR)
    .filter((fileName) => fileName.endsWith('.json'))
    .map((fileName) => {
      const filePath = path.join(CAPSULES_DIR, fileName);
      try {
        const raw = fs.readFileSync(filePath, 'utf8');
        const data = JSON.parse(raw);
        return { fileName, filePath, data };
      } catch (error) {
        console.warn(`⚠️  Could not parse ${fileName}: ${error.message}`);
        return null;
      }
    })
    .filter(Boolean)
    .sort((a, b) => {
      const aId = a.data.capsule_id ?? a.fileName;
      const bId = b.data.capsule_id ?? b.fileName;
      return aId.localeCompare(bId);
    });
}

function listCapsules(entries) {
  if (entries.length === 0) {
    console.log('No capsules found.');
    return;
  }

  console.log('Available capsules:\n');
  entries.forEach(({ data, fileName }) => {
    const capsuleId = data.capsule_id ?? fileName.replace(/\.json$/u, '');
    const type = data.type ?? 'unknown';
    const version = data.version ?? 'n/a';
    const status = data.attestation?.status ?? 'unlisted';
    console.log(`- ${capsuleId} (type: ${type}, version: ${version}, status: ${status})`);
  });

  console.log('\nUse "node scripts/previewCapsule.js <capsule-id>" for details.');
}

function previewCapsule(entries, target) {
  const normalizedTarget = target.endsWith('.json') ? target : `${target}.json`;

  const match =
    entries.find(({ fileName }) => fileName === target || fileName === normalizedTarget) ??
    entries.find(({ data }) => data.capsule_id === target);

  if (!match) {
    console.error(`Unable to find a capsule for "${target}".`);
    const suggestions = entries
      .map(({ data }) => data.capsule_id)
      .filter(Boolean)
      .slice(0, 5);
    if (suggestions.length > 0) {
      console.error('Known capsule ids include:');
      suggestions.forEach((id) => console.error(`  - ${id}`));
    }
    process.exit(1);
  }

  const { data, fileName } = match;
  const capsuleId = data.capsule_id ?? fileName.replace(/\.json$/u, '');

  console.log(`Capsule preview: ${capsuleId}`);
  console.log(`  File: ${fileName}`);
  if (data.type) console.log(`  Type: ${data.type}`);
  if (data.version) console.log(`  Version: ${data.version}`);
  if (data.attestation?.status) console.log(`  Status: ${data.attestation.status}`);

  const { capsule_id, type, version, ...rest } = data;
  const keys = Object.keys(rest).sort();

  keys.forEach((key) => {
    const value = rest[key];
    if (value === undefined || value === null) return;

    if (typeof value === 'object') {
      console.log(`\n${key}:`);
      printObject(value, 2);
    } else {
      console.log(`\n${key}: ${value}`);
    }
  });
}

function printObject(value, indent) {
  const prefix = ' '.repeat(indent);
  const text = JSON.stringify(value, null, 2)
    .split('\n')
    .map((line) => prefix + line)
    .join('\n');
  console.log(text);
}

function main() {
  if (args.includes('--help') || args.includes('-h')) {
    printHelp();
    return;
  }

  ensureCapsuleDir();
  const entries = loadCapsuleEntries();

  if (args.length === 0) {
    listCapsules(entries);
    return;
  }

  previewCapsule(entries, args[0]);
}

main();
