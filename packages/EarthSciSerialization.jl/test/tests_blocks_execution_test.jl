# Execution runner for inline `tests` blocks (schema gt-cc1).
#
# The `tests/valid/tests_examples_comprehensive.esm` fixture exists for
# schema coverage of the inline `tests` / `examples` surface — parsing and
# round-trip only. This file closes the schema-vs-execution gap for the
# Julia reference binding: it walks every Model's inline `tests` list,
# builds the MTK system, applies `initial_conditions` and
# `parameter_overrides`, solves across the test's `time_span`, and
# verifies each `Assertion` against the resolved tolerance (assertion
# → test → model). Without this, a regression in the `tests`-block
# execution path outside of the arrayop-specific fixtures would pass CI.
using Test
using EarthSciSerialization
import ModelingToolkit
import OrdinaryDiffEqDefault

const _ESM_TB = EarthSciSerialization
const _MTK_TB = ModelingToolkit

# Resolve a local name ("N", "r", ...) against a compiled MTK system,
# searching unknowns first, then parameters. The flattener namespaces
# names as `Model.local`, which the MTK extension sanitizes to
# `Model_local`; we match either the exact name or the `_local` suffix.
function _find_sym(simp, system_name::Symbol, local_name::AbstractString)
    suffix = "_" * local_name
    for u in _MTK_TB.unknowns(simp)
        nm = string(_MTK_TB.getname(u))
        (nm == local_name || endswith(nm, suffix)) && return u
    end
    for p in _MTK_TB.parameters(simp)
        nm = string(_MTK_TB.getname(p))
        (nm == local_name || endswith(nm, suffix)) && return p
    end
    error("No symbol '$local_name' on compiled $(system_name) system " *
          "(unknowns=$(_MTK_TB.unknowns(simp)), " *
          "parameters=$(_MTK_TB.parameters(simp)))")
end

# Resolve (rel, abs) precedence: assertion-level wins, then test-level,
# then model-level. An unset field contributes 0. Falls back to rtol=1e-6
# when nothing is configured.
function _resolve_tol(model_tol, test_tol, assertion_tol)
    for cand in (assertion_tol, test_tol, model_tol)
        cand === nothing && continue
        r = cand.rel === nothing ? 0.0 : cand.rel
        a = cand.abs === nothing ? 0.0 : cand.abs
        return (r, a)
    end
    return (1.0e-6, 0.0)
end

function _run_one_test(simp, system_name::Symbol,
                       model_tol, t::_ESM_TB.Test)
    u0_map = Dict{Any,Float64}()
    for (name, val) in t.initial_conditions
        u0_map[_find_sym(simp, system_name, name)] = Float64(val)
    end
    p_map = Dict{Any,Float64}()
    for (name, val) in t.parameter_overrides
        p_map[_find_sym(simp, system_name, name)] = Float64(val)
    end

    tspan = (t.time_span.start, t.time_span.stop)
    # Current MTK prefers a single merged u0+p map; the 4-arg form is
    # deprecated. Merging is safe here because u0_map and p_map key off
    # disjoint symbolic handles (unknowns vs parameters).
    combined = Dict{Any,Float64}()
    for (k, v) in u0_map; combined[k] = v; end
    for (k, v) in p_map;  combined[k] = v; end
    prob = _MTK_TB.ODEProblem(simp, combined, tspan)
    sol = OrdinaryDiffEqDefault.solve(prob; reltol=1e-10, abstol=1e-12)
    @test sol.retcode == _MTK_TB.SciMLBase.ReturnCode.Success

    for a in t.assertions
        handle = _find_sym(simp, system_name, a.variable)
        rel, abs_ = _resolve_tol(model_tol, t.tolerance, a.tolerance)
        actual = sol(a.time, idxs=handle)
        if abs_ > 0 && iszero(a.expected)
            @test isapprox(actual, a.expected; atol=abs_)
        elseif rel > 0
            @test isapprox(actual, a.expected; rtol=rel, atol=abs_)
        else
            @test isapprox(actual, a.expected; atol=abs_)
        end
    end
end

@testset "Inline tests-block execution runner" begin
    fixture_path = joinpath(@__DIR__, "..", "..", "..",
                            "tests", "valid",
                            "tests_examples_comprehensive.esm")
    @test isfile(fixture_path)

    file = _ESM_TB.load(fixture_path)
    @test file.models !== nothing

    # Sanity: this runner targets Models with inline tests. The Julia
    # ReactionSystem type does not currently parse `tests`/`tolerance`
    # (tracked by the ReactionSystem-tests follow-up); that branch is
    # schema-only for now.
    any_tests = false
    for (mname, model) in file.models
        isempty(model.tests) && continue
        any_tests = true
        sys = _MTK_TB.System(model; name=Symbol(mname))
        simp = _MTK_TB.mtkcompile(sys)
        for t in model.tests
            @testset "$(mname)/$(t.id)" begin
                _run_one_test(simp, Symbol(mname), model.tolerance, t)
            end
        end
    end
    @test any_tests
end
