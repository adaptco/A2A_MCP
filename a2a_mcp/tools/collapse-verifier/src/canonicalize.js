// JCS-style deterministic canonicalizer
// Produces a compact, stable JSON string for hashing
function canonicalize(obj) {
  if (obj === null || typeof obj !== 'object') {
    return JSON.stringify(obj);
  }

  if (Array.isArray(obj)) {
    return '[' + obj.map(canonicalize).join(',') + ']';
  }

  const keys = Object.keys(obj).sort();
  const parts = keys.map((k) => JSON.stringify(k) + ':' + canonicalize(obj[k]));
  return '{' + parts.join(',') + '}';
}

module.exports = { canonicalize };
