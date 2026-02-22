#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "mock_cosign requires a subcommand" >&2
  exit 1
fi

subcommand="$1"
shift

if [ "$subcommand" != "sign-blob" ]; then
  echo "mock_cosign only supports sign-blob" >&2
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
  echo "mock_cosign missing blob argument" >&2
  exit 1
fi

if [ ! -f "$blob" ]; then
  echo "mock_cosign blob '$blob' not found" >&2
  exit 1
fi

sig="MOCK-SIGNATURE:$(sha256sum "$blob" | awk '{print $1}')"
printf '%s\n' "$sig"
