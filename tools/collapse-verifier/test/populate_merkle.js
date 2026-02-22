// Small helper to compute leaf hashes and merkle root for the fixture
const fs = require('fs');
const path = require('path');
const { leafHash, merkleRoot } = require('../src/merkle');

const filePath = path.resolve('test/fixtures/batch.json');
const batch = JSON.parse(fs.readFileSync(filePath, 'utf8'));

const leaves = batch.items.map((item) => {
  const hash = leafHash(item);
  item.merkle.leaf_hash = hash;
  return hash;
});

const root = merkleRoot(leaves);
batch.merkle_root = root;
batch.items.forEach((item) => {
  item.merkle.root_hash = root;
});

fs.writeFileSync(filePath, JSON.stringify(batch, null, 2));
console.log('Populated batch.json with merkle_root:', root);
