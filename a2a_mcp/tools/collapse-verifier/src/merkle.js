const crypto = require('crypto');
const { canonicalize } = require('./canonicalize');

// SHA-256 hex
function sha256Hex(input) {
  return crypto.createHash('sha256').update(input).digest('hex');
}

// Leaf hash: canonicalized JSON -> sha256
function leafHash(obj) {
  const canon = canonicalize(obj);
  return sha256Hex(canon);
}

// Compute merkle root from array of leaf hashes (hex strings)
// Uses left-right pairing; odd nodes are promoted (duplicate last)
function merkleRoot(leafHashes) {
  if (!leafHashes.length) return null;
  let layer = leafHashes.slice();
  while (layer.length > 1) {
    const next = [];
    for (let i = 0; i < layer.length; i += 2) {
      const left = layer[i];
      const right = i + 1 < layer.length ? layer[i + 1] : layer[i];
      next.push(sha256Hex(left + right));
    }
    layer = next;
  }
  return layer[0];
}

// Verify proof_path for a given leaf_hash against root_hash
// proof_path: [{position: "left"|"right", hash: "<hex>"}]
function verifyProof(leafHashHex, proofPath, rootHashHex) {
  let acc = leafHashHex;
  for (const step of proofPath) {
    if (step.position === 'left') {
      acc = sha256Hex(step.hash + acc);
    } else {
      acc = sha256Hex(acc + step.hash);
    }
  }
  return acc === rootHashHex;
}

module.exports = { sha256Hex, leafHash, merkleRoot, verifyProof };
