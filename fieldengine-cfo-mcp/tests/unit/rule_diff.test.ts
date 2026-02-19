import { describe, expect, it } from 'vitest';
import { compareRules, diffRules } from '../../src/domain/policy_engine/rule_diff.js';

describe('compareRules', () => {
  it('returns added, removed, and unchanged rules', () => {
    expect(compareRules(['a', 'b'], ['b', 'c'])).toEqual({
      added: ['c'],
      removed: ['a'],
      unchanged: ['b'],
    });
  });

  it('de-duplicates repeated values before comparison', () => {
    expect(compareRules(['a', 'a', 'b'], ['b', 'b', 'c', 'c'])).toEqual({
      added: ['c'],
      removed: ['a'],
      unchanged: ['b'],
    });
  });
});

describe('diffRules', () => {
  it('keeps backward-compatible added-rule output', () => {
    expect(diffRules(['retained_earnings'], ['retained_earnings', 'cash_buffer'])).toEqual([
      'cash_buffer',
    ]);
  });
});
