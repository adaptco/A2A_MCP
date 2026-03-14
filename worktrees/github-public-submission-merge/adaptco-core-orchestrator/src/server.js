// adaptco-core-orchestrator/src/server.js
'use strict';

const createApp = require('./index');
const logger = require('./log');

const PORT = process.env.PORT || 3000;

const app = createApp();

app.listen(PORT, () => {
  logger.info({ port: PORT }, 'Adaptco Core Orchestrator listening');
});
