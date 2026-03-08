// adaptco-ssot/src/server.js
'use strict';

const app = require('./index');
const logger = require('./log');

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  logger.info({ port: PORT }, 'Adaptco SSoT API listening');
});
