"""
Expression substitution and structural operations module.

This module provides functions for working with ESM format expressions:
- Variable substitution with scoped reference support
- Free variable analysis
- Expression evaluation with variable bindings
- Expression simplification through constant folding

All operations are non-mutating and return new Expr objects.
"""

# ========================================
# 1. Variable Substitution
# ========================================

"""
    substitute(expr::Expr, bindings::Dict{String,Expr})::Expr

Recursively replace variables in an expression with provided bindings.
Supports scoped reference resolution - if a variable is not found in bindings,
it remains unchanged. Returns a new Expr object (non-mutating).

# Arguments
- `expr`: The expression to perform substitution on
- `bindings`: Dictionary mapping variable names to replacement expressions

# Examples
```julia
# Simple substitution
x = VarExpr("x")
y = VarExpr("y")
sum_expr = OpExpr("+", [x, y])
bindings = Dict("x" => NumExpr(2.0))
result = substitute(sum_expr, bindings)  # OpExpr("+", [NumExpr(2.0), VarExpr("y")])

# Nested substitution
nested = OpExpr("*", [OpExpr("+", [x, NumExpr(1.0)]), y])
result = substitute(nested, bindings)  # OpExpr("*", [OpExpr("+", [NumExpr(2.0), NumExpr(1.0)]), VarExpr("y")])
```
"""
function substitute(expr::NumExpr, bindings::Dict{String,Expr})::Expr
    return expr  # Numeric literals are unchanged
end

function substitute(expr::IntExpr, bindings::Dict{String,Expr})::Expr
    return expr  # Integer literals are unchanged
end

function substitute(expr::VarExpr, bindings::Dict{String,Expr})::Expr
    return get(bindings, expr.name, expr)  # Replace if bound, otherwise keep original
end

function substitute(expr::OpExpr, bindings::Dict{String,Expr})::Expr
    # Recursively substitute arguments
    new_args = Expr[substitute(arg, bindings) for arg in expr.args]
    return OpExpr(expr.op, new_args, wrt=expr.wrt, dim=expr.dim)
end

# ========================================
# 2. Free Variable Analysis
# ========================================

"""
    free_variables(expr::Expr)::Set{String}

Extract all free (unbound) variable names from an expression.
Returns a set of variable names that appear in the expression.

# Examples
```julia
x = VarExpr("x")
y = VarExpr("y")
sum_expr = OpExpr("+", [x, y])
vars = free_variables(sum_expr)  # Set(["x", "y"])

nested = OpExpr("*", [OpExpr("+", [x, NumExpr(1.0)]), y])
vars = free_variables(nested)  # Set(["x", "y"])
```
"""
function free_variables(expr::NumExpr)::Set{String}
    return Set{String}()  # No variables in numeric literals
end

function free_variables(expr::IntExpr)::Set{String}
    return Set{String}()  # No variables in integer literals
end

function free_variables(expr::VarExpr)::Set{String}
    return Set([expr.name])  # Single variable
end

function free_variables(expr::OpExpr)::Set{String}
    # Union of free variables from all arguments
    result = Set{String}()
    for arg in expr.args
        union!(result, free_variables(arg))
    end

    # Add variables from wrt field if present
    if expr.wrt !== nothing
        push!(result, expr.wrt)
    end

    return result
end

# ========================================
# 3. Variable Containment Check
# ========================================

"""
    contains(expr::Expr, var::String)::Bool

Check if an expression contains a specific variable name.
Returns true if the variable appears anywhere in the expression.

# Examples
```julia
x = VarExpr("x")
y = VarExpr("y")
sum_expr = OpExpr("+", [x, y])
contains(sum_expr, "x")  # true
contains(sum_expr, "z")  # false
```
"""
function contains(expr::IntExpr, var::String)::Bool
    return false  # Integer literals don't contain variables
end

function contains(expr::NumExpr, var::String)::Bool
    return false  # Numeric literals don't contain variables
end

function contains(expr::VarExpr, var::String)::Bool
    return expr.name == var
end

function contains(expr::OpExpr, var::String)::Bool
    # Check if any argument contains the variable
    for arg in expr.args
        if contains(arg, var)
            return true
        end
    end

    # Check wrt field
    if expr.wrt !== nothing && expr.wrt == var
        return true
    end

    return false
end

# ========================================
# 4. Expression Evaluation
# ========================================

"""
    UnboundVariableError

Exception thrown when trying to evaluate an expression with unbound variables.
"""
struct UnboundVariableError <: Exception
    variable_name::String
    message::String
end

Base.show(io::IO, e::UnboundVariableError) = print(io, "UnboundVariableError: $(e.message)")

"""
    evaluate(expr::Expr, bindings::Dict{String,Float64})::Float64

Numerically evaluate an expression using provided variable bindings.
Throws UnboundVariableError if any variable is not found in bindings.

# Arguments
- `expr`: The expression to evaluate
- `bindings`: Dictionary mapping variable names to numeric values

# Examples
```julia
x = VarExpr("x")
y = VarExpr("y")
sum_expr = OpExpr("+", [x, y])
bindings = Dict("x" => 2.0, "y" => 3.0)
result = evaluate(sum_expr, bindings)  # 5.0
```

# Supported Operations
- Arithmetic: "+", "-", "*", "/", "^"
- Mathematical functions: "sin", "cos", "tan", "exp", "log", "sqrt", "abs"
- Constants: "π", "e"
"""
function evaluate(expr::NumExpr, bindings::Dict{String,Float64})::Float64
    return expr.value
end

function evaluate(expr::IntExpr, bindings::Dict{String,Float64})::Float64
    # Integer literals promote to Float64 at evaluation time only (RFC §5.4.1:
    # "Promotion happens only in evaluate, not in simplify/canonicalize").
    return Float64(expr.value)
end

"""
    _extract_const_array(arg::Expr, fname::String) -> AbstractVector

Extract the inline array from a `const`-op AST node, without numeric
evaluation. Used by closed functions (`interp.searchsorted`) whose array
argument arrives as `{op: "const", value: [...]}` and would otherwise be
collapsed to a scalar by the recursive `evaluate` walk.
"""
function _extract_const_array(arg::Expr, fname::String)::AbstractVector
    if arg isa OpExpr && arg.op == "const" && arg.value isa AbstractVector
        return arg.value
    end
    throw(ArgumentError("$(fname): array argument must be a `const`-op AST node carrying " *
                        "an inline array (got $(typeof(arg)))"))
end

function evaluate(expr::VarExpr, bindings::Dict{String,Float64})::Float64
    if !haskey(bindings, expr.name)
        throw(UnboundVariableError(expr.name, "Variable '$(expr.name)' not found in bindings"))
    end
    return bindings[expr.name]
end

function evaluate(expr::OpExpr, bindings::Dict{String,Float64})::Float64
    op = expr.op

    # ============================================================
    # Closed function registry (esm-spec §9.2 / esm-tzp)
    # ============================================================
    if op == "fn"
        fname = expr.name
        if fname === nothing
            throw(ArgumentError("`fn` op missing required `name` field (esm-spec §4.4)"))
        end
        # `interp.searchsorted` takes an array as its second argument; the
        # array MUST arrive as a `const`-op AST node and is extracted without
        # numeric evaluation.
        if fname == "interp.searchsorted"
            if length(expr.args) != 2
                throw(ClosedFunctionError("closed_function_arity",
                    "interp.searchsorted expects 2 arguments, got $(length(expr.args))"))
            end
            x_val = evaluate(expr.args[1], bindings)
            xs = _extract_const_array(expr.args[2], "interp.searchsorted")
            return Float64(evaluate_closed_function(fname, Any[x_val, xs]))
        elseif fname == "interp.linear"
            # `interp.linear(table, axis, x)` — table and axis arrive as
            # `const`-op AST nodes carrying inline arrays; only the scalar
            # query argument is recursively evaluated. Extracting the arrays
            # bypasses the scalar `const` evaluation path that would otherwise
            # try to coerce the array to Float64.
            if length(expr.args) != 3
                throw(ClosedFunctionError("closed_function_arity",
                    "interp.linear expects 3 arguments, got $(length(expr.args))"))
            end
            table = _extract_const_array(expr.args[1], "interp.linear")
            axis  = _extract_const_array(expr.args[2], "interp.linear")
            x_val = evaluate(expr.args[3], bindings)
            return Float64(evaluate_closed_function(fname, Any[table, axis, x_val]))
        elseif fname == "interp.bilinear"
            # `interp.bilinear(table, axis_x, axis_y, x, y)` — table is a
            # nested `const`-op array (Vector of Vectors); axes are flat
            # `const`-op arrays; x, y are scalar.
            if length(expr.args) != 5
                throw(ClosedFunctionError("closed_function_arity",
                    "interp.bilinear expects 5 arguments, got $(length(expr.args))"))
            end
            table  = _extract_const_array(expr.args[1], "interp.bilinear")
            axis_x = _extract_const_array(expr.args[2], "interp.bilinear")
            axis_y = _extract_const_array(expr.args[3], "interp.bilinear")
            x_val  = evaluate(expr.args[4], bindings)
            y_val  = evaluate(expr.args[5], bindings)
            return Float64(evaluate_closed_function(fname,
                Any[table, axis_x, axis_y, x_val, y_val]))
        end
        evaluated = Any[evaluate(a, bindings) for a in expr.args]
        result = evaluate_closed_function(fname, evaluated)
        return Float64(result)
    end

    # `const` ops carry inline literal values; for scalar consts the value is
    # numeric and returned directly. Non-scalar consts are only valid as
    # arguments to ops that consume arrays (`interp.searchsorted`, `index`),
    # which extract the array via `_extract_const_array` above without going
    # through this scalar path.
    if op == "const"
        v = expr.value
        if v isa Real && !(v isa Bool)
            return Float64(v)
        end
        throw(ArgumentError("`const` op with non-scalar value cannot be evaluated as Float64; " *
                            "non-scalar consts are valid only as array arguments to specific ops"))
    end

    # `enum` ops MUST be lowered to `const` integers before evaluation
    # (esm-spec §9.3 / `lower_enums!` in registered_functions.jl).
    if op == "enum"
        throw(ArgumentError("`enum` op encountered during evaluation; expected `lower_enums!` to have replaced it with a `const` integer (esm-spec §9.3)"))
    end

    args = [evaluate(arg, bindings) for arg in expr.args]


    # Arithmetic operators
    if op == "+"
        if length(args) == 1
            return args[1]  # Unary plus
        elseif length(args) == 2
            return args[1] + args[2]
        else
            return sum(args)  # n-ary addition
        end
    elseif op == "-"
        if length(args) == 1
            return -args[1]  # Unary minus
        elseif length(args) == 2
            return args[1] - args[2]
        else
            throw(ArgumentError("Subtraction requires 1 or 2 arguments, got $(length(args))"))
        end
    elseif op == "*"
        if length(args) == 1
            return args[1]
        elseif length(args) == 2
            return args[1] * args[2]
        else
            return prod(args)  # n-ary multiplication
        end
    elseif op == "/"
        if length(args) == 2
            if args[2] == 0.0
                throw(DivideError())
            end
            return args[1] / args[2]
        else
            throw(ArgumentError("Division requires exactly 2 arguments, got $(length(args))"))
        end
    elseif op == "^"
        if length(args) == 2
            return args[1] ^ args[2]
        else
            throw(ArgumentError("Exponentiation requires exactly 2 arguments, got $(length(args))"))
        end

    # Mathematical functions
    elseif op == "sin"
        if length(args) == 1
            return sin(args[1])
        else
            throw(ArgumentError("sin requires exactly 1 argument, got $(length(args))"))
        end
    elseif op == "cos"
        if length(args) == 1
            return cos(args[1])
        else
            throw(ArgumentError("cos requires exactly 1 argument, got $(length(args))"))
        end
    elseif op == "tan"
        if length(args) == 1
            return tan(args[1])
        else
            throw(ArgumentError("tan requires exactly 1 argument, got $(length(args))"))
        end
    elseif op == "exp"
        if length(args) == 1
            return exp(args[1])
        else
            throw(ArgumentError("exp requires exactly 1 argument, got $(length(args))"))
        end
    elseif op == "log"
        if length(args) == 1
            if args[1] <= 0.0
                throw(DomainError(args[1], "log argument must be positive"))
            end
            return log(args[1])
        else
            throw(ArgumentError("log requires exactly 1 argument, got $(length(args))"))
        end
    elseif op == "sqrt"
        if length(args) == 1
            if args[1] < 0.0
                throw(DomainError(args[1], "sqrt argument must be non-negative"))
            end
            return sqrt(args[1])
        else
            throw(ArgumentError("sqrt requires exactly 1 argument, got $(length(args))"))
        end
    elseif op == "abs"
        if length(args) == 1
            return abs(args[1])
        else
            throw(ArgumentError("abs requires exactly 1 argument, got $(length(args))"))
        end

    # Constants (handled as zero-argument functions)
    elseif op == "π" || op == "pi"
        if length(args) == 0
            return π
        else
            throw(ArgumentError("π constant takes no arguments, got $(length(args))"))
        end
    elseif op == "e"
        if length(args) == 0
            return ℯ
        else
            throw(ArgumentError("e constant takes no arguments, got $(length(args))"))
        end

    else
        throw(ArgumentError("Unsupported operator: $op"))
    end
end

# ========================================
# 5. Expression Simplification
# ========================================

"""
    simplify(expr::Expr)::Expr

Perform constant folding and algebraic simplification on an expression.
Returns a new simplified Expr object (non-mutating).

# Simplification Rules
- Constant folding: `2 + 3` → `5`
- Additive identity: `x + 0` → `x`, `0 + x` → `x`
- Multiplicative identity: `x * 1` → `x`, `1 * x` → `x`
- Multiplicative zero: `x * 0` → `0`, `0 * x` → `0`
- Exponentiation: `x^0` → `1`, `x^1` → `x`

# Examples
```julia
# Constant folding
expr = OpExpr("+", [NumExpr(2.0), NumExpr(3.0)])
result = simplify(expr)  # NumExpr(5.0)

# Identity elimination
expr = OpExpr("*", [VarExpr("x"), NumExpr(1.0)])
result = simplify(expr)  # VarExpr("x")
```
"""
function simplify(expr::NumExpr)::Expr
    return expr  # Already simplified
end

function simplify(expr::IntExpr)::Expr
    return expr  # Already simplified
end

function simplify(expr::VarExpr)::Expr
    return expr  # Already simplified
end

"""
    is_literal(expr::Expr)::Bool

True iff `expr` is a numeric literal (either integer or float node).
"""
is_literal(expr::Expr)::Bool = isa(expr, NumExpr) || isa(expr, IntExpr)

"""
    literal_value(expr::Expr)

Return the numeric value of a literal node, as `Float64`. Throws on non-literals.
"""
literal_value(expr::NumExpr) = expr.value
literal_value(expr::IntExpr) = Float64(expr.value)

function simplify(expr::OpExpr)::Expr
    # First recursively simplify all arguments
    simplified_args = Expr[simplify(arg) for arg in expr.args]

    op = expr.op

    # Try constant folding first - if all arguments are numeric, evaluate.
    # Per RFC §5.4.1, promotion happens only in evaluate, not simplify;
    # so when mixed int/float inputs fold, the result is a float literal.
    # When all inputs are integer, preserve integer result (for ops whose
    # integer result is representable — fall back to float on non-integer).
    if all(is_literal, simplified_args)
        try
            bindings = Dict{String,Float64}()
            result_value = evaluate(OpExpr(op, simplified_args, wrt=expr.wrt, dim=expr.dim), bindings)
            all_int = all(arg -> isa(arg, IntExpr), simplified_args)
            if all_int && isfinite(result_value) && result_value == trunc(result_value) &&
               abs(result_value) <= Float64(typemax(Int64))
                return IntExpr(Int64(result_value))
            end
            return NumExpr(result_value)
        catch
            # If evaluation fails, continue with algebraic simplification
        end
    end

    # Helper: true when arg is a numeric literal equal to v (compared by value).
    is_lit_val(arg, v) = (isa(arg, NumExpr) && arg.value == v) ||
                         (isa(arg, IntExpr) && Float64(arg.value) == v)

    # Algebraic simplification rules
    if op == "+"
        # Remove zeros: x + 0 = x, 0 + x = x
        non_zero_args = filter(arg -> !is_lit_val(arg, 0.0), simplified_args)
        if length(non_zero_args) == 0
            return NumExpr(0.0)
        elseif length(non_zero_args) == 1
            return non_zero_args[1]
        else
            return OpExpr(op, Expr[non_zero_args...], wrt=expr.wrt, dim=expr.dim)
        end

    elseif op == "*"
        # Check for zeros: x * 0 = 0, 0 * x = 0
        for arg in simplified_args
            if is_lit_val(arg, 0.0)
                return NumExpr(0.0)
            end
        end

        # Remove ones: x * 1 = x, 1 * x = x
        non_one_args = filter(arg -> !is_lit_val(arg, 1.0), simplified_args)
        if length(non_one_args) == 0
            return NumExpr(1.0)
        elseif length(non_one_args) == 1
            return non_one_args[1]
        else
            return OpExpr(op, Expr[non_one_args...], wrt=expr.wrt, dim=expr.dim)
        end

    elseif op == "^" && length(simplified_args) == 2
        base = simplified_args[1]
        exponent = simplified_args[2]

        # x^0 = 1
        if is_lit_val(exponent, 0.0)
            return NumExpr(1.0)
        end

        # x^1 = x
        if is_lit_val(exponent, 1.0)
            return base
        end

        # 0^x = 0 (for x > 0)
        if is_lit_val(base, 0.0) && is_literal(exponent) && literal_value(exponent) > 0.0
            return NumExpr(0.0)
        end

        # 1^x = 1
        if is_lit_val(base, 1.0)
            return NumExpr(1.0)
        end

        return OpExpr(op, simplified_args, wrt=expr.wrt, dim=expr.dim)

    elseif op == "-" && length(simplified_args) == 2
        # x - 0 = x
        if is_lit_val(simplified_args[2], 0.0)
            return simplified_args[1]
        end

        return OpExpr(op, simplified_args, wrt=expr.wrt, dim=expr.dim)

    elseif op == "/" && length(simplified_args) == 2
        # x / 1 = x
        if is_lit_val(simplified_args[2], 1.0)
            return simplified_args[1]
        end

        # 0 / x = 0 (for x != 0)
        if isa(simplified_args[1], NumExpr) && simplified_args[1].value == 0.0
            return NumExpr(0.0)
        end

        return OpExpr(op, simplified_args, wrt=expr.wrt, dim=expr.dim)
    end

    # If no simplification rules apply, return the expression with simplified arguments
    return OpExpr(op, simplified_args, wrt=expr.wrt, dim=expr.dim)
end