#!/usr/bin/env bash
# rewrite-history.sh — Remove large files from git history
#
# This script uses git-filter-repo to purge large artifacts from the
# repository history: venv/, dist/, node_modules/, Go binaries, and
# large generated docs.
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
#   bash scripts/rewrite-history.sh [--dry-run]
#   # Review the result, then force-push:
#   git push --force --all origin
#
# Large objects in history (as of 2026-04-10):
#   - docs/generated/generated/api-data.json: ~75MB x 12 versions
#   - docs/generated/api-data.json: ~73MB x 5 versions
#   - docs/generated/api/python.md: ~49MB x 8 versions
#   - packages/earthsci_toolkit/venv/: ~25MB+ (numpy/scipy .so files)
#   - packages/esm_format/venv/: ~20MB+ (various .so files)
#   - packages/esm-format-go/esm-go: ~13MB x 3 versions
#   - packages/esm-format/node_modules/: ~9MB+ (esbuild, typescript)
#   - packages/esm-editor/node_modules/: ~5MB+
#   - dist/: ~8MB+ (CLI binaries)

set -euo pipefail

if ! command -v git-filter-repo &>/dev/null; then
    echo "ERROR: git-filter-repo is required. Install with: pip install git-filter-repo"
    exit 1
fi

# Verify we're in a git repo (not a worktree)
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo "ERROR: Not inside a git repository"
    exit 1
fi

if [ "$(git rev-parse --git-dir)" != ".git" ]; then
    echo "ERROR: Must be run from a standalone clone, not a worktree."
    echo "Usage: git clone <repo-url> repo-rewrite && cd repo-rewrite && bash scripts/rewrite-history.sh"
    exit 1
fi

DRY_RUN=false
if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=true
fi

echo "=== Pre-filter repository size ==="
git count-objects -vH
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "=== DRY RUN: Analyzing paths to remove ==="
    echo ""
    echo "Paths that would be removed:"
    for pattern in 'venv/' 'dist/' 'node_modules/'; do
        count=$(git log --all --diff-filter=A --name-only --pretty=format: -- "*${pattern}*" 2>/dev/null | sort -u | wc -l)
        echo "  ${pattern}: ${count} unique files in history"
    done
    echo ""
    echo "Large generated docs:"
    for pattern in 'docs/generated/api-data.json' 'docs/generated/generated/api-data.json' 'docs/generated/api/python.md'; do
        versions=$(git log --all --oneline -- "$pattern" 2>/dev/null | wc -l)
        echo "  ${pattern}: ${versions} commits"
    done
    echo ""
    echo "Run without --dry-run to execute the filter."
    exit 0
fi

echo "=== Removing large directories and files from history ==="
echo "This will rewrite ALL commits."
echo ""

# Use --path for exact prefix matching (more reliable than --path-glob for dirs)
# and --path-glob only for patterns needing wildcards.
#
# --path 'dir/' matches all files under dir/ at the repo root.
# --path-glob '**/dir' matches nested occurrences anywhere in the tree.
git filter-repo \
    --invert-paths \
    --path 'venv/' \
    --path 'dist/' \
    --path 'node_modules/' \
    --path-glob '**/venv/**' \
    --path-glob '**/dist/**' \
    --path-glob '**/node_modules/**' \
    --path 'docs/generated/api-data.json' \
    --path 'docs/generated/generated/api-data.json' \
    --path 'docs/generated/api/python.md' \
    --path 'docs/generated/generated/cross-language-comparison.md' \
    --path 'docs/generated/cross-language-comparison.md' \
    --path-glob '**/esm-go' \
    --path-glob '**/esm-format-go' \
    --force

echo ""
echo "=== History rewrite complete ==="
echo ""
echo "=== Post-filter repository size ==="
git count-objects -vH
echo ""
echo "Next steps:"
echo "  1. Review the rewritten history: git log --oneline | head -20"
echo "  2. Verify no large blobs remain:"
echo "     git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectsize) %(objectname) %(rest)' | awk '\$1==\"blob\" && \$2>1000000' | sort -k2 -rn | head -10"
echo "  3. Add the remote back (filter-repo removes it):"
echo "     git remote add origin <repo-url>"
echo "  4. Force push ALL branches:"
echo "     git push --force --all origin"
echo "  5. Force push tags:"
echo "     git push --force --tags origin"
echo "  6. All collaborators must re-clone or run:"
echo "     git fetch origin && git reset --hard origin/main"
