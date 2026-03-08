import { describe, expect, it } from 'vitest';
import { projectCapitalValue } from '../../src/domain/capital_model/models.js';

describe('projectCapitalValue', () => {
  it('adds delta', () => {
    expect(projectCapitalValue(10, 3)).toBe(13);
  });
});
