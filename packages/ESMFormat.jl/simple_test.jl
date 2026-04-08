#!/usr/bin/env julia

# Simple test without precompilation issues

println("Testing ESM types only (no MTK/Catalyst)...")

# Load just our package
push!(LOAD_PATH, "src")
include("src/types.jl")

println("Creating basic ESM expressions...")

# Test basic expression types
num_expr = NumExpr(42.0)
var_expr = VarExpr("x")
op_expr = OpExpr("+", [var_expr, num_expr])

println("✓ NumExpr: $num_expr")
println("✓ VarExpr: $var_expr")
println("✓ OpExpr: $op_expr")

# Test model creation
println("\nCreating ESM model...")

variables = Dict{String,ModelVariable}(
    "x" => ModelVariable(StateVariable; default=1.0),
    "k" => ModelVariable(ParameterVariable; default=0.5)
)

equations = [
    Equation(
        OpExpr("D", Expr[VarExpr("x")], wrt="t"),
        OpExpr("*", Expr[OpExpr("-", Expr[VarExpr("k")]), VarExpr("x")])
    )
]

model = Model(variables, equations)
println("✓ Model created with $(length(model.variables)) variables and $(length(model.equations)) equations")

# Test reaction system
println("\nCreating ESM reaction system...")

species = [Species("A"), Species("B")]
parameters = [Parameter("k", 1.0)]
reactions = [
    Reaction(Dict("A" => 1), Dict("B" => 1), VarExpr("k"))
]

rsys = ReactionSystem(species, reactions; parameters=parameters)
println("✓ ReactionSystem created with $(length(rsys.species)) species and $(length(rsys.reactions)) reactions")

println("\nBasic ESM types working correctly!")