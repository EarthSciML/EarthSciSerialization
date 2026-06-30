# ============================================================================
# Downstream shape promotion (scalar → array) as an AST transform
# ============================================================================
#
# A coupled system is often authored with a SPATIAL field (e.g. a level-set
# `psi[x,y]`) fed by a chain of scalar "physics" variables (`R = f(U, EMC, …)`),
# which are in turn fed by ARRAY sources (a per-cell regridded forcing `F_tgt[x,y]`).
# The scalar authoring is a dimensionality fiction: each physics quantity really
# varies per grid cell. Rather than re-author every component per-cell, or lift
# scalars over the grid in the evaluator (runner logic), we PROMOTE shapes in the
# AST: any variable whose defining expression's inferred shape is an array grid
# shape is promoted to that shape, and its equation is rewritten from a scalar
# expression into an `arrayop` that indexes the now-array operands per cell and
# broadcasts the genuine scalars. Because the rewrite emits standard `arrayop`
# nodes, the evaluator needs NO new per-cell machinery.
#
# This is broadcast shape inference over the dataflow graph:
#  - SEED: variables with an explicit (grid) shape — regrid outputs, loader
#    fields, the spatial state.
#  - PROPAGATE: an operand's shape flows to the result through elementwise ops;
#    an `aggregate`/`arrayop` with a contracting `output_idx` is a PROMOTION
#    BOUNDARY (a genuine reduction stays scalar), and an `index` gather is scalar.
#  - CONFLICT: all array sources must resolve to one grid shape; a genuine
#    mismatch is an error (the caller picks the target grid).

# Output shape (vector of index-set / dim names; empty = scalar) of an expression
# under the current per-variable shape map.
function _infer_expr_shape(expr::EarthSciSerialization.Expr,
                           shapes::Dict{String,Vector{String}})::Vector{String}
    if expr isa NumExpr || expr isa IntExpr
        return String[]
    elseif expr isa VarExpr
        return get(shapes, expr.name, String[])
    elseif expr isa OpExpr
        op = expr.op
        if op == "index"
            # A gather selects one element (or a fixed slice) — scalar output for
            # promotion purposes (the level-set already indexes its own field).
            return String[]
        elseif op == "aggregate" || op == "arrayop" || op == "makearray"
            # Output is exactly the uncontracted axes named in output_idx.
            return expr.output_idx === nothing ? String[] :
                   String[string(x) for x in expr.output_idx]
        else
            # Elementwise: broadcast — all non-scalar operands must agree, the
            # result takes that shape. `lower`/`upper` (integral bounds) and
            # `filter` don't shape the elementwise result.
            sh = String[]
            for a in expr.args
                s = _infer_expr_shape(a, shapes)
                isempty(s) && continue
                if isempty(sh)
                    sh = s
                elseif sh != s
                    throw(ArgumentError(
                        "shape-promotion: conflicting operand shapes $(sh) vs $(s) " *
                        "in op '$(op)' — array sources must resolve to one grid shape"))
                end
            end
            return sh
        end
    end
    return String[]
end

# Replace each VarExpr leaf naming a promoted ARRAY variable with `index(v, loops…)`,
# leaving scalar leaves (params, constants, reductions' results) untouched. Does
# not descend into nested aggregate/arrayop bodies — those carry their own indexing.
function _index_array_leaves(expr::EarthSciSerialization.Expr,
                             arrayvars::Set{String}, loops::Vector{String})::EarthSciSerialization.Expr
    if expr isa VarExpr
        if expr.name in arrayvars
            idx = EarthSciSerialization.Expr[VarExpr(expr.name)]
            for l in loops
                push!(idx, VarExpr(l))
            end
            return OpExpr("index", idx)
        end
        return expr
    elseif expr isa OpExpr
        (expr.op == "aggregate" || expr.op == "arrayop" || expr.op == "makearray" ||
         expr.op == "index") && return expr
        new_args = EarthSciSerialization.Expr[_index_array_leaves(a, arrayvars, loops) for a in expr.args]
        return reconstruct(expr; args=new_args)
    end
    return expr
end

# Wrap a (formerly scalar) defining expression in an arrayop producing `shape`.
# Loop vars are fresh simple names (`_p0`, `_p1`, …) — NOT the index-set names,
# which may be dotted/namespaced — each ranging over the corresponding set.
function _lift_to_arrayop(expr::EarthSciSerialization.Expr, shape::Vector{String},
                          arrayvars::Set{String})::OpExpr
    loops = String["_p$(i-1)" for i in 1:length(shape)]
    ranges = Dict{String,Any}(loops[i] => IndexSetRef(shape[i]) for i in eachindex(shape))
    body = _index_array_leaves(expr, arrayvars, loops)
    return OpExpr("arrayop", EarthSciSerialization.Expr[];
                  output_idx=Any[l for l in loops], ranges=ranges, expr_body=body)
end

"""
    promote_downstream_shapes(flat::FlattenedSystem) -> FlattenedSystem

Promote every variable whose defining algebraic equation has an inferred ARRAY
(grid) shape from scalar to that shape, rewriting its equation into an `arrayop`
that indexes the now-array operands per cell. Shape inference is seeded by the
variables already carrying a grid shape (regrid outputs, loader fields, the
spatial state) and propagates through elementwise ops, stopping at aggregate
reductions and `index` gathers. The transform is a no-op for a system with no
scalar-downstream-of-array variables (it returns an equivalent system).

`index_sets` for the grid axes must already be declared (the loop ranges resolve
against them); supply them on the FlattenedSystem before calling. Returns a new
FlattenedSystem; the input is untouched.
"""
function promote_downstream_shapes(flat::FlattenedSystem)::FlattenedSystem
    # Current shapes from declarations (scalar = []).
    shapes = Dict{String,Vector{String}}()
    for d in (flat.state_variables, flat.parameters, flat.observed_variables)
        for (k, v) in d
            shapes[k] = v.shape === nothing ? String[] : String[string(s) for s in v.shape]
        end
    end

    # Index the ALGEBRAIC defining equations (bare `x = expr`). State equations
    # (`D(x,t) = …`) don't define x's shape (x keeps its declared shape).
    defs = Dict{String,EarthSciSerialization.Expr}()
    for eq in flat.equations
        eq.lhs isa VarExpr || continue
        defs[(eq.lhs::VarExpr).name] = eq.rhs
    end

    # Fixed-point shape inference: a scalar var whose defining expression infers
    # an array shape is promoted. Repeat until stable (acyclic chain ⇒ converges).
    changed = true
    while changed
        changed = false
        for (name, rhs) in defs
            cur = get(shapes, name, String[])
            isempty(cur) || continue                     # already array — leave it
            inferred = _infer_expr_shape(rhs, shapes)
            if !isempty(inferred)
                shapes[name] = inferred
                changed = true
            end
        end
    end

    # The set of variables that are now array-shaped (for leaf indexing).
    arrayvars = Set{String}(k for (k, s) in shapes if !isempty(s))

    # Rebuild variable partitions with promoted shapes.
    function promote_partition(part)
        out = OrderedDict{String,ModelVariable}()
        for (k, v) in part
            s = get(shapes, k, String[])
            if !isempty(s) && (v.shape === nothing || isempty(v.shape))
                out[k] = _with_shape(v, s)              # promoted: was scalar
            else
                out[k] = v
            end
        end
        return out
    end
    new_states = promote_partition(flat.state_variables)
    new_params = promote_partition(flat.parameters)
    new_observeds = promote_partition(flat.observed_variables)

    # Rewrite equations: a promoted var's bare `x = expr` becomes `x = arrayop(…)`;
    # otherwise index any newly-array operands that appear bare in the RHS
    # (e.g. an aggregate body, or a still-scalar consumer that must now gather).
    new_eqs = Equation[]
    for eq in flat.equations
        if eq.lhs isa VarExpr && (eq.lhs::VarExpr).name in arrayvars &&
           haskey(defs, (eq.lhs::VarExpr).name) &&
           (flat_was_scalar(flat, (eq.lhs::VarExpr).name))
            name = (eq.lhs::VarExpr).name
            push!(new_eqs, Equation(eq.lhs, _lift_to_arrayop(eq.rhs, shapes[name], arrayvars);
                                    _comment=eq._comment, region=eq.region))
        else
            push!(new_eqs, eq)
        end
    end

    return FlattenedSystem(flat.independent_variables, new_states, new_params,
                           new_observeds, new_eqs, flat.continuous_events,
                           flat.discrete_events, flat.domain, flat.metadata,
                           flat.index_sets, flat.function_tables)
end

# True iff `name` was authored scalar (no declared shape) in the original system.
function flat_was_scalar(flat::FlattenedSystem, name::AbstractString)::Bool
    for d in (flat.state_variables, flat.parameters, flat.observed_variables)
        haskey(d, name) && return d[name].shape === nothing || isempty(d[name].shape)
    end
    return true
end

# Return a copy of a ModelVariable with a new (array) shape. A promoted variable's
# defining scalar `expression` is cleared — its rewritten `arrayop` EQUATION is now
# the single source of truth (flatten always emits an equation per observed), so a
# stale scalar expression at an array shape can't be mistaken for the definition.
function _with_shape(v::ModelVariable, shape::Vector{String})::ModelVariable
    return ModelVariable(v.type; default=v.default, units=v.units,
        default_units=v.default_units, description=v.description,
        expression=nothing, shape=copy(shape), location=v.location,
        noise_kind=v.noise_kind, correlation_group=v.correlation_group)
end
