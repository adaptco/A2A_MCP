#!/usr/bin/env node
/**
 * Generate a glyphstream overlay preview for apprentice ignition arcs.
 *
 * The preview collates avatar glyph anchors, palettes, and capsule routes into a
 * single overlay document so cockpit operators can rehearse the HUD layout.
 */

const fs = require('fs');
const path = require('path');

const DEFAULT_SOURCE = path.join('public', 'data', 'avatar_bindings.v1.json');
const DEFAULT_OUTPUT = path.join('.out', 'glyphstream_overlay.preview.json');
const DEFAULT_OVERLAY_ID = 'hud.overlay.apprentice.preview.v1';

function parseArgs(argv) {
  const args = {
    source: DEFAULT_SOURCE,
    out: DEFAULT_OUTPUT,
    overlay: DEFAULT_OVERLAY_ID,
    pretty: false,
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
    } else if (arg === '--pretty') {
      args.pretty = true;
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
    } else if (arg.startsWith('--overlay=')) {
      args.overlay = arg.slice('--overlay='.length);
    } else if (arg === '--overlay' && i + 1 < argv.length) {
      args.overlay = argv[i + 1];
      i += 1;
    }
  }

  return args;
}

function printHelp() {
  console.log(`Preview a glyphstream overlay assembled from avatar bindings.\n\n` +
    `Usage:\n  node scripts/overlays/previewGlyphstreamOverlay.js [options]\n\n` +
    `Options:\n` +
    `  --source <path>    Avatar bindings JSON source (default: ${DEFAULT_SOURCE})\n` +
    `  --out <path>       Target overlay JSON file (default: ${DEFAULT_OUTPUT})\n` +
    `  --overlay <id>     Overlay identifier stamped on the document\n` +
    `  --pretty           Pretty-print JSON output\n` +
    `  --dry-run          Skip writing to disk\n` +
    `  -h, --help         Show this help message.`);
}

function ensureDirExists(filePath) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function loadAvatarBindings(sourcePath) {
  const payload = fs.readFileSync(sourcePath, 'utf8');
  const parsed = JSON.parse(payload);
  if (!Array.isArray(parsed.avatars)) {
    throw new Error('Avatar bindings file does not contain an "avatars" array.');
  }
  return parsed.avatars;
}

function buildOverlayEntries(avatars) {
  return avatars.map((avatar, idx) => ({
    channel: `apprentice-${idx + 1}`,
    contributor_id: avatar.id,
    contributor_name: avatar.name,
    vessel: avatar.vessel,
    glyph: avatar.glyph || null,
    anchor: avatar.geometry && avatar.geometry.glyph_anchor ? avatar.geometry.glyph_anchor : null,
    framing: avatar.framing || null,
    palette: avatar.colors || null,
    proof_lock: avatar.capsule || null,
    flow_route: avatar.capsule_gate || null,
    execution_hint: avatar.features && avatar.features.light_pool ? avatar.features.light_pool : null,
  }));
}

function previewTable(entries) {
  const table = entries.map((entry) => ({
    channel: entry.channel,
    contributor: `${entry.contributor_name} (${entry.contributor_id})`,
    glyph: entry.glyph ? entry.glyph.text : '—',
    anchor: entry.anchor || 'n/a',
    vessel: entry.vessel || 'n/a',
    flow_route: entry.flow_route || '—',
  }));
  console.table(table);
}

function writeOverlay(outPath, overlay, pretty) {
  ensureDirExists(outPath);
  const payload = pretty ? JSON.stringify(overlay, null, 2) : JSON.stringify(overlay);
  fs.writeFileSync(outPath, `${payload}\n`, 'utf8');
}

function main() {
  const args = parseArgs(process.argv);
  if (args.help) {
    printHelp();
    process.exit(0);
  }

  const sourcePath = path.resolve(args.source);
  if (!fs.existsSync(sourcePath)) {
    console.error(`Avatar bindings source not found: ${sourcePath}`);
    process.exit(1);
  }

  const avatars = loadAvatarBindings(sourcePath);
  const entries = buildOverlayEntries(avatars);
  previewTable(entries);

  const overlayDocument = {
    overlay_id: args.overlay,
    generated_at: new Date().toISOString(),
    source_capsule: 'capsule.rehearsal.scrollstream.v1',
    glyphstream: entries,
  };

  if (!args.dryRun) {
    const outPath = path.resolve(args.out);
    writeOverlay(outPath, overlayDocument, args.pretty);
    console.log(`\nGlyphstream overlay written → ${outPath}`);
  } else {
    console.log('\nDry run enabled → no overlay file written.');
  }
}

main();
