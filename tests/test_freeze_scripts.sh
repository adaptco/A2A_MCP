#!/usr/bin/env bash

set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PASS_COUNT=0
FAIL_COUNT=0

pass() {
  printf 'PASS: %s\n' "$1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  printf 'FAIL: %s\n' "$1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

reset_outputs() {
  rm -f governance/authority_map.v1.canonical.json \
        governance/authority_map.v1.hash \
        governance/authority_map.v1.sig \
        governance/capsule_remap.v1.canonical.json \
        governance/capsule_remap.v1.hash \
        governance/capsule_remap.v1.sig
}

run_with_stub_signer() {
  local stub_dir
  stub_dir="$(mktemp -d)"
  cat <<'COSIGN' >"${stub_dir}/cosign"
#!/usr/bin/env bash
set -eu
if [ "$#" -lt 2 ]; then
  echo "cosign stub expects subcommand" >&2
  exit 1
fi
subcommand="$1"
shift
if [ "$subcommand" != "sign-blob" ]; then
  echo "cosign stub supports only sign-blob" >&2
  exit 1
fi
blob=""
while [ $# -gt 0 ]; do
  case "$1" in
    --yes)
      shift
      ;;
    --key)
      shift
      if [ $# -gt 0 ]; then
        shift
      fi
      ;;
    --*)
      # ignore other flags
      shift
      ;;
    *)
      blob="$1"
      shift
      break
      ;;
  esac
done
if [ -z "$blob" ]; then
  echo "cosign stub missing blob argument" >&2
  exit 1
fi
sig="MOCK-SIGNATURE:$(sha256sum "$blob" | awk '{print $1}')"
printf '%s\n' "$sig"
exit 0
COSIGN
  chmod +x "${stub_dir}/cosign"
  PATH="${stub_dir}:$PATH" "$@"
  rm -rf "$stub_dir"
}

reset_outputs

run_with_stub_signer scripts/freeze_authority_map.sh >/tmp/freeze_authority.stdout 2>/tmp/freeze_authority.stderr || fail "freeze_authority_map.sh should succeed with stub signer"
if [ -f governance/authority_map.v1.canonical.json ]; then
  pass "authority_map canonical generated"
else
  fail "authority_map canonical missing"
fi
if [ -f governance/authority_map.v1.hash ]; then
  expected_hash="$(sha256sum governance/authority_map.v1.canonical.json | awk '{print $1}')"
  actual_hash="$(cat governance/authority_map.v1.hash)"
  if [ "$expected_hash" = "$actual_hash" ]; then
    pass "authority_map hash matches"
  else
    fail "authority_map hash mismatch"
  fi
else
  fail "authority_map hash missing"
fi
if [ -f governance/authority_map.v1.sig ]; then
  if grep -q '^MOCK-SIGNATURE:' governance/authority_map.v1.sig; then
    pass "authority_map signature captured"
  else
    fail "authority_map signature unexpected"
  fi
else
  fail "authority_map signature missing"
fi

run_with_stub_signer scripts/freeze_remap.sh >/tmp/freeze_remap.stdout 2>/tmp/freeze_remap.stderr || fail "freeze_remap.sh should succeed with stub signer"
if [ -f governance/capsule_remap.v1.canonical.json ]; then
  pass "capsule_remap canonical generated"
else
  fail "capsule_remap canonical missing"
fi
if [ -f governance/capsule_remap.v1.hash ]; then
  expected_hash="$(sha256sum governance/capsule_remap.v1.canonical.json | awk '{print $1}')"
  actual_hash="$(cat governance/capsule_remap.v1.hash)"
  if [ "$expected_hash" = "$actual_hash" ]; then
    pass "capsule_remap hash matches"
  else
    fail "capsule_remap hash mismatch"
  fi
else
  fail "capsule_remap hash missing"
fi
if [ -f governance/capsule_remap.v1.sig ]; then
  if grep -q '^MOCK-SIGNATURE:' governance/capsule_remap.v1.sig; then
    pass "capsule_remap signature captured"
  else
    fail "capsule_remap signature unexpected"
  fi
else
  fail "capsule_remap signature missing"
fi

if scripts/freeze_authority_map.sh >/tmp/freeze_missing.stdout 2>/tmp/freeze_missing.stderr; then
  fail "freeze_authority_map.sh should fail without cosign"
else
  if grep -q 'cosign required but not found. Install cosign or provide SIGNER' /tmp/freeze_missing.stderr; then
    pass "freeze_authority_map.sh emits cosign guidance"
  else
    fail "freeze_authority_map.sh missing cosign guidance"
  fi
fi

reset_outputs

printf 'PASS total: %d\n' "$PASS_COUNT"
if [ "$FAIL_COUNT" -eq 0 ]; then
  printf 'All freeze script tests passed.\n'
  exit 0
fi
printf 'FAIL total: %d\n' "$FAIL_COUNT"
exit 1
