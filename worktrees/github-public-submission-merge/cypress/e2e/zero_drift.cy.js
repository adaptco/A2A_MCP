const crypto = require('crypto');

const canonicalize = (input) => input.trim().toLowerCase().replace(/\s+/g, ' ');
const computeHash = (canonical) => crypto.createHash('sha256').update(canonical).digest('hex');

const EXPECTED_CANONICAL_STRING = canonicalize('predict wear for hydraulic pump');
const EXPECTED_HASH = computeHash(EXPECTED_CANONICAL_STRING);

const runClientSimulation = (input) => {
  const canonical = canonicalize(input);
  const hash = computeHash(canonical);
  return { canonical, hash };
};

describe('ZERO-DRIFT verification', () => {
  it('ensures Mobile and Desktop produce identical Query Hashes', () => {
    const mobileResult = runClientSimulation('Predict Wear   for Hydraulic Pump');
    const desktopResult = runClientSimulation('predict wear for hydraulic pump  ');

    expect(mobileResult.canonical).to.eq(EXPECTED_CANONICAL_STRING);
    expect(desktopResult.canonical).to.eq(EXPECTED_CANONICAL_STRING);
    expect(mobileResult.hash).to.eq(EXPECTED_HASH);
    expect(desktopResult.hash).to.eq(EXPECTED_HASH);
    expect(mobileResult.hash).to.eq(desktopResult.hash);
  });

  it('ensures Server returns identical Top-K Ranking', () => {
    cy.request('POST', '/v1/embeddings', { input: EXPECTED_CANONICAL_STRING })
      .its('body')
      .then((body) => {
        expect(body.canonical_input).to.eq(EXPECTED_CANONICAL_STRING);
        expect(body.hash).to.eq(EXPECTED_HASH);
        expect(body.ids.slice(0, 2)).to.deep.equal([1, 2]);
        const scoresAreSorted = body.scores.every((entry, index) => {
          if (index === 0) return true;
          const prev = body.scores[index - 1];
          return prev.score > entry.score || (prev.score === entry.score && prev.doc_id <= entry.doc_id);
        });
        expect(scoresAreSorted).to.eq(true);
      });
  });
});
