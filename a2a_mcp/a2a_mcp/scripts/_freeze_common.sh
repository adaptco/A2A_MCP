#!/usr/bin/env bash

set -euo pipefail

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '%s\n' "Missing required command: $1" >&2
    exit 1
  fi
}

resolve_signer() {
  if [ -n "${SIGNER:-}" ]; then
    if command -v "$SIGNER" >/dev/null 2>&1; then
      printf '%s\n' "$SIGNER"
      return 0
    fi
    printf '%s\n' "Signer command '$SIGNER' not found" >&2
    exit 1
  fi
  if command -v cosign >/dev/null 2>&1; then
    printf '%s\n' cosign
    return 0
  fi
  printf '%s\n' "cosign required but not found. Install cosign or provide SIGNER" >&2
  exit 1
}

freeze_manifest() {
  input_file="$1"
  base_name="$2"

  require_cmd jq
  require_cmd sha256sum

  signer_bin="$(resolve_signer)"

  dir_name="$(dirname "$input_file")"
  canonical_file="${dir_name}/${base_name}.canonical.json"
  hash_file="${dir_name}/${base_name}.hash"
  sig_file="${dir_name}/${base_name}.sig"

  tmp_canonical="${canonical_file}.tmp"
  jq -S . "$input_file" > "$tmp_canonical"
  mv "$tmp_canonical" "$canonical_file"

  sha256sum "$canonical_file" | awk '{print $1}' > "${hash_file}.tmp"
  mv "${hash_file}.tmp" "$hash_file"

  sign_args=("$signer_bin" "sign-blob")
  if [ -n "${SIGNER_KEY:-}" ]; then
    sign_args+=("--key" "$SIGNER_KEY")
  fi
  if [ "${COSIGN_CONFIRM:-yes}" = "yes" ]; then
    sign_args+=("--yes")
  fi
  sign_args+=("$canonical_file")

  "${sign_args[@]}" > "${sig_file}.tmp"
  mv "${sig_file}.tmp" "$sig_file"

  printf '%s\n' "Frozen $base_name using $signer_bin"
}
