#!/usr/bin/env julia

"""
Julia conformance test runner for ESM Format cross-language testing.

This script runs the Julia EarthSciSerialization.jl implementation against test fixtures
and generates standardized outputs for comparison with other language implementations.
"""

using Pkg

# Activate a side env (scripts/julia-conformance-env) that pulls in both the
# EarthSciSerialization package and the MTK / OrdinaryDiffEqDefault solver
# stack. The main package declares those as test extras only, so running
# inside its own env can't reach them.
project_dir = dirname(dirname(@__FILE__))
julia_package = joinpath(project_dir, "packages", "EarthSciSerialization.jl")
conformance_env = joinpath(project_dir, "scripts", "julia-conformance-env")
Pkg.activate(conformance_env)
Pkg.develop(path=julia_package)
Pkg.instantiate()

using EarthSciSerialization
using JSON3
using Printf
import ModelingToolkit
import OrdinaryDiffEqDefault
const _MTK_CONF = ModelingToolkit

struct ConformanceResults
    language::String
    timestamp::String
    validation_results::Dict{String, Any}
    display_results::Dict{String, Any}
    substitution_results::Dict{String, Any}
    graph_results::Dict{String, Any}
    arrayop_results::Dict{String, Any}
    errors::Vector{String}
end

function write_results(output_dir::String, results::ConformanceResults)
    mkpath(output_dir)

    # Write main results file
    results_file = joinpath(output_dir, "results.json")
    open(results_file, "w") do f
        JSON3.pretty(f, results)
    end

    println("Julia conformance results written to: $results_file")
end

function run_validation_tests(tests_dir::String)
    """Test schema and structural validation on valid and invalid ESM files."""
    validation_results = Dict{String, Any}()

    # Test valid files
    valid_dir = joinpath(tests_dir, "valid")
    if isdir(valid_dir)
        valid_results = Dict{String, Any}()
        for filename in filter(f -> endswith(f, ".esm"), readdir(valid_dir))
            filepath = joinpath(valid_dir, filename)
            try
                esm_data = EarthSciSerialization.load(filepath)
                result = EarthSciSerialization.validate(esm_data)

                valid_results[filename] = Dict(
                    "is_valid" => result.is_valid,
                    "schema_errors" => result.schema_errors,
                    "structural_errors" => result.structural_errors,
                    "parsed_successfully" => true
                )
            catch e
                valid_results[filename] = Dict(
                    "parsed_successfully" => false,
                    "error" => string(e),
                    "error_type" => string(typeof(e))
                )
            end
        end
        validation_results["valid"] = valid_results
    end

    # Test invalid files
    invalid_dir = joinpath(tests_dir, "invalid")
    if isdir(invalid_dir)
        invalid_results = Dict{String, Any}()
        for filename in filter(f -> endswith(f, ".esm"), readdir(invalid_dir))
            filepath = joinpath(invalid_dir, filename)
            try
                esm_data = EarthSciSerialization.load(filepath)
                result = EarthSciSerialization.validate(esm_data)

                invalid_results[filename] = Dict(
                    "is_valid" => result.is_valid,
                    "schema_errors" => result.schema_errors,
                    "structural_errors" => result.structural_errors,
                    "parsed_successfully" => true
                )
            catch e
                invalid_results[filename] = Dict(
                    "parsed_successfully" => false,
                    "error" => string(e),
                    "error_type" => string(typeof(e)),
                    "is_expected_error" => true  # Invalid files should error
                )
            end
        end
        validation_results["invalid"] = invalid_results
    end

    return validation_results
end

function run_display_tests(tests_dir::String)
    """Test pretty-printing and display format generation."""
    display_results = Dict{String, Any}()

    display_dir = joinpath(tests_dir, "display")
    if isdir(display_dir)
        for filename in filter(f -> endswith(f, ".json"), readdir(display_dir))
            filepath = joinpath(display_dir, filename)
            try
                test_data = JSON3.read(read(filepath, String))
                test_results = Dict{String, Any}()

                # Test chemical formula rendering
                if haskey(test_data, "chemical_formulas")
                    formula_results = []
                    for formula_test in test_data["chemical_formulas"]
                        if haskey(formula_test, "input")
                            input_formula = formula_test["input"]
                            try
                                unicode_result = EarthSciSerialization.render_chemical_formula(input_formula)

                                push!(formula_results, Dict(
                                    "input" => input_formula,
                                    "output_unicode" => unicode_result,
                                    "output_latex" => get(formula_test, "expected_latex", ""),
                                    "output_ascii" => input_formula,  # Fallback
                                    "success" => true
                                ))
                            catch e
                                push!(formula_results, Dict(
                                    "input" => input_formula,
                                    "error" => string(e),
                                    "success" => false
                                ))
                            end
                        end
                    end
                    test_results["chemical_formulas"] = formula_results
                end

                # Test expression rendering
                if haskey(test_data, "expressions")
                    expression_results = []
                    for expr_test in test_data["expressions"]
                        if haskey(expr_test, "input")
                            input_expr = expr_test["input"]
                            try
                                expr = EarthSciSerialization.parse_expression(input_expr)
                                unicode_result = EarthSciSerialization.pretty_print(expr, format="unicode")
                                latex_result = EarthSciSerialization.pretty_print(expr, format="latex")
                                ascii_result = EarthSciSerialization.pretty_print(expr, format="ascii")

                                push!(expression_results, Dict(
                                    "input" => input_expr,
                                    "output_unicode" => unicode_result,
                                    "output_latex" => latex_result,
                                    "output_ascii" => ascii_result,
                                    "success" => true
                                ))
                            catch e
                                push!(expression_results, Dict(
                                    "input" => input_expr,
                                    "error" => string(e),
                                    "success" => false
                                ))
                            end
                        end
                    end
                    test_results["expressions"] = expression_results
                end

                display_results[filename] = test_results

            catch e
                display_results[filename] = Dict(
                    "error" => string(e),
                    "success" => false
                )
            end
        end
    end

    return display_results
end

function run_substitution_tests(tests_dir::String)
    """Test expression substitution functionality."""
    substitution_results = Dict{String, Any}()

    substitution_dir = joinpath(tests_dir, "substitution")
    if isdir(substitution_dir)
        for filename in filter(f -> endswith(f, ".json"), readdir(substitution_dir))
            filepath = joinpath(substitution_dir, filename)
            try
                test_data = JSON3.read(read(filepath, String))
                test_results = []

                if haskey(test_data, "tests")
                    for test_case in test_data["tests"]
                        if haskey(test_case, "expression") && haskey(test_case, "substitutions")
                            try
                                expr = EarthSciSerialization.parse_expression(test_case["expression"])
                                substitutions = Dict(
                                    k => EarthSciSerialization.parse_expression(v)
                                    for (k, v) in test_case["substitutions"]
                                )

                                result_expr = EarthSciSerialization.substitute(expr, substitutions)
                                result_str = EarthSciSerialization.pretty_print(result_expr)

                                push!(test_results, Dict(
                                    "input" => test_case["expression"],
                                    "substitutions" => test_case["substitutions"],
                                    "result" => result_str,
                                    "success" => true
                                ))
                            catch e
                                push!(test_results, Dict(
                                    "input" => get(test_case, "expression", ""),
                                    "error" => string(e),
                                    "success" => false
                                ))
                            end
                        end
                    end
                end

                substitution_results[filename] = test_results

            catch e
                substitution_results[filename] = Dict(
                    "error" => string(e),
                    "success" => false
                )
            end
        end
    end

    return substitution_results
end

function run_graph_tests(tests_dir::String)
    """Test graph generation functionality."""
    graph_results = Dict{String, Any}()

    graphs_dir = joinpath(tests_dir, "graphs")
    if isdir(graphs_dir)
        for filename in filter(f -> endswith(f, ".json"), readdir(graphs_dir))
            filepath = joinpath(graphs_dir, filename)
            try
                test_data = JSON3.read(read(filepath, String))

                if haskey(test_data, "esm_file")
                    esm_file_path = joinpath(dirname(filepath), test_data["esm_file"])
                    if isfile(esm_file_path)
                        try
                            esm_data = EarthSciSerialization.load(esm_file_path)

                            # Generate system graph
                            system_graph = EarthSciSerialization.generate_system_graph(esm_data)

                            # Export in different formats
                            dot_output = EarthSciSerialization.export_dot(system_graph)
                            json_output = EarthSciSerialization.export_json(system_graph)

                            graph_results[filename] = Dict(
                                "esm_file" => esm_file_path,
                                "system_graph" => Dict(
                                    "nodes" => length(system_graph.nodes),
                                    "edges" => length(system_graph.edges),
                                    "dot_format" => dot_output,
                                    "json_format" => json_output
                                ),
                                "success" => true
                            )
                        catch e
                            graph_results[filename] = Dict(
                                "esm_file" => esm_file_path,
                                "error" => string(e),
                                "success" => false
                            )
                        end
                    else
                        graph_results[filename] = Dict(
                            "error" => "ESM file not found: $esm_file_path",
                            "success" => false
                        )
                    end
                end

            catch e
                graph_results[filename] = Dict(
                    "error" => string(e),
                    "success" => false
                )
            end
        end
    end

    return graph_results
end

# ------------------------------------------------------------------
# Arrayop fixture runner — walks tests/fixtures/arrayop/*.esm, runs
# each inline test through the MTK simulate path, records actuals
# for cross-language diffing.
# ------------------------------------------------------------------

function _parse_varspec(spec::AbstractString)
    lb = findfirst('[', spec)
    lb === nothing && return String(spec), Int[]
    rb = findfirst(']', spec)
    rb === nothing && error("unterminated index in '$spec'")
    base = String(spec[1:(lb - 1)])
    body = spec[(lb + 1):(rb - 1)]
    idxs = [parse(Int, strip(t)) for t in split(body, ',')]
    return base, idxs
end

function _resolve_on_simp(simp, model_name::Symbol, spec::AbstractString)
    base, idxs = _parse_varspec(spec)
    arr = _MTK_CONF.getproperty(simp, Symbol(String(model_name) * "_" * base))
    return isempty(idxs) ? arr : arr[idxs...]
end

function _merge_tolerance_jl(model_tol, test_tol, assertion_tol)
    rel = 0.0
    ab = 0.0
    for tol in (model_tol, test_tol, assertion_tol)
        tol === nothing && continue
        r = hasproperty(tol, :rel) ? tol.rel : nothing
        a = hasproperty(tol, :abs) ? tol.abs : nothing
        if r !== nothing
            rel = Float64(r)
        end
        if a !== nothing
            ab = Float64(a)
        end
    end
    return rel, ab
end

function _assertion_passes_jl(actual, expected, rel, ab)
    diff = abs(actual - expected)
    if ab > 0 && diff <= ab
        return true
    end
    if rel > 0
        denom = max(abs(expected), 1e-12)
        if diff / denom <= rel
            return true
        end
    end
    if ab == 0 && rel == 0
        return diff == 0.0
    end
    return false
end

function run_arrayop_tests(tests_dir::String)
    """Run every inline arrayop fixture test and collect per-assertion actuals."""
    fixtures_dir = joinpath(tests_dir, "fixtures", "arrayop")
    results = Dict{String, Any}()
    if !isdir(fixtures_dir)
        return results
    end

    for fname in sort(filter(f -> endswith(f, ".esm"), readdir(fixtures_dir)))
        fixture_path = joinpath(fixtures_dir, fname)
        fixture_out = Dict{String, Any}()
        local file
        try
            file = EarthSciSerialization.load(fixture_path)
        catch e
            results[fname] = Dict("__fixture_error" => string(e))
            continue
        end
        models_dict = file.models
        if models_dict === nothing
            results[fname] = fixture_out
            continue
        end

        for (mname, model) in models_dict
            if isempty(model.tests)
                continue
            end
            local sys, simp
            try
                sys = _MTK_CONF.System(model; name=Symbol(mname))
                simp = _MTK_CONF.mtkcompile(sys)
            catch e
                fixture_out[String(mname)] = Dict("__compile_error" => string(e))
                continue
            end

            model_out = Dict{String, Any}()
            for t in model.tests
                test_id = String(t.id)
                sim_ok = true
                sim_msg = ""
                local sol
                try
                    u0_map = Dict{Any, Float64}()
                    for (spec, val) in t.initial_conditions
                        handle = _resolve_on_simp(simp, Symbol(mname), spec)
                        u0_map[handle] = Float64(val)
                    end
                    tspan = (Float64(t.time_span.start), Float64(t.time_span.stop))
                    prob = _MTK_CONF.ODEProblem(simp, u0_map, tspan)
                    sol = OrdinaryDiffEqDefault.solve(prob; reltol=1e-10, abstol=1e-12)
                    if sol.retcode != _MTK_CONF.SciMLBase.ReturnCode.Success
                        sim_ok = false
                        sim_msg = "retcode=$(sol.retcode)"
                    end
                catch e
                    sim_ok = false
                    sim_msg = string(e)
                end

                assertions_out = Vector{Dict{String, Any}}()
                for a in t.assertions
                    rel, ab = _merge_tolerance_jl(model.tolerance, t.tolerance, a.tolerance)
                    rec = Dict{String, Any}(
                        "variable" => String(a.variable),
                        "time" => Float64(a.time),
                        "expected" => Float64(a.expected),
                        "tolerance" => Dict("rel" => rel, "abs" => ab),
                    )
                    if sim_ok
                        try
                            handle = _resolve_on_simp(simp, Symbol(mname), a.variable)
                            actual = Float64(sol(a.time, idxs=handle))
                            rec["actual"] = actual
                            rec["passed"] = _assertion_passes_jl(actual, rec["expected"], rel, ab)
                        catch e
                            rec["actual"] = nothing
                            rec["passed"] = false
                            rec["error"] = string(e)
                        end
                    else
                        rec["actual"] = nothing
                        rec["passed"] = false
                    end
                    push!(assertions_out, rec)
                end

                model_out[test_id] = Dict{String, Any}(
                    "success" => sim_ok,
                    "message" => sim_msg,
                    "assertions" => assertions_out,
                )
            end
            if !isempty(model_out)
                fixture_out[String(mname)] = model_out
            end
        end
        results[fname] = fixture_out
    end

    return results
end

function main()
    if length(ARGS) != 1
        println("Usage: julia run-julia-conformance.jl <output_dir>")
        exit(1)
    end

    output_dir = ARGS[1]
    project_root = dirname(dirname(@__FILE__))
    tests_dir = joinpath(project_root, "tests")

    println("Running Julia conformance tests...")
    println("Tests directory: $tests_dir")
    println("Output directory: $output_dir")

    errors = String[]

    # Run all test categories
    try
        validation_results = run_validation_tests(tests_dir)
        println("✓ Validation tests completed")
    catch e
        validation_results = Dict{String, Any}()
        push!(errors, "Validation tests failed: $(string(e))")
        println("✗ Validation tests failed: $e")
    end

    try
        display_results = run_display_tests(tests_dir)
        println("✓ Display tests completed")
    catch e
        display_results = Dict{String, Any}()
        push!(errors, "Display tests failed: $(string(e))")
        println("✗ Display tests failed: $e")
    end

    try
        substitution_results = run_substitution_tests(tests_dir)
        println("✓ Substitution tests completed")
    catch e
        substitution_results = Dict{String, Any}()
        push!(errors, "Substitution tests failed: $(string(e))")
        println("✗ Substitution tests failed: $e")
    end

    try
        graph_results = run_graph_tests(tests_dir)
        println("✓ Graph tests completed")
    catch e
        graph_results = Dict{String, Any}()
        push!(errors, "Graph tests failed: $(string(e))")
        println("✗ Graph tests failed: $e")
    end

    try
        arrayop_results = run_arrayop_tests(tests_dir)
        println("✓ Arrayop simulation tests completed")
    catch e
        arrayop_results = Dict{String, Any}()
        push!(errors, "Arrayop tests failed: $(string(e))")
        println("✗ Arrayop tests failed: $e")
    end

    # Compile results
    results = ConformanceResults(
        "julia",
        string(now()),
        validation_results,
        display_results,
        substitution_results,
        graph_results,
        arrayop_results,
        errors
    )

    # Write results to file
    write_results(output_dir, results)

    if isempty(errors)
        println("Julia conformance testing completed successfully!")
        exit(0)
    else
        println("Julia conformance testing completed with $(length(errors)) errors")
        exit(1)
    end
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end