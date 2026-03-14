#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

function usage() {
  const script = path.basename(process.argv[1] || 'export-audit-ledger');
  console.log(`Usage: ${script} --input <payloads.ndjson> [--output <dir>]`);
}

function parseArgs(argv) {
  const args = { input: null, output: 'vault/audits/burn_in_2026' };
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

function formatYamlScalar(value) {
  if (value === null || value === undefined) {
    return 'null';
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  const stringValue = String(value);
  if (
    stringValue === '' ||
    /[:#\n]/.test(stringValue) ||
    /^\s|\s$/.test(stringValue)
  ) {
    return JSON.stringify(stringValue);
  }
  return stringValue;
}

function toYaml(value, indent = 0) {
  const pad = ' '.repeat(indent);
  if (value === null || value === undefined) {
    return `${pad}null`;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return `${pad}[]`;
    }
    return value
      .map((item) => {
        if (item && (Array.isArray(item) || typeof item === 'object')) {
          return `${pad}-\n${toYaml(item, indent + 2)}`;
        }
        return `${pad}- ${formatYamlScalar(item)}`;
      })
      .join('\n');
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value).filter(([, entryValue]) => entryValue !== undefined);
    if (entries.length === 0) {
      return `${pad}{}`;
    }
    return entries
      .map(([key, entryValue]) => {
        if (entryValue && (Array.isArray(entryValue) || typeof entryValue === 'object')) {
          return `${pad}${key}:\n${toYaml(entryValue, indent + 2)}`;
        }
        return `${pad}${key}: ${formatYamlScalar(entryValue)}`;
      })
      .join('\n');
  }
  return `${pad}${formatYamlScalar(value)}`;
}

function toFrontmatter(data) {
  return `---\n${toYaml(data)}\n---`;
}

function extractTelemetry(entry) {
  const telemetry = entry.telemetry || {};
  return {
    drift: entry.drift ?? telemetry.drift,
    ppm: entry.ppm ?? telemetry.ppm,
    intervention_status:
      entry.intervention_status ??
      entry.interventionStatus ??
      telemetry.intervention_status ??
      telemetry.interventionStatus,
  };
}

function formatStatus(entry) {
  if (entry.entry_type === 'Standard') return '✅ Nominal';
  if (entry.entry_type === 'Refusal') return '🚫 Sentinel Veto';
  if (entry.status) return entry.status;
  return '✅ Nominal';
}

function formatTimestamp(entry) {
  return entry.timestamp ?? entry.created_at ?? entry.createdAt ?? 'unknown';
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input) {
    usage();
    process.exit(1);
  }

  const records = readJsonLines(args.input);
  fs.mkdirSync(args.output, { recursive: true });

  records.forEach((entry, idx) => {
    const sequenceId = entry.sequence_id ?? entry.sequenceId ?? idx + 1;
    const merkleRoot = entry.merkle_root ?? entry.merkleRoot;
    const prevMerkleRoot = entry.prev_merkle_root ?? entry.prevMerkleRoot;
    const telemetry = extractTelemetry(entry);

    const frontmatter = toFrontmatter({
      ...entry,
      sequence_id: sequenceId,
      run_id: entry.run_id ?? entry.runId,
      vehicle_id: entry.vehicle_id ?? entry.vehicleId,
      merkle_root: merkleRoot,
      prev_merkle_root: prevMerkleRoot,
      timestamp: formatTimestamp(entry),
    });

    const lines = [
      frontmatter,
      `# Audit Entry: Sequence ${sequenceId}`,
      '',
      `**Status:** ${formatStatus(entry)}`,
      `**Timestamp:** ${formatTimestamp(entry)}`,
      '',
      `**Drift:** ${telemetry.drift ?? 'n/a'}`,
      `**PPM:** ${telemetry.ppm ?? 'n/a'}`,
      `**Intervention Status:** ${telemetry.intervention_status ?? 'n/a'}`,
      '',
      '> [!ABSTRACT] Merkle Proof',
    ];

    if (merkleRoot) {
      lines.push(`> Root: \`0x${String(merkleRoot).replace(/^0x/, '')}\``);
    }
    if (prevMerkleRoot) {
      lines.push(`> Prev Root: \`0x${String(prevMerkleRoot).replace(/^0x/, '')}\``);
    }

    const fileName = path.join(args.output, `burn_in_seq_${String(sequenceId).padStart(6, '0')}.md`);
    fs.writeFileSync(fileName, `${lines.join('\n')}\n`, 'utf8');
  });

  console.log(`Exported ${records.length} audit entries → ${args.output}`);
}

if (require.main === module) {
  main();
}
