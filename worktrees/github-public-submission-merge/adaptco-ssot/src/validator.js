// adaptco-ssot/src/validator.js
'use strict';

const Ajv = require('ajv/dist/2020');
const addFormats = require('ajv-formats');
const schema = require('../schemas/asset.schema.json');

const ajv = new Ajv({
  allErrors: true,
  strict: false
});
addFormats(ajv);

const validate = ajv.compile(schema);

function validateAsset(asset) {
  const valid = validate(asset);
  if (!valid) {
    const error = new Error('Asset validation failed');
    error.statusCode = 400;
    error.errors = validate.errors;
    throw error;
  }

  const registryPacket = asset.registry;
  const entry = registryPacket.entry;

  if (entry.artifact_id !== asset.id) {
    const error = new Error('Asset id must match registry.entry.artifact_id');
    error.statusCode = 400;
    throw error;
  }

  if (entry.type !== asset.kind) {
    const error = new Error('Asset kind must match registry.entry.type');
    error.statusCode = 400;
    throw error;
  }

  if (!Array.isArray(entry.council_attestation.signatures) || entry.council_attestation.signatures.length === 0) {
    const error = new Error('registry.entry.council_attestation.signatures must include at least one value');
    error.statusCode = 400;
    throw error;
  }

  const lineage = registryPacket.lineage;
  if (typeof lineage.immutable !== 'boolean') {
    const error = new Error('registry.lineage.immutable must be a boolean');
    error.statusCode = 400;
    throw error;
  }

  const replay = registryPacket.replay;
  if (!Array.isArray(replay.conditions) || replay.conditions.length === 0) {
    const error = new Error('registry.replay.conditions must include at least one condition');
    error.statusCode = 400;
    throw error;
  }

  return asset;
}

module.exports = {
  ajv,
  validateAsset
};
