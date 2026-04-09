#!/usr/bin/env bash
# rewrite-history.sh — Remove large files from git history
#
# This script uses git-filter-repo to purge large artifacts from the
# repository history: venv/, dist/, node_modules/, and large generated docs.
#
# PREREQUISITES:
#   pip install git-filter-repo
#
# WARNING: This rewrites git history and requires a force push.
#   - All collaborators must re-clone or rebase after the rewrite
#   - Back up the repo before running
#   - Run on a fresh clone (git-filter-repo requires it)
#
# Usage:
#   git clone <repo-url> repo-rewrite
#   cd repo-rewrite
#   bash scripts/rewrite-history.sh
#   # Review the result, then force-push:
#   git push --force origin main
#
# Estimated savings: ~400MB+ (based on objects analysis)
#
# Large objects in history (as of 2026-04-09):
#   - docs/generated/generated/api-data.json: ~75MB x 12 versions
#   - docs/generated/api-data.json: ~73MB x 5 versions
#   - docs/generated/api/python.md: ~49MB x 8 versions
#   - packages/earthsci_toolkit/venv/: ~25MB+ (numpy/scipy .so files)
#   - packages/esm-format-go/esm-go: ~13MB x 3 versions
#   - packages/esm-format/node_modules/: ~9MB+ (esbuild, typescript)
#   - dist/: ~8MB+ (CLI binaries)

set -euo pipefail

if ! command -v git-filter-repo &>/dev/null; then
    echo "ERROR: git-filter-repo is required. Install with: pip install git-filter-repo"
    exit 1
fi

# Verify we're in a git repo
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "ERROR: Not inside a git repository"
    exit 1
fi

# git-filter-repo requires a fresh clone (no remotes configured as "origin"
# unless --force is used)
echo "=== Removing large directories from history ==="
echo "This will rewrite ALL commits. Estimated time: 1-5 minutes."
echo ""

git filter-repo \
    --invert-paths \
    --path-glob 'venv/' \
    --path-glob '**/venv/' \
    --path-glob 'dist/' \
    --path-glob '**/dist/' \
    --path-glob 'node_modules/' \
    --path-glob '**/node_modules/' \
    --path-glob 'docs/generated/api-data.json' \
    --path-glob 'docs/generated/generated/api-data.json' \
    --path-glob '**/esm-go' \
    --path-glob '**/esm-format-go' \
    --force

echo ""
echo "=== History rewrite complete ==="
echo ""
echo "Before/after comparison:"
git count-objects -vH
echo ""
echo "Next steps:"
echo "  1. Review the rewritten history: git log --oneline | head -20"
echo "  2. Add the remote back: git remote add origin <repo-url>"
echo "  3. Force push: git push --force origin main"
echo "  4. All collaborators must re-clone or run:"
echo "     git fetch origin && git reset --hard origin/main"
