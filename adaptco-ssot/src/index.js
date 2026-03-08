// adaptco-ssot/src/index.js
'use strict';

const express = require('express');
const logger = require('./log');
const { validateAsset } = require('./validator');
const store = require('./store');

const app = express();

app.use(express.json({ limit: '1mb' }));

app.get('/health', (req, res) => {
  res.json({ status: 'ok', uptime: process.uptime() });
});

app.get('/assets', (req, res) => {
  res.json(store.getAll());
});

app.post('/assets', (req, res, next) => {
  try {
    const asset = validateAsset(req.body);
    const created = store.create(asset);
    res.status(201).json({ status: 'created', asset: created });
  } catch (error) {
    if (error.statusCode === 400) {
      res.status(400).json({ status: 'error', errors: error.errors || [] });
      return;
    }
    if (error.statusCode === 409) {
      res.status(409).json({ status: 'error', message: error.message });
      return;
    }
    next(error);
  }
});

app.put('/assets/:id', (req, res, next) => {
  try {
    const asset = validateAsset(req.body);
    if (asset.id !== req.params.id) {
      res.status(400).json({
        status: 'error',
        message: 'asset id must match request parameter'
      });
      return;
    }
    const updated = store.update(req.params.id, asset);
    if (!updated) {
      res.status(404).json({ status: 'error', message: 'asset not found' });
      return;
    }
    res.json({ status: 'ok', asset: updated });
  } catch (error) {
    if (error.statusCode === 400) {
      res.status(400).json({ status: 'error', errors: error.errors || [] });
      return;
    }
    if (error.statusCode === 409) {
      res.status(409).json({ status: 'error', message: error.message });
      return;
    }
    next(error);
  }
});

app.use((err, req, res, next) => {
  logger.error({ err }, 'Unhandled error');
  if (res.headersSent) {
    return next(err);
  }
  res.status(500).json({ status: 'error', message: 'internal server error' });
});

module.exports = app;
