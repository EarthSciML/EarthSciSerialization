# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->


## Build & Test

See [CONTRIBUTING.md](CONTRIBUTING.md) for full setup and [CONFORMANCE_SPEC.md](CONFORMANCE_SPEC.md) for cross-language conformance details.

```bash
# Cross-language conformance tests (all languages)
./scripts/test-conformance.sh

# Individual language tests
julia --project=. -e 'using Pkg; Pkg.test()'                       # Julia
cd packages/earthsci-toolkit && npm test                            # TypeScript
cd packages/earthsci_toolkit && python3 -m pytest tests/ -v         # Python
cd packages/earthsci-toolkit-rs && cargo test                       # Rust
cd packages/esm-format-go && go test ./...                          # Go

# Dependency management
./scripts/deps install   # Install all dependencies
./scripts/deps check     # Verify dependencies
```

## Architecture Overview

EarthSciSerialization is a language-agnostic JSON format for earth science model components, defined by `esm-schema.json` and documented in `esm-spec.md`. Language implementations live under `packages/`:

- **EarthSciSerialization.jl** — Julia reference implementation (MTK/Catalyst integration)
- **earthsci-toolkit** — TypeScript types and utilities
- **earthsci_toolkit** — Python scientific integration
- **earthsci-toolkit-rs** — Rust high-performance implementation
- **esm-format-go** — Go lightweight implementation
- **esm-editor** — SolidJS interactive web editor

Shared test fixtures in `tests/` (valid, invalid, conformance) ensure cross-language consistency.

## Conventions & Patterns

- Follow conventional commits: `type(scope): description` (e.g. `feat(julia): add expression support`)
- All implementations must conform to `esm-schema.json` and pass `./scripts/test-conformance.sh`
- Follow each language's idiomatic style (see [CONTRIBUTING.md](CONTRIBUTING.md#language-specific-standards))
