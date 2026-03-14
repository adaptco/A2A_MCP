# PRT.AUTO_REPAIR.V1

## Summary
- Describe the exact repair applied on top of the target PR.

## Trigger
- Link or quote the triggering review comment, check run, or system event.

## Changes
- List each file changed and why.

## Invariant Impact
- Confirm preservation of locked invariants:
  - INV.MAKER_CHECKER.PR_ONLY
  - INV.FINGERPRINT.MATCH_HERMETIC
  - INV.NETWORK.NO_EGRESS_HERMETIC
  - INV.SECRETS.NONE
  - INV.POLICY_ZONING.REVIEW_QUORUM
  - INV.ARTIFACTS.DETERMINISTIC

## Validation
- Include commands run and outcomes.

## Rollback
- Describe how to revert safely if needed.
