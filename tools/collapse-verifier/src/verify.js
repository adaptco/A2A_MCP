const crypto = require('crypto');
const { canonicalize } = require('./canonicalize');
const { verifyProof, leafHash, merkleRoot } = require('./merkle');

// Helper to detect encoding (hex vs base64)
function detectEncoding(value) {
  if (/^[0-9a-fA-F]+$/.test(value)) return 'hex';
  return 'base64';
}

// Verify ed25519 signature using Node's crypto (Node 18+)
// publicKey: hex or base64 (auto-detect)
// signature: hex or base64
function verifyEd25519(publicKeyRaw, message, signatureRaw) {
  const pubKey = Buffer.from(publicKeyRaw, detectEncoding(publicKeyRaw));
  const sig = Buffer.from(signatureRaw, detectEncoding(signatureRaw));
  return crypto.verify(null, Buffer.from(message), { key: pubKey, format: 'der', type: 'spki' }, sig);
}

// Build verification receipt object
function buildVerificationReceipt(batch) {
  // batch: { batch_id, epoch_id, items: [CollapseReceipt.v2 objects], merkle_root, signer_pub, signature }
  const receipt = {
    schema_version: 'VERIFICATION_RECEIPT.v1',
    batch_id: batch.batch_id,
    epoch_id: batch.epoch_id,
    item_count: batch.items.length,
    merkle_root: batch.merkle_root,
    verified_at_utc: new Date().toISOString(),
    verification: {
      merkle_ok: false,
      signature_ok: false,
      item_proofs_ok: [],
    },
  };

  // Recompute leaf hashes and verify proofs for each item
  const leafHashes = batch.items.map((item) => leafHash(item));
  const recomputedRoot = merkleRoot(leafHashes);
  receipt.verification.merkle_ok = recomputedRoot === batch.merkle_root;

  // Verify each item's proof_path if present
  for (let i = 0; i < batch.items.length; i += 1) {
    const item = batch.items[i];
    const leaf = leafHashes[i];
    const proof = item.merkle && item.merkle.proof_path ? item.merkle.proof_path : [];
    const ok = verifyProof(leaf, proof, batch.merkle_root);
    receipt.verification.item_proofs_ok.push({ trace_id: item.trace_id || null, ok });
  }

  // Signature verification (optional): message is canonicalized batch header
  if (batch.signer_pub && batch.signature) {
    const header = {
      batch_id: batch.batch_id,
      epoch_id: batch.epoch_id,
      merkle_root: batch.merkle_root,
      item_count: batch.items.length,
    };
    const canon = canonicalize(header);
    try {
      receipt.verification.signature_ok = !!verifyEd25519(batch.signer_pub, canon, batch.signature);
    } catch (error) {
      receipt.verification.signature_ok = false;
      receipt.verification.signature_error = String(error);
    }
  }

  return receipt;
}

module.exports = { buildVerificationReceipt, verifyEd25519 };
