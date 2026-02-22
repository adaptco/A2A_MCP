// adaptco-core-orchestrator/src/index.js
'use strict';

const express = require('express');
const logger = require('./log');
const createCapsuleRouter = require('./routes/capsules');
const defaultLedger = require('./ledger');
const SentinelAgent = require('./sentinel');
const defaultHashRunner = require('./hash_scroll');

function createApp(options = {}) {
  const app = express();

  app.use(express.json({ limit: '1mb' }));

  app.get('/health', (req, res) => {
    res.json({ status: 'ok', uptime: process.uptime() });
  });

  const sentinel = options.sentinel || new SentinelAgent(options.sentinelOptions || {});
  const ledger = options.ledger || defaultLedger;
  const hashRunner = options.hashRunner || defaultHashRunner;

  app.use(
    '/capsule',
    createCapsuleRouter({
      ledger,
      sentinel,
      hashRunner
    })
  );

  app.use((err, req, res, next) => {
    logger.error({ err }, 'Unhandled error');
    if (res.headersSent) {
      return next(err);
    }
    res.status(500).json({ status: 'error', message: 'internal server error' });
  });

  return app;
}

module.exports = createApp;
