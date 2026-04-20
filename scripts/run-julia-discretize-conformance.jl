#!/usr/bin/env julia

# CI-integrable runner for the discretize conformance harness (gt-l3dg).
#
# Drives the same adapter as the Pkg.test() path but without needing the
# full EarthSciSerialization.jl test suite. Exits with a non-zero status
# on any mismatch so CI (and scripts/test-conformance.sh) picks up the
# failure immediately.
#
# Usage:
#   julia --project=packages/EarthSciSerialization.jl \
#     scripts/run-julia-discretize-conformance.jl [--update]
#
# Env vars:
#   UPDATE_DISCRETIZE_GOLDEN=1   # regenerate goldens instead of asserting

using Pkg

const _SCRIPT_DIR   = dirname(@__FILE__)
const _PROJECT_ROOT = normpath(joinpath(_SCRIPT_DIR, ".."))
const _JULIA_PKG    = joinpath(_PROJECT_ROOT, "packages", "EarthSciSerialization.jl")

cd(_JULIA_PKG)
Pkg.activate(".")

# The adapter ships as a test-suite file; re-use it via include so the
# canonical-emit and manifest-driving code has one source of truth.
using Test
include(joinpath(_JULIA_PKG, "test", "conformance_discretize_test.jl"))

# The @testset above runs on include. Exit code from `julia` already
# reflects success/failure of the test suite via the Test stdlib, but we
# make it explicit here for the CI runner.
Test.get_testset_depth() # no-op; presence asserts Test is loaded
