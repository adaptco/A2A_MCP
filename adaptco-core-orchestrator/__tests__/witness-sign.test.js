'use strict';

const Ajv = require('ajv');
const { signPetition, verifyPetition } = require('../src/witness-sign');
const schema = require('../schemas/Update_IoT_Twin_State.json');

const ajv = new Ajv();
const validate = ajv.compile(schema);

describe('Sovereign Petition Verification', () => {
  const hmacKey = '00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff';

  const validPetition = {
    world_id: 'ADAPTCO-PROT-01',
    nonce: `${new Date().toISOString()}-001`,
    proposed_state: {
      cabin_comfort: { target_temp_f: 72, fan_speed: 4 }
    }
  };

  test('Schema Conformance: Should pass valid cabin_comfort mutations', () => {
    expect(validate(validPetition)).toBe(true);
  });

  test('Boundary Refusal: Should fail if temp is outside 60-82 range', () => {
    const invalidTemp = {
      ...validPetition,
      proposed_state: { cabin_comfort: { target_temp_f: 55 } }
    };
    expect(validate(invalidTemp)).toBe(false);
  });

  test('Air-Gap Security: Should fail if safety-critical keys are injected', () => {
    const malicious = {
      ...validPetition,
      proposed_state: { steering_torque: 100 }
    };
    expect(validate(malicious)).toBe(false);
  });

  test('JCS Parity: Sign and Verify should maintain zero-drift across worldlines', () => {
    const { jcsBytes, sigB64 } = signPetition(validPetition, hmacKey);
    const isValid = verifyPetition(jcsBytes, sigB64, hmacKey);
    expect(isValid).toBe(true);

    const jcsString = jcsBytes.toString('utf8');
    const keys = Object.keys(JSON.parse(jcsString));
    expect(keys).toEqual([...keys].sort());
  });
});
