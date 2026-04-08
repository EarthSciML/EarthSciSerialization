#!/usr/bin/env julia

# Quick test script for MTK/Catalyst conversion functionality
# Test without loading MTK/Catalyst to check basic functionality first

using ESMFormat

println("Testing basic ESM expression and model functionality...")

# Test basic expression creation
println("Creating basic expressions...")
try
    num_expr = NumExpr(42.0)
    var_expr = VarExpr("x")
    op_expr = OpExpr("+", ESMFormat.Expr[var_expr, num_expr])
    println("✓ Basic expressions created successfully")
    println("  NumExpr: $num_expr")
    println("  VarExpr: $var_expr")
    println("  OpExpr: $op_expr")
catch e
    println("✗ Error creating basic expressions: $e")
end

# Test model creation
println("\nCreating basic ESM model...")
try
    variables = Dict{String,ModelVariable}(
        "x" => ModelVariable(StateVariable; default=1.0, description="Position"),
        "k" => ModelVariable(ParameterVariable; default=0.5, description="Damping coefficient")
    )

    equations = [
        Equation(
            OpExpr("D", ESMFormat.Expr[VarExpr("x")], wrt="t"),
            OpExpr("*", ESMFormat.Expr[
                OpExpr("-", ESMFormat.Expr[VarExpr("k")]),
                VarExpr("x")
            ])
        )
    ]

    model = Model(variables, equations)
    println("✓ ESM model created successfully")
    println("  Variables: $(length(model.variables))")
    println("  Equations: $(length(model.equations))")
catch e
    println("✗ Error creating ESM model: $e")
end

# Test reaction system creation
println("\nCreating basic ESM reaction system...")
try
    species = [Species("A"), Species("B")]
    parameters = [Parameter("k", 1.0)]
    reactions = [
        Reaction(Dict("A" => 1), Dict("B" => 1), VarExpr("k"))
    ]

    rsys = ReactionSystem(species, reactions; parameters=parameters)
    println("✓ ESM reaction system created successfully")
    println("  Species: $(length(rsys.species))")
    println("  Reactions: $(length(rsys.reactions))")
    println("  Parameters: $(length(rsys.parameters))")
catch e
    println("✗ Error creating ESM reaction system: $e")
end

# Now test MTK/Catalyst functions - but expect they might fail initially
println("\nTesting MTK/Catalyst conversion functions...")

# Try MTK conversion
println("Testing ESM -> MTK conversion...")
try
    variables = Dict{String,ModelVariable}(
        "x" => ModelVariable(StateVariable; default=1.0)
    )
    equations = [
        Equation(OpExpr("D", ESMFormat.Expr[VarExpr("x")], wrt="t"), VarExpr("x"))
    ]
    model = Model(variables, equations)

    println("Attempting to_mtk_system...")
    mtk_sys = to_mtk_system(model, "TestModel")
    println("✓ MTK system created: $(typeof(mtk_sys))")

    println("Attempting from_mtk_system...")
    recovered = from_mtk_system(mtk_sys, "TestModel")
    println("✓ Round-trip successful")

catch e
    println("✗ MTK conversion error: $e")
end

# Try Catalyst conversion
println("Testing ESM -> Catalyst conversion...")
try
    species = [Species("A")]
    reactions = [Reaction(Dict("A" => 1), Dict{String,Int}(), VarExpr("k"))]
    rsys = ReactionSystem(species, reactions)

    println("Attempting to_catalyst_system...")
    cat_sys = to_catalyst_system(rsys, "TestRxn")
    println("✓ Catalyst system created: $(typeof(cat_sys))")

    println("Attempting from_catalyst_system...")
    recovered = from_catalyst_system(cat_sys, "TestRxn")
    println("✓ Round-trip successful")

catch e
    println("✗ Catalyst conversion error: $e")
end

println("\nBasic functionality test completed!")