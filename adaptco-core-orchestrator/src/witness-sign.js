'use strict';

const { createHmac, timingSafeEqual } = require('crypto');

function canonicalize(value) {
  if (Array.isArray(value)) {
    return value.map((item) => canonicalize(item));
  }
  if (value && typeof value === 'object' && !(value instanceof Date)) {
    const sortedKeys = Object.keys(value).sort();
    return sortedKeys.reduce((acc, key) => {
      acc[key] = canonicalize(value[key]);
      return acc;
    }, {});
  }
  return value;
}

function canonJson(value) {
  return JSON.stringify(canonicalize(value));
}

function normalizeKey(hmacKey) {
  if (typeof hmacKey !== 'string') {
    throw new TypeError('hmacKey must be a hex string');
  }
  const trimmed = hmacKey.trim();
  if (!/^[0-9a-fA-F]+$/.test(trimmed) || trimmed.length % 2 !== 0) {
    throw new Error('hmacKey must be a valid hex string');
  }
  return Buffer.from(trimmed, 'hex');
}

function signPetition(petition, hmacKey) {
  const key = normalizeKey(hmacKey);
  const jcsString = canonJson(petition);
  const jcsBytes = Buffer.from(jcsString, 'utf8');
  const sigB64 = createHmac('sha256', key).update(jcsBytes).digest('base64');
  return { jcsBytes, sigB64 };
}

function verifyPetition(jcsBytes, sigB64, hmacKey) {
  const key = normalizeKey(hmacKey);
  const expected = createHmac('sha256', key).update(jcsBytes).digest();
  const provided = Buffer.from(sigB64, 'base64');
  if (expected.length !== provided.length) {
    return false;
  }
  return timingSafeEqual(expected, provided);
}

module.exports = {
  canonJson,
  signPetition,
  verifyPetition
};
