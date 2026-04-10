#!/usr/bin/env bash
# sync-schema.sh — Copy root esm-schema.json to all language package locations.
#
# Usage:
#   scripts/sync-schema.sh          # Copy root schema to all packages
#   scripts/sync-schema.sh --check  # Check for drift (exit 1 if out of sync)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CANONICAL="${REPO_ROOT}/esm-schema.json"

TARGETS=(
  "packages/esm-format-go/pkg/esm/esm-schema.json"
  "packages/earthsci-toolkit-rs/src/esm-schema.json"
  "packages/EarthSciSerialization.jl/data/esm-schema.json"
  "packages/earthsci_toolkit/src/earthsci_toolkit/data/esm-schema.json"
)

if [[ ! -f "$CANONICAL" ]]; then
  echo "ERROR: Canonical schema not found: $CANONICAL" >&2
  exit 1
fi

check_mode=false
if [[ "${1:-}" == "--check" ]]; then
  check_mode=true
fi

drifted=0

for target in "${TARGETS[@]}"; do
  full_path="${REPO_ROOT}/${target}"
  if [[ "$check_mode" == true ]]; then
    if [[ ! -f "$full_path" ]]; then
      echo "MISSING: $target"
      drifted=1
    elif ! diff -q "$CANONICAL" "$full_path" > /dev/null 2>&1; then
      echo "DRIFT:   $target"
      drifted=1
    else
      echo "OK:      $target"
    fi
  else
    mkdir -p "$(dirname "$full_path")"
    cp "$CANONICAL" "$full_path"
    echo "Synced:  $target"
  fi
done

if [[ "$check_mode" == true && "$drifted" -ne 0 ]]; then
  echo ""
  echo "Schema drift detected. Run: scripts/sync-schema.sh"
  exit 1
fi
