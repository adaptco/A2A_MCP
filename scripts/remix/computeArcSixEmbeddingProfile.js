const fs = require('fs');
const path = require('path');

const runtimeDir = path.join(__dirname, '..', '..', 'capsules', 'runtime');
const preludePath = path.join(runtimeDir, 'prelude.drift.arcSix.v1.json');
const threadPath = path.join(runtimeDir, 'thread.remix.eligibility.arcSix.v1.json');
const profilePath = path.join(runtimeDir, 'profile.embedding.arcSix.v1.json');

function loadJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (error) {
    throw new Error(`Failed to load ${path.basename(filePath)}: ${error.message}`);
  }
}

function normalizePercentage(value) {
  if (typeof value === 'number') {
    return value / 100;
  }

  if (typeof value === 'string') {
    const numeric = parseFloat(value.replace(/[^0-9.\-]/g, ''));
    if (!Number.isFinite(numeric)) {
      throw new Error(`Unable to parse percentage from value: ${value}`);
    }
    if (value.includes('%')) {
      return numeric / 100;
    }
    return numeric;
  }

  throw new Error(`Unsupported value type for percentage normalization: ${typeof value}`);
}

function computeGlyphVector(seed, dimensions) {
  const sanitized = seed.replace(/\s+/g, '').toLowerCase();
  const charCodes = Array.from(sanitized).map((char) => char.charCodeAt(0));

  if (charCodes.length === 0) {
    return Array(dimensions).fill(0);
  }

  const vector = Array.from({ length: dimensions }, (_, index) => {
    const primary = charCodes[index % charCodes.length];
    const secondary = charCodes[(index + 1) % charCodes.length];
    const mix = (primary * (index + 3) + secondary * (index + 1) + sanitized.length * 7) % 997;
    const scaled = (mix / 498.5) - 1; // normalize roughly to [-1, 1]
    return Number(scaled.toFixed(4));
  });

  return vector;
}

function computeMagnitude(vector) {
  const magnitude = Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0));
  return Number(magnitude.toFixed(4));
}

function dominantAxis(vector) {
  const axisIndex = vector.reduce((bestIndex, value, index, arr) => {
    if (Math.abs(value) > Math.abs(arr[bestIndex])) {
      return index;
    }
    return bestIndex;
  }, 0);

  return axisIndex;
}

function deriveEmotionAnchors(emotionalModulation) {
  return emotionalModulation.split('→').map((part) => part.trim());
}

function buildProfile() {
  const prelude = loadJson(preludePath);
  const thread = loadJson(threadPath);

  const glyphSeeds = prelude.glyph_seeds || [];
  const emotionSequence = deriveEmotionAnchors(prelude.emotional_modulation || '');
  const embeddingModel = {
    name: 'GlyphWeave-16d',
    version: '0.1.0',
    dimensionality: 16,
    training_corpus: 'Scrollstream Glyph Ledger v6',
    intent: 'Pedagogical motif resonance scoring'
  };

  const glyphEmbeddings = {};
  const dimensions = embeddingModel.dimensionality;
  glyphSeeds.forEach((seed) => {
    const vector = computeGlyphVector(seed, dimensions);
    glyphEmbeddings[seed] = {
      vector,
      magnitude: computeMagnitude(vector),
      dominant_axis: dominantAxis(vector),
      checksum: Number(
        vector
          .map((value, index) => Math.abs(value) * (index + 1))
          .reduce((sum, value) => sum + value, 0)
          .toFixed(4)
      )
    };
  });

  const glyphAlignment = thread.glyph_alignment || {};
  const emotionalDeltas = thread.emotional_deltas || {};

  const remixAlignment = Object.entries(glyphAlignment).reduce((accumulator, [contributor, score]) => {
    const normalized = normalizePercentage(score);
    const scoreString = typeof score === 'string' ? score : `${score}`;
    const glyphName = scoreString.includes('·') ? scoreString.split('·')[0].trim() : scoreString.trim();
    const rawDelta = emotionalDeltas[contributor] || '0';
    const parsedDelta = parseFloat(String(rawDelta).replace('+', ''));

    accumulator[contributor] = {
      glyph: glyphName,
      fidelity: Number(normalized.toFixed(4)),
      emotional_delta: Number((Number.isFinite(parsedDelta) ? parsedDelta : 0).toFixed(4))
    };
    return accumulator;
  }, {});

  const profile = {
    profile_id: 'embedding.arcSix.4737',
    source_capsules: {
      prelude: prelude.prelude_id,
      thread: thread.thread_id
    },
    embedding_model: embeddingModel,
    glyph_embeddings: glyphEmbeddings,
    emotional_projection: {
      sequence: emotionSequence,
      inquiry_anchor: emotionSequence[0] || null,
      resolution_anchor: emotionSequence[emotionSequence.length - 1] || null,
      modulation_vector: emotionSequence.map((phase, index) => ({
        phase,
        index,
        tension_bias: Number(((index / Math.max(emotionSequence.length - 1, 1)) - 0.5).toFixed(4))
      }))
    },
    remix_alignment: remixAlignment,
    seal: '.embedding.profiled + .arcSix.attested'
  };

  fs.writeFileSync(profilePath, `${JSON.stringify(profile, null, 2)}\n`);
  return profile;
}

function main() {
  const profile = buildProfile();
  // eslint-disable-next-line no-console
  console.log(`Arc Six embedding profile generated with ${Object.keys(profile.glyph_embeddings).length} glyph vectors.`);
}

if (require.main === module) {
  main();
}

module.exports = {
  buildProfile,
  computeGlyphVector,
  computeMagnitude,
  dominantAxis
};
