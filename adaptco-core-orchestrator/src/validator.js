// adaptco-core-orchestrator/src/validator.js
'use strict';

const Ajv = require('ajv/dist/2020');
const addFormats = require('ajv-formats');

const ajv = new Ajv({
  allErrors: true,
  strict: false
});
addFormats(ajv);

function compile(schema) {
  if (typeof schema === 'string') {
    const validate = ajv.getSchema(schema);
    if (!validate) {
      throw new Error(`Schema not found for key: ${schema}`);
    }
    return validate;
  }

  if (schema && schema.$id) {
    const existing = ajv.getSchema(schema.$id);
    if (existing) {
      return existing;
    }
  }

  return ajv.compile(schema);
}

function validateOrThrow(schema, data) {
  const validate = compile(schema);
  const valid = validate(data);
  if (!valid) {
    const error = new Error('Validation failed');
    error.statusCode = 400;
    error.errors = validate.errors;
    throw error;
  }
  return data;
}

module.exports = {
  ajv,
  validateOrThrow
};
