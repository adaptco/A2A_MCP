#!/usr/bin/env node
/**
 * Inscribe a contributor echo trace ledger derived from avatar bindings data.
 *
 * The echo trace fuses P3L notes for each contributor avatar so rehearsal capsules
 * can be replayed with lineage-aware commentary.
 */

const fs = require('fs');
const path = require('path');

const DEFAULT_SOURCE = path.join('public', 'data', 'avatar_bindings.v1.json');
const DEFAULT_OUTPUT = path.join('.out', 'contributor_echo_trace.jsonl');
const DEFAULT_CAPSULE = 'capsule.contributor.echo_trace.v1';

function parseArgs(argv) {
  const args = {
    source: DEFAULT_SOURCE,
    out: DEFAULT_OUTPUT,
    capsule: DEFAULT_CAPSULE,
    mode: 'append',
    dryRun: false,
  };

  for (let i = 2; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') {
      args.help = true;
      break;
    }

    if (arg === '--dry-run') {
      args.dryRun = true;
    } else if (arg.startsWith('--source=')) {
      args.source = arg.slice('--source='.length);
    } else if (arg === '--source' && i + 1 < argv.length) {
      args.source = argv[i + 1];
      i += 1;
    } else if (arg.startsWith('--out=')) {
      args.out = arg.slice('--out='.length);
    } else if (arg === '--out' && i + 1 < argv.length) {
      args.out = argv[i + 1];
      i += 1;
    } else if (arg.startsWith('--capsule=')) {
      args.capsule = arg.slice('--capsule='.length);
    } else if (arg === '--capsule' && i + 1 < argv.length) {
      args.capsule = argv[i + 1];
      i += 1;
    } else if (arg.startsWith('--mode=')) {
      args.mode = arg.slice('--mode='.length);
    } else if (arg === '--mode' && i + 1 < argv.length) {
      args.mode = argv[i + 1];
      i += 1;
    } else if (arg.startsWith('--seed=')) {
      args.seed = arg.slice('--seed='.length);
    } else if (arg === '--seed' && i + 1 < argv.length) {
      args.seed = argv[i + 1];
      i += 1;
    }
  }

  return args;
}

function printHelp() {
  console.log(`Inscribe a contributor echo trace ledger for rehearsal capsules.\n\n` +
    `Usage:\n  node scripts/contributors/inscribeContributorEchoTrace.js [options]\n\n` +
    `Options:\n` +
    `  --source <path>   Avatar bindings JSON source (default: ${DEFAULT_SOURCE})\n` +
    `  --out <path>      Target NDJSON ledger file (default: ${DEFAULT_OUTPUT})\n` +
    `  --capsule <id>    Capsule identifier stamped on each entry\n` +
    `  --mode <append|overwrite>  File write strategy (default: append)\n` +
    `  --seed <iso8601>  Deterministic base timestamp for reproducible runs\n` +
    `  --dry-run         Do not write to disk, just preview the payload\n` +
    `  -h, --help        Show this help message and exit.`);
}

function ensureDirExists(filePath) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function isoTimestamp(baseTime, offsetSeconds) {
  const ts = new Date(baseTime.getTime() + offsetSeconds * 1000);
  return ts.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function loadAvatarBindings(sourcePath) {
  const payload = fs.readFileSync(sourcePath, 'utf8');
  const parsed = JSON.parse(payload);
  if (!Array.isArray(parsed.avatars)) {
    throw new Error('Avatar bindings file does not contain an "avatars" array.');
  }
  return parsed.avatars;
}

function buildEchoEntry(avatar, capsuleId, timestamp) {
  const glyph = avatar.glyph || null;
  const glyphText = glyph && glyph.text ? glyph.text : '—';
  const glyphAnchor = avatar.geometry && avatar.geometry.glyph_anchor
    ? avatar.geometry.glyph_anchor
    : 'unspecified anchor';

  const proofNote = `Glyph ${glyphText} anchored at ${glyphAnchor}.`;
  const flowNoteParts = [`Capsule ${avatar.capsule || 'unknown'}`];
  if (avatar.capsule_gate) {
    flowNoteParts.push(`gate ${avatar.capsule_gate}`);
  }
  flowNoteParts.push(`vessel ${avatar.vessel || 'unspecified'}`);
  const flowNote = flowNoteParts.join(' → ');

  const executionNote = avatar.framing
    ? `Framing directive: ${avatar.framing}.`
    : 'Framing directive: not specified.';

  return {
    t: timestamp,
    capsule: capsuleId,
    contributor: {
      id: avatar.id,
      name: avatar.name,
      vessel: avatar.vessel,
    },
    glyph,
    capsule_gate: avatar.capsule_gate || null,
    proof: {
      note: proofNote,
      geometry_reference: glyphAnchor,
    },
    flow: {
      note: flowNote,
      policies: {
        route: avatar.capsule || null,
        gate: avatar.capsule_gate || null,
      },
    },
    execution: {
      note: executionNote,
      overlay_hint: avatar.geometry && avatar.geometry.props ? avatar.geometry.props.join('; ') : null,
    },
    resonance: {
      palette: avatar.colors || null,
      signal: avatar.features && avatar.features.light_pool ? avatar.features.light_pool : null,
      material: avatar.materials ? Object.values(avatar.materials).filter(Boolean)[0] || null : null,
    },
  };
}

function writeLedger(outPath, mode, lines) {
  ensureDirExists(outPath);
  if (mode === 'overwrite') {
    fs.writeFileSync(outPath, `${lines.join('\n')}\n`, 'utf8');
  } else if (mode === 'append') {
    fs.appendFileSync(outPath, `${lines.join('\n')}\n`, 'utf8');
  } else {
    throw new Error(`Unsupported mode: ${mode}. Use "append" or "overwrite".`);
  }
}

function previewTable(entries) {
  const table = entries.map((entry) => ({
    t: entry.t,
    contributor: `${entry.contributor.name} (${entry.contributor.id})`,
    glyph: entry.glyph ? entry.glyph.text : '—',
    vessel: entry.contributor.vessel || 'n/a',
    proof: entry.proof.note,
    flow: entry.flow.note,
    execution: entry.execution.note,
  }));
  console.table(table);
}

function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    printHelp();
    process.exit(0);
  }

  const sourcePath = path.resolve(args.source);
  const outPath = path.resolve(args.out);

  if (!fs.existsSync(sourcePath)) {
    console.error(`Avatar bindings source not found: ${sourcePath}`);
    process.exit(1);
  }

  const avatars = loadAvatarBindings(sourcePath);
  const baseTime = args.seed ? new Date(args.seed) : new Date();

  const entries = avatars.map((avatar, idx) => {
    const timestamp = isoTimestamp(baseTime, idx * 5);
    return buildEchoEntry(avatar, args.capsule, timestamp);
  });

  previewTable(entries);

  if (!args.dryRun) {
    const lines = entries.map((entry) => JSON.stringify(entry));
    writeLedger(outPath, args.mode, lines);
    console.log(`\nEcho trace ledger ${args.mode === 'append' ? 'appended to' : 'written at'} → ${outPath}`);
  } else {
    console.log('\nDry run enabled → no ledger file written.');
  }
}

main();
