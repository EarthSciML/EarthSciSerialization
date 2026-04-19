module EarthSciSerializationCatalystExt

using EarthSciSerialization
using EarthSciSerialization: Expr, NumExpr, IntExpr, VarExpr, OpExpr, Reaction,
    ReactionSystem, Species, Parameter, Equation, ContinuousEvent,
    DiscreteEvent, AffectEquation, FunctionalAffect, ConditionTrigger,
    PeriodicTrigger, PresetTimesTrigger
using ModelingToolkit
using Symbolics
using Catalyst

# ========================================
# ESM Expr → Symbolics conversion (local copy for rate expressions)
# ========================================

function _esm_to_symbolic(expr::Expr, var_dict::Dict{String,Any})
    if expr isa IntExpr
        return expr.value
    elseif expr isa NumExpr
        return expr.value
    elseif expr isa VarExpr
        if haskey(var_dict, expr.name)
            return var_dict[expr.name]
        else
            sym = Symbolics.variable(Symbol(expr.name); T=Real)
            var_dict[expr.name] = sym
            return sym
        end
    elseif expr isa OpExpr
        op = expr.op
        if op == "+"
            args = [_esm_to_symbolic(a, var_dict) for a in expr.args]
            return length(args) == 1 ? args[1] : sum(args)
        elseif op == "-"
            args = [_esm_to_symbolic(a, var_dict) for a in expr.args]
            return length(args) == 1 ? -args[1] : args[1] - args[2]
        elseif op == "*"
            args = [_esm_to_symbolic(a, var_dict) for a in expr.args]
            return length(args) == 1 ? args[1] : prod(args)
        elseif op == "/"
            l = _esm_to_symbolic(expr.args[1], var_dict)
            r = _esm_to_symbolic(expr.args[2], var_dict)
            return l / r
        elseif op == "^"
            l = _esm_to_symbolic(expr.args[1], var_dict)
            r = _esm_to_symbolic(expr.args[2], var_dict)
            return l^r
        elseif op in ("exp", "log", "log10", "sin", "cos", "tan", "sqrt", "abs")
            arg = _esm_to_symbolic(expr.args[1], var_dict)
            fn = getfield(Base, Symbol(op))
            return fn(arg)
        else
            error("Unsupported operator in rate expression: $op")
        end
    end
    error("Unknown expression type: $(typeof(expr))")
end

# ========================================
# ESM ReactionSystem → Catalyst.ReactionSystem
# ========================================

"""
    Catalyst.ReactionSystem(rsys::EarthSciSerialization.ReactionSystem; name=:anonymous, kwargs...)

Build a `Catalyst.ReactionSystem` from an ESM `ReactionSystem`.
"""
# Create a Catalyst species using @species so it carries the species
# metadata Catalyst.Reaction expects — the plain Symbolics.variable path
# strips it. We invoke @species at runtime via Core.eval because the macro
# insists on literal identifiers.
function _make_species(name::Symbol, t_sym)
    binding = Core.Expr(:(=), :__esm_t, t_sym)
    call = Core.Expr(:call, name, :__esm_t)
    block = Core.Expr(:block, binding, :(Catalyst.@species $(call)))
    let_expr = Core.Expr(:let, Core.Expr(:block), block)
    vars = Core.eval(Catalyst, let_expr)
    return vars[1]
end

function _make_cparam(name::Symbol)
    vars = Core.eval(Catalyst, :(@parameters $(name)))
    return vars[1]
end

function _make_civ(name::Symbol)
    # Independent variables in Catalyst/MTK need @independent_variables metadata.
    vars = Core.eval(Catalyst, :(@variables $(name)))
    return vars[1]
end

function Catalyst.ReactionSystem(rsys::EarthSciSerialization.ReactionSystem;
                                 name::Union{Symbol,AbstractString}=:anonymous,
                                 kwargs...)
    t = _make_civ(:t)

    species_dict = Dict{String,Any}()
    species_syms = Any[]
    for sp in rsys.species
        sym = _make_species(Symbol(sp.name), t)
        push!(species_syms, sym)
        species_dict[sp.name] = sym
    end

    param_dict = Dict{String,Any}()
    param_syms = Any[]
    for p in rsys.parameters
        sym = _make_cparam(Symbol(p.name))
        push!(param_syms, sym)
        param_dict[p.name] = sym
    end

    all_vars = Base.merge(species_dict, param_dict)
    rxns = Any[]
    for esm_rxn in rsys.reactions
        rate = _esm_to_symbolic(esm_rxn.rate, all_vars)

        reactants_syms = Any[]
        reactant_stoich = Real[]
        for (spname, st) in esm_rxn.reactants
            haskey(species_dict, spname) || continue
            push!(reactants_syms, species_dict[spname])
            push!(reactant_stoich, st)
        end

        products_syms = Any[]
        product_stoich = Real[]
        for (spname, st) in esm_rxn.products
            haskey(species_dict, spname) || continue
            push!(products_syms, species_dict[spname])
            push!(product_stoich, st)
        end

        if isempty(reactants_syms) && !isempty(products_syms)
            push!(rxns, Catalyst.Reaction(rate, nothing, products_syms,
                                          nothing, product_stoich))
        elseif !isempty(reactants_syms) && isempty(products_syms)
            push!(rxns, Catalyst.Reaction(rate, reactants_syms, nothing,
                                          reactant_stoich, nothing))
        elseif !isempty(reactants_syms) && !isempty(products_syms)
            push!(rxns, Catalyst.Reaction(rate, reactants_syms, products_syms,
                                          reactant_stoich, product_stoich))
        end
    end

    sys_name = name isa Symbol ? name : Symbol(name)
    return Catalyst.ReactionSystem(rxns, t, species_syms, param_syms;
                                   name=sys_name, kwargs...)
end

# ========================================
# Reverse direction: Catalyst → ESM ReactionSystem
# ========================================

"""
    EarthSciSerialization.ReactionSystem(rs::Catalyst.ReactionSystem)

Convert a `Catalyst.ReactionSystem` back to an ESM `ReactionSystem`.
"""
function EarthSciSerialization.ReactionSystem(rs::Catalyst.ReactionSystem)
    species = Species[]
    for sp in Catalyst.species(rs)
        name = _strip_time(string(Catalyst.getname(sp)))
        initial = try
            Symbolics.getmetadata(Symbolics.unwrap(sp),
                                  Symbolics.VariableDefaultValue, 0.0)
        catch
            0.0
        end
        push!(species, Species(name; default=initial))
    end

    parameters = Parameter[]
    for p in Catalyst.parameters(rs)
        pname = string(Catalyst.getname(p))
        default = try
            Symbolics.getmetadata(Symbolics.unwrap(p),
                                  Symbolics.VariableDefaultValue, 1.0)
        catch
            1.0
        end
        push!(parameters, Parameter(pname, default))
    end

    reactions = Reaction[]
    for rxn in Catalyst.reactions(rs)
        reactants = Dict{String,Int}()
        if !isempty(rxn.substrates)
            for (i, s) in enumerate(rxn.substrates)
                name = _strip_time(string(Catalyst.getname(s)))
                stoich = length(rxn.substoich) >= i ? Int(rxn.substoich[i]) : 1
                reactants[name] = stoich
            end
        end
        products = Dict{String,Int}()
        if !isempty(rxn.products)
            for (i, pr) in enumerate(rxn.products)
                name = _strip_time(string(Catalyst.getname(pr)))
                stoich = length(rxn.prodstoich) >= i ? Int(rxn.prodstoich[i]) : 1
                products[name] = stoich
            end
        end
        rate = _catalyst_rate_to_esm(rxn.rate)
        push!(reactions, Reaction(reactants, products, rate))
    end

    return ReactionSystem(species, reactions; parameters=parameters)
end

_strip_time(s::AbstractString) = endswith(s, "(t)") ? s[1:end-3] : s

function _catalyst_rate_to_esm(expr)
    if expr isa Bool
        return IntExpr(Int64(expr))  # defensive
    elseif expr isa Integer
        return IntExpr(Int64(expr))
    elseif expr isa AbstractFloat
        return NumExpr(Float64(expr))
    elseif expr isa Real
        return NumExpr(Float64(expr))
    end
    raw = Symbolics.unwrap(expr)
    if Symbolics.issym(raw)
        return VarExpr(_strip_time(string(Symbolics.getname(raw))))
    end
    if Symbolics.iscall(raw)
        op = Symbolics.operation(raw)
        args = Symbolics.arguments(raw)
        esm_args = [_catalyst_rate_to_esm(a) for a in args]
        if op == (+); return OpExpr("+", esm_args)
        elseif op == (*); return OpExpr("*", esm_args)
        elseif op == (-); return OpExpr("-", esm_args)
        elseif op == (/); return OpExpr("/", esm_args)
        elseif op == (^); return OpExpr("^", esm_args)
        else
            return OpExpr(string(nameof(op)), esm_args)
        end
    end
    return VarExpr(string(expr))
end

end # module EarthSciSerializationCatalystExt
