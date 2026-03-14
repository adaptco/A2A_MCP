// adaptco-ssot/src/store.js
'use strict';

const fs = require('fs');
const path = require('path');
const logger = require('./log');

const catalogPath = path.join(__dirname, '..', 'data', 'catalog.json');
let catalog = [];

function clone(value) {
  if (typeof structuredClone === 'function') {
    return structuredClone(value);
  }
  return JSON.parse(JSON.stringify(value));
}

function loadCatalog() {
  try {
    const raw = fs.readFileSync(catalogPath, 'utf8');
    catalog = JSON.parse(raw);
  } catch (error) {
    logger.warn({ err: error }, 'Failed to load catalog, initializing empty store');
    catalog = [];
  }
}

function persist() {
  fs.writeFileSync(catalogPath, JSON.stringify(catalog, null, 2));
}

function getAll() {
  return catalog.map((asset) => clone(asset));
}

function create(asset) {
  if (catalog.some((existing) => existing.id === asset.id)) {
    const error = new Error(`Asset with id ${asset.id} already exists`);
    error.statusCode = 409;
    throw error;
  }
  const stored = clone(asset);
  catalog.push(stored);
  persist();
  return clone(stored);
}

function update(id, asset) {
  const index = catalog.findIndex((existing) => existing.id === id);
  if (index === -1) {
    return null;
  }

  const targetId = asset.id;
  if (
    typeof targetId === 'string' &&
    targetId !== id &&
    catalog.some((existing, existingIndex) => existingIndex !== index && existing.id === targetId)
  ) {
    const error = new Error(`Asset with id ${targetId} already exists`);
    error.statusCode = 409;
    throw error;
  }
  catalog[index] = { ...asset };
  persist();
  return clone(catalog[index]);
}

function reload() {
  loadCatalog();
  return getAll();
}

loadCatalog();

module.exports = {
  getAll,
  create,
  update,
  reload,
  catalogPath
};
