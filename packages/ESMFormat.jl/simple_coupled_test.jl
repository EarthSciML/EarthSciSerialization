#!/usr/bin/env julia

"""
Simple test for the coupled system functionality
"""

using ESMFormat

println("Testing to_coupled_system...")

# Create simple test models
model1_vars = Dict{String,ModelVariable}(
    "x" => ModelVariable(StateVariable; default=1.0, description="Concentration"),
    "k" => ModelVariable(ParameterVariable; default=0.1, description="Decay rate")
)

model1_eqs = [
    Equation(
        OpExpr("D", ESMFormat.Expr[VarExpr("x")], wrt="t"),
        OpExpr("*", ESMFormat.Expr[OpExpr("-", ESMFormat.Expr[VarExpr("k")]), VarExpr("x")])
    )
]

model1 = Model(model1_vars, model1_eqs)

# Create test ESM file with coupling
metadata = Metadata("Test Coupled System")
models = Dict("Model1" => model1)

coupling_entries = [
    CouplingOperatorCompose(["Model1", "Model1"]; description="Test self-composition")
]

esm_file = EsmFile("1.0", metadata; models=models, coupling=coupling_entries)

# Test the main function
coupled_system = to_coupled_system(esm_file)

println("✅ SUCCESS!")
println("Created coupled system with $(length(coupled_system.systems)) systems")
println("Applied $(length(coupled_system.couplings)) coupling rules")
println("System names: $(keys(coupled_system.systems))")