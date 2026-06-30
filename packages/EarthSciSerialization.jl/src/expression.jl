"""
Expression substitution and structural operations module.

This module provides functions for working with ESM format expressions:
- Variable substitution with scoped reference support
- Free variable analysis
- Expression simplification through constant folding

All operations are non-mutating and return new Expr objects.

Numerical evaluation lives in `tree_walk.jl` (`evaluate_expr` /
`build_evaluator`) — the official ESS Julia evaluator — so this module
hosts no parallel dispatch table. `simplify`'s constant-folding step
delegates to `evaluate_expr` so adding an op to the tree-walk evaluator
transparently extends the folder.
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
    # Substitute into EVERY sub-expression the node carries — not just `args` —
    # so substitution is complete inside aggregate/arrayop bodies, filter
    # predicates, integral bounds, makearray values, and table_lookup axis
    # inputs. `reconstruct` then preserves all other fields (semiring, ranges,
    # output_idx, table, manifold, id, join, …) that earlier hand-listed
    # rebuilds silently dropped. Bound locals (index vars, `int_var`) are short
    # local symbols never present in `bindings` (whose keys are namespaced
    # globals / parameter names), so recursing cannot capture them.
    sub(x) = x === nothing ? nothing : substitute(x, bindings)
    new_args = Expr[substitute(arg, bindings) for arg in expr.args]
    new_values = expr.values === nothing ? nothing :
        Expr[substitute(v, bindings) for v in expr.values]
    new_table_axes = expr.table_axes === nothing ? nothing :
        Dict{String,Expr}(k => substitute(v, bindings) for (k, v) in expr.table_axes)
    return reconstruct(expr;
        args = new_args,
        lower = sub(expr.lower), upper = sub(expr.upper),
        expr_body = sub(expr.expr_body), filter = sub(expr.filter),
        values = new_values, table_axes = new_table_axes)
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
# 4. Evaluation error type
# ========================================

"""
    UnboundVariableError

Raised by [`evaluate_expr`](@ref) (the tree-walk evaluator entry point)
when an expression references a variable name that is not in the supplied
bindings. Defined here so it is in scope for callers that catch the
"binding not yet resolved" signal during iterated observed-variable
fixed-point passes.
"""
struct UnboundVariableError <: Exception
    variable_name::String
    message::String
end

Base.show(io::IO, e::UnboundVariableError) = print(io, "UnboundVariableError: $(e.message)")

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
    lower_simplified = expr.lower === nothing ? nothing : simplify(expr.lower)
    upper_simplified = expr.upper === nothing ? nothing : simplify(expr.upper)

    op = expr.op

    # Try constant folding first - if all arguments are numeric, evaluate.
    # Per RFC §5.4.1, promotion happens only in evaluate, not simplify;
    # so when mixed int/float inputs fold, the result is a float literal.
    # When all inputs are integer, preserve integer result (for ops whose
    # integer result is representable — fall back to float on non-integer).
    # Folding is delegated to the official tree-walk evaluator
    # (`evaluate_expr`) so the simplifier shares the runner's dispatch
    # table and there is no parallel operator switch in this module.
    if all(is_literal, simplified_args)
        try
            result_value = evaluate_expr(
                reconstruct(expr; args=simplified_args, lower=lower_simplified, upper=upper_simplified),
                Dict{String,Float64}())
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
            return reconstruct(expr; args=Expr[non_zero_args...], lower=lower_simplified, upper=upper_simplified)
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
            return reconstruct(expr; args=Expr[non_one_args...], lower=lower_simplified, upper=upper_simplified)
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

        return reconstruct(expr; args=simplified_args, lower=lower_simplified, upper=upper_simplified)

    elseif op == "-" && length(simplified_args) == 2
        # x - 0 = x
        if is_lit_val(simplified_args[2], 0.0)
            return simplified_args[1]
        end

        return reconstruct(expr; args=simplified_args, lower=lower_simplified, upper=upper_simplified)

    elseif op == "/" && length(simplified_args) == 2
        # x / 1 = x
        if is_lit_val(simplified_args[2], 1.0)
            return simplified_args[1]
        end

        # 0 / x = 0 (for x != 0)
        if isa(simplified_args[1], NumExpr) && simplified_args[1].value == 0.0
            return NumExpr(0.0)
        end

        return reconstruct(expr; args=simplified_args, lower=lower_simplified, upper=upper_simplified)
    end

    # If no simplification rules apply, return the expression with simplified arguments
    return reconstruct(expr; args=simplified_args, lower=lower_simplified, upper=upper_simplified)
end