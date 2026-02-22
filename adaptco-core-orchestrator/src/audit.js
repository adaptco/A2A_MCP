// adaptco-core-orchestrator/src/audit.js
'use strict';

const fs = require('fs');
const path = require('path');
const { ledgerFile } = require('./ledger');

function normalizeCriteria(criteria = {}) {
  const { id, capsuleId, version } = criteria;

  if (!id && !capsuleId) {
    throw new Error('An artifact identifier (id or capsuleId) is required to build a trace');
  }

  if (id) {
    if (id.startsWith('capsule-')) {
      const remainder = id.slice('capsule-'.length);
      const lastDash = remainder.lastIndexOf('-');
      if (lastDash !== -1) {
        return {
          id,
          capsuleId: remainder.slice(0, lastDash),
          version: remainder.slice(lastDash + 1)
        };
      }
    }

    if (id.includes('.')) {
      const parts = id.split('.');
      return {
        id,
        capsuleId: parts.slice(0, -1).join('.'),
        version: parts[parts.length - 1]
      };
    }

    return { id, capsuleId, version };
  }

  return {
    id: version ? `capsule-${capsuleId}-${version}` : undefined,
    capsuleId,
    version
  };
}

async function readLedger(targetPath = ledgerFile) {
  const resolved = path.resolve(targetPath);
  try {
    const content = await fs.promises.readFile(resolved, 'utf8');
    return content
      .split(/\r?\n/)
      .filter(Boolean)
      .map((line) => JSON.parse(line));
  } catch (error) {
    if (error.code === 'ENOENT') {
      return [];
    }
    throw error;
  }
}

function entryTimestamp(entry) {
  return entry.at || entry.ts;
}

function deriveArtifactId(entries, criteria) {
  if (criteria.id) {
    return criteria.id;
  }

  const { capsuleId, version } = criteria;
  const filteredEntries = entries.filter((entry) => {
    const payloadCapsuleId = entry.payload?.capsule?.capsule_id;
    const capsuleMatch =
      payloadCapsuleId === capsuleId ||
      (typeof entry.capsule_id === 'string' && entry.capsule_id.startsWith(`${capsuleId}.`)) ||
      (typeof entry.capsule_ref === 'string' && entry.capsule_ref.startsWith(`${capsuleId}.`));

    if (!capsuleMatch) {
      return false;
    }

    if (!version) {
      return true;
    }

    const payloadVersion = entry.payload?.capsule?.version || entry.payload?.version;
    const artifactFromPayload = entry.payload?.id;

    return (
      payloadVersion === version ||
      (typeof artifactFromPayload === 'string' &&
        artifactFromPayload.startsWith(`capsule-${capsuleId}-`) &&
        artifactFromPayload.slice(`capsule-${capsuleId}-`.length) === version) ||
      entry.capsule_id === `${capsuleId}.${version}` ||
      entry.capsule_ref === `${capsuleId}.${version}`
    );
  });

  for (const entry of filteredEntries) {
    const payloadCapsuleId = entry.payload?.capsule?.capsule_id;
    const artifactFromPayload = entry.payload?.id;

    const capsuleMatch =
      payloadCapsuleId === capsuleId ||
      (typeof entry.capsule_id === 'string' && entry.capsule_id.startsWith(`${capsuleId}.`)) ||
      (typeof entry.capsule_ref === 'string' && entry.capsule_ref.startsWith(`${capsuleId}.`));

    if (!capsuleMatch) {
      continue;
    }

    if (artifactFromPayload) {
      return artifactFromPayload;
    }
    if (entry.capsule_id) {
      return entry.capsule_id;
    }
    if (entry.capsule_ref) {
      return entry.capsule_ref;
    }
  }

  if (version) {
    return `capsule-${capsuleId}-${version}`;
  }

  return undefined;
}

function matchesTarget(entry, artifactId, capsuleId) {
  const capsuleMatch =
    capsuleId &&
    (entry.payload?.capsule?.capsule_id === capsuleId ||
      (typeof entry.capsule_id === 'string' && entry.capsule_id.startsWith(`${capsuleId}.`)) ||
      (typeof entry.capsule_ref === 'string' && entry.capsule_ref.startsWith(`${capsuleId}.`)));

  const artifactMatch =
    artifactId &&
    (entry.payload?.id === artifactId || entry.capsule_id === artifactId || entry.capsule_ref === artifactId);

  return artifactMatch || capsuleMatch;
}

function deriveCapsuleFromArtifact(criteria) {
  if (criteria.capsuleId && criteria.version) {
    return {
      capsule_id: criteria.capsuleId,
      version: criteria.version
    };
  }
  return undefined;
}

function summarizeEvent(entry) {
  if (entry.type === 'capsule.registered' && entry.payload?.capsule) {
    const capsule = entry.payload.capsule;
    const capsuleLabel = [capsule.capsule_id, capsule.version].filter(Boolean).join(' ');
    return `Capsule ${capsuleLabel} registered`;
  }
  return `Event ${entry.type || entry.event}`;
}

function buildTrace(entries, criteria) {
  const normalized = normalizeCriteria(criteria);

  if (!Array.isArray(entries)) {
    throw new TypeError('entries must be an array');
  }

  const artifactId = deriveArtifactId(entries, normalized);
  const capsuleId = normalized.capsuleId;

  const matchingIndices = [];
  for (let idx = 0; idx < entries.length; idx += 1) {
    if (matchesTarget(entries[idx], artifactId, capsuleId)) {
      matchingIndices.push(idx);
    }
  }

  let selectedEntries;
  if (matchingIndices.length === 0) {
    selectedEntries = entries.filter((entry) => matchesTarget(entry, artifactId, capsuleId));
  } else {
    const firstIdx = Math.min(...matchingIndices);
    const lastIdx = Math.max(...matchingIndices);
    selectedEntries = entries.slice(firstIdx, lastIdx + 1);
  }

  if (selectedEntries.length === 0) {
    return null;
  }

  selectedEntries.sort((a, b) => {
    const aTime = entryTimestamp(a);
    const bTime = entryTimestamp(b);
    if (aTime === bTime) return 0;
    return aTime < bTime ? -1 : 1;
  });

  const resolvedArtifactId = artifactId || selectedEntries[0].payload?.id || selectedEntries[0].capsule_id;

  const events = selectedEntries.map((entry) => ({
    type: entry.type || entry.event,
    at: entryTimestamp(entry),
    payload: entry.payload || entry,
    summary: summarizeEvent(entry)
  }));

  const firstSeen = events[0].at;
  const lastSeen = events[events.length - 1].at;

  const trace = {
    artifactId: resolvedArtifactId,
    criteria: Object.assign({}, normalized, { id: resolvedArtifactId || normalized.id }),
    capsule: entries.find((entry) => entry.payload?.capsule)?.payload?.capsule || deriveCapsuleFromArtifact(normalized),
    totalEvents: events.length,
    firstSeen,
    lastSeen,
    events
  };

  return trace;
}

module.exports = {
  readLedger,
  buildTrace
};
