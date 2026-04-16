#!/usr/bin/env bash
# sync-schema.sh — Copy root esm-schema.json to all language package locations
# and verify that binding package versions stay aligned.
#
# Usage:
#   scripts/sync-schema.sh          # Copy root schema to all packages
#   scripts/sync-schema.sh --check  # Check schema + version drift (exit 1 if any)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CANONICAL="${REPO_ROOT}/esm-schema.json"

TARGETS=(
  "packages/esm-format-go/pkg/esm/esm-schema.json"
  "packages/earthsci-toolkit-rs/src/esm-schema.json"
  "packages/EarthSciSerialization.jl/data/esm-schema.json"
  "packages/earthsci_toolkit/src/earthsci_toolkit/data/esm-schema.json"
)

# Binding manifests that must share a synchronized version string.
# Go (esm-format-go) uses module-path versioning via git tags and is not listed.
VERSION_MANIFESTS=(
  "packages/earthsci-toolkit/package.json"
  "packages/earthsci_toolkit/pyproject.toml"
  "packages/earthsci-toolkit-rs/Cargo.toml"
  "packages/EarthSciSerialization.jl/Project.toml"
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

# Extract the version field from a binding manifest.
# Emits "<file>: <version>" to stdout.
read_version() {
  local manifest="$1"
  local full_path="${REPO_ROOT}/${manifest}"
  local version=""
  case "$manifest" in
    *package.json)
      version=$(python3 -c "import json,sys; print(json.load(open('$full_path'))['version'])")
      ;;
    *pyproject.toml|*Cargo.toml|*Project.toml)
      version=$(grep -m1 -E '^version\s*=' "$full_path" | sed -E 's/^version\s*=\s*"([^"]+)".*/\1/')
      ;;
  esac
  printf '%s' "$version"
}

if [[ "$check_mode" == true ]]; then
  echo ""
  echo "Binding versions:"
  declare -A seen
  for manifest in "${VERSION_MANIFESTS[@]}"; do
    full_path="${REPO_ROOT}/${manifest}"
    if [[ ! -f "$full_path" ]]; then
      echo "MISSING: $manifest"
      drifted=1
      continue
    fi
    v=$(read_version "$manifest")
    if [[ -z "$v" ]]; then
      echo "UNPARSED: $manifest"
      drifted=1
      continue
    fi
    printf '  %-60s %s\n' "$manifest" "$v"
    seen["$v"]=1
  done
  if [[ "${#seen[@]}" -gt 1 ]]; then
    echo "VERSION DRIFT: bindings disagree on version (${!seen[*]})"
    drifted=1
  fi
fi

if [[ "$check_mode" == true && "$drifted" -ne 0 ]]; then
  echo ""
  echo "Drift detected. Fix schema drift by running: scripts/sync-schema.sh"
  echo "Fix version drift by editing the listed manifests to agree."
  exit 1
fi
