"""
    EarthSciSerialization

EarthSciML Serialization Format Julia library.

This module provides Julia types and functions for working with ESM format files,
which are JSON-based serialization format for EarthSciML model components,
their composition, and runtime configuration.

Deep ModelingToolkit/Catalyst integration is provided by package extensions
(`EarthSciSerializationMTKExt`, `EarthSciSerializationCatalystExt`) that load
automatically when the user imports `ModelingToolkit` or `Catalyst`. Without
those packages loaded, `MockMTKSystem`, `MockPDESystem`, and `MockCatalystSystem`
give plain-Julia snapshots of the flattened system with the same ODE/PDE split.
"""
module EarthSciSerialization

using Dates
using JSON3
using JSONSchema

include("types.jl")
include("error_handling.jl")
include("validate.jl")
include("reactions.jl")
include("flatten.jl")
include("mock_systems.jl")
include("registered_functions.jl")
include("expression_templates.jl")
include("parse.jl")
include("serialize.jl")
include("expression.jl")
include("display.jl")
include("graph.jl")
include("units.jl")
include("edit.jl")
include("codegen.jl")
include("canonicalize.jl")
include("rule_engine.jl")
include("discretize.jl")
include("grid_accessor.jl")
include("abstract_grid.jl")
include("grid_assembly.jl")
include("ghost_cells.jl")
include("mtk_export.jl")
include("tree_walk.jl")
include("mms_evaluator.jl")

export
    # Expression types
    Expr, NumExpr, IntExpr, VarExpr, OpExpr,
    # Literal predicates (RFC §5.4.1 int/float distinction)
    is_literal, literal_value,
    # Equation types
    Equation, AffectEquation,
    # Model component types
    ModelVariableType, StateVariable, ParameterVariable, ObservedVariable, BrownianVariable,
    ModelVariable, Model, Species, Parameter, Reaction, ReactionSystem,
    # Event types
    EventType, ContinuousEvent, DiscreteEvent, FunctionalAffect, DiscreteEventTrigger,
    ConditionTrigger, PeriodicTrigger, PresetTimesTrigger,
    # Data and operator types
    DataLoader, DataLoaderSource, DataLoaderTemporal, DataLoaderSpatial,
    DataLoaderVariable, DataLoaderRegridding, DataLoaderMesh, DataLoaderDeterminism,
    Operator, RegisteredFunction, RegisteredFunctionSignature, CouplingEntry,
    # Concrete coupling types
    CouplingOperatorCompose, CouplingCouple, CouplingVariableMap,
    CouplingOperatorApply, CouplingCallback, CouplingEvent,
    # Flattened system (§4.7.5 / §4.7.6)
    FlattenMetadata, FlattenedSystem, flatten, lower_reactions_to_equations,
    infer_array_shapes,
    # Flatten error taxonomy (spec §4.7.6.10, 8 types for cross-language parity)
    ConflictingDerivativeError, DimensionPromotionError, UnmappedDomainError,
    UnsupportedMappingError, DomainUnitMismatchError,
    DomainExtentMismatchError, SliceOutOfDomainError, CyclicPromotionError,
    # System types
    Domain, Interface, Grid, StaggeringRule, Reference, Metadata, EsmFile,
    # JSON functionality
    load, save, ParseError, SchemaValidationError, SchemaError, validate_schema,
    # Subsystem reference resolution
    resolve_subsystem_refs!, SubsystemRefError,
    # Coupling serialization functions
    serialize_coupling_entry, coerce_coupling_entry,
    # Structural validation
    StructuralError, ValidationResult, validate_structural, validate,
    validate_reaction_rate_units, validate_model_gradient_units,
    # Expression operations
    substitute, free_variables, contains, evaluate, simplify, UnboundVariableError,
    # Qualified reference resolution
    resolve_qualified_reference, QualifiedReferenceError, ReferenceResolution,
    validate_reference_syntax, is_valid_identifier,
    # Reaction system ODE derivation
    derive_odes, stoichiometric_matrix, mass_action_rate,
    # Mock systems (no-MTK / no-Catalyst fallbacks)
    MockMTKSystem, MockPDESystem, MockCatalystSystem,
    # Graph analysis (Section 4.8)
    Graph, ComponentNode, CouplingEdge, VariableNode, DependencyEdge,
    component_graph, expression_graph, adjacency, predecessors, successors,
    to_dot, to_mermaid, to_json,
    # Chemical subscript rendering
    render_chemical_formula, format_node_label,
    # Unit validation
    parse_units, get_expression_dimensions, validate_equation_dimensions,
    validate_model_dimensions, validate_reaction_system_dimensions, validate_file_dimensions,
    infer_variable_units,
    # Editing operations (Section 4)
    add_variable, remove_variable, rename_variable,
    add_equation, remove_equation, substitute_in_equations,
    add_reaction, remove_reaction, add_species, remove_species,
    add_continuous_event, add_discrete_event, remove_event,
    add_coupling, remove_coupling, compose, map_variable,
    merge, extract,
    # Code generation
    to_julia_code, to_python_code,
    # ASCII display format
    to_ascii, format_expression_ascii,
    # Canonical AST form (RFC §5.4)
    canonicalize, canonical_json, format_canonical_float, CanonicalizeError,
    # Rule engine (RFC §5.2, §5.2.7, §5.2.8)
    Rule, Guard, RuleContext, RuleEngineError, RuleBinding,
    BoundaryPolicy, BoundaryPolicySpec, GhostWidth,
    RuleRegion, RegionBoundary, RegionPanelBoundary,
    RegionMaskField, RegionIndexRange,
    match_pattern, apply_bindings, rewrite,
    check_guards, check_guard, check_scope,
    with_query_point,
    parse_rule, parse_rules, check_unrewritten_pde_ops,
    # Discretization pipeline (RFC §11, gt-gbs2)
    discretize,
    # MTK → ESM export (gt-dod2; Phase 1 migration tooling)
    mtk2esm, mtk2esm_gaps, GapReport,
    # Tree-walk evaluator (gt-e8yw; MTK-free RHS path)
    build_evaluator, TreeWalkError,
    # Closed function registry (esm-tzp / esm-4aw; esm-spec §9.2)
    evaluate_closed_function, closed_function_names, ClosedFunctionError,
    lower_enums!,
    # GridAccessor interface (gt-hvl4; concrete impls live in ESD)
    GridAccessor, GridAccessorError,
    cell_centers, neighbors, metric_eval,
    register_grid_accessor!, unregister_grid_accessor!,
    grid_accessor_factory, registered_grid_families, make_grid_accessor,
    # AbstractGrid trait (esm-a3z; concrete impls live in ESD)
    AbstractGrid, AbstractCurvilinearGrid, AbstractStaggeredGrid,
    AbstractVerticalGrid, AbstractUnstructuredGrid, GridTraitError,
    cell_volume, cell_widths, neighbor_indices, boundary_mask,
    n_cells, n_dims, axis_names,
    metric_g, metric_ginv, metric_jacobian, metric_dgij_dxk,
    coord_jacobian, coord_jacobian_second,
    # FV grid-metric assembly (esm-xom; ported from ESD src/fv_stencil.jl)
    FVLaplacianStencil, FVGradientStencil,
    precompute_laplacian_stencil, precompute_gradient_stencil,
    apply_laplacian!, apply_gradient!,
    # Trait-generic ghost-cell gathering (esm-dlz; ported from ESD src/ghost_cells.jl)
    extend_with_ghosts, fill_ghost_cells!, extend_with_ghosts_vector,
    # Symbolic ArrayOp assembly (esm-tet; ported from ESD src/discretization.jl)
    # — concrete methods live in ext/grid_assembly_symbolic.jl, loaded with MTK.
    fv_laplacian_extended, fv_gradient_extended,
    laplacian_neighbor_table, gradient_neighbor_table,
    const_wrap, get_idx_vars, make_arrayop, evaluate_arrayop,
    # MMS convergence harness (esm-ivo; ESD walker Layer B driver)
    # PPM reconstruction extensions (esm-k1d): sub-stencil targeting,
    # output-kind selector, parabola pass.
    # MPAS-style unstructured MMS support (esm-0sy).
    # 2D structured + per-cell metric bindings + sphere MMS registry (esm-5ur).
    MMSEvaluatorError, ManufacturedSolution, ManufacturedSolution2D,
    ReconstructionManufacturedSolution2D,
    MMSConvergenceResult, CellBindings, bindings_at,
    parse_accuracy_order, lookup_manufactured_solution,
    lookup_manufactured_solution_2d,
    lookup_manufactured_solution_2d_reconstruction,
    register_manufactured_solution!, eval_coeff, OUTPUT_KINDS,
    apply_stencil_periodic_1d, apply_stencil_2d_latlon,
    apply_stencil_2d_arakawa, apply_stencil_1d_vertical,
    parabola_reconstruct_periodic_1d,
    mms_convergence, verify_mms_convergence,
    # WENO5 nonlinear reconstruction (esm-rq3)
    apply_weno5_reconstruction_periodic_1d, mms_weno5_convergence,
    # MPAS-style unstructured MMS support (esm-0sy)
    VectorManufacturedSolution, MPASLikeMesh, MPASCoeffContext,
    register_vector_manufactured_solution!, lookup_vector_manufactured_solution,
    make_periodic_quad_mesh, apply_mpas_cell_stencil,
    sample_edge_normal_flux, sample_cell_divergence,
    mms_convergence_mpas, verify_mms_convergence_mpas

end # module EarthSciSerialization
