// adaptco-previz/src/validator.js
'use strict';

const Ajv = require('ajv/dist/2020');
const addFormats = require('ajv-formats');
const schema = require('../schemas/asset-descriptor.schema.json');

const ajv = new Ajv({
  allErrors: true,
  strict: false
});
addFormats(ajv);

const validate = ajv.compile(schema);

function validateDescriptor(descriptor) {
  const valid = validate(descriptor);
  if (!valid) {
    const error = new Error('Descriptor validation failed');
    error.errors = validate.errors;
    throw error;
  }
  return descriptor;
}

module.exports = {
  ajv,
  validateDescriptor
};
