# Tests for the run_esm_tests walker (src/run_tests.jl, esm-ol5qa).
#
# Covers: discover_esm_files, run_esm_tests PASS/FAIL/exit_code paths, the
# model-relative fallback in _resolve_handle (spec §10.7 subsystem refs), and
# JUnit XML emission.
using Test
using EarthSciSerialization
import ModelingToolkit
import OrdinaryDiffEqTsit5

const _inline_dir = joinpath(@__DIR__, "fixtures", "inline_tests")

@testset "run_esm_tests walker (esm-ol5qa)" begin

    @testset "discover_esm_files" begin
        found = discover_esm_files([_inline_dir])
        @test length(found) == 3
        @test all(endswith(f, ".esm") for f in found)
        @test issorted(found)
    end

    @testset "discover_esm_files honours exclude" begin
        kw = discover_esm_files([_inline_dir]; exclude=["failing_decay"])
        @test length(kw) == 2
        @test any(endswith(f, "passing_decay.esm") for f in kw)
        @test any(endswith(f, "subsystem_composed_decay.esm") for f in kw)

        prev = get(ENV, "ESM_TESTS_EXCLUDE", nothing)
        try
            ENV["ESM_TESTS_EXCLUDE"] = "failing_decay.esm"
            envf = discover_esm_files([_inline_dir])
            @test length(envf) == 2
            @test any(endswith(f, "passing_decay.esm") for f in envf)
        finally
            if prev === nothing
                delete!(ENV, "ESM_TESTS_EXCLUDE")
            else
                ENV["ESM_TESTS_EXCLUDE"] = prev
            end
        end
    end

    @testset "passing fixture → all PASS" begin
        passing = joinpath(_inline_dir, "passing_decay.esm")
        results, exit_code = run_esm_tests([_inline_dir];
                                            verbose=false,
                                            exclude=["failing_decay",
                                                     "subsystem_composed"])
        passing_results = filter(r -> r.file == passing, results)
        @test !isempty(passing_results)
        @test all(r -> r.status == EarthSciSerialization.PASS, passing_results)
        @test exit_code == 0
    end

    @testset "failing fixture → reports FAIL, exit_code != 0" begin
        failing = joinpath(_inline_dir, "failing_decay.esm")
        results, exit_code = run_esm_tests([_inline_dir];
                                            verbose=false,
                                            exclude=["passing_decay",
                                                     "subsystem_composed"])
        failing_results = filter(r -> r.file == failing, results)
        @test !isempty(failing_results)
        @test any(r -> r.status == EarthSciSerialization.FAIL, failing_results)
        @test exit_code != 0
    end

    @testset "subsystem-composed fixture → all PASS (esm-ol5qa)" begin
        # Exercises the model-relative fallback in _resolve_handle: assertions
        # and parameter_overrides use spec §10.7 fully-qualified refs of the
        # form "ModelName.sub.var", which MTK exposes as the model-relative
        # "sub_var" property (stripping the system-name prefix).
        results, exit_code = run_esm_tests([_inline_dir];
                                            verbose=false,
                                            exclude=["failing_decay",
                                                     "passing_decay"])
        @test !isempty(results)
        @test all(r -> r.status == EarthSciSerialization.PASS, results)
        @test exit_code == 0
    end

    @testset "junit XML emission" begin
        mktempdir() do tmp
            xml_path = joinpath(tmp, "report.xml")
            results, _ = run_esm_tests([_inline_dir];
                                        verbose=false, junit_xml=xml_path)
            @test isfile(xml_path)
            content = read(xml_path, String)
            @test occursin("<testsuites", content)
            @test occursin("FailingDecay", content)
            @test occursin("<failure", content)
        end
    end

end
