# Cross-Language API Comparison

This document shows equivalent functionality across different ESM Format language implementations.

## Functions Available in Multiple Languages

### Base

**Julia:**
```julia
function Base.show(io::IO, ::MIME"text/plain", expr::Expr)
```

> Base.

**Julia:**
```julia
function Base.show(io::IO, ::MIME"text/latex", expr::Expr)
```

> Base.

**Julia:**
```julia
function Base.show(io::IO, ::MIME"text/ascii", expr::Expr)
```

> Base.

**Julia:**
```julia
function Base.show(io::IO, equation::Equation)
```

> Base.

**Julia:**
```julia
function Base.show(io::IO, model::Model)
```

> Base.

**Julia:**
```julia
function Base.show(io::IO, esm_file::EsmFile)
```

> Base.

**Julia:**
```julia
function Base.show(io::IO, reaction_system::ReactionSystem)
```

> Base.

---

### Equation

**Julia:**
```julia
Equation(...)
```

**Julia:**
```julia
Equation(...)
```

---

### Expression

**Julia:**
```julia
Expression(...)
```

**Julia:**
```julia
Expression(...)
```

---

### Graph

**Julia:**
```julia
Graph(...)
```

**Julia:**
```julia
Graph(...)
```

---

### MockCatalystSystem

**Julia:**
```julia
MockCatalystSystem(...)
```

**Julia:**
```julia
function MockCatalystSystem(rsys::ReactionSystem;
```

> MockCatalystSystem(rsys::ReactionSystem; name=:anonymous)

Build a `MockCatalystSystem` snapshot from an ESM `ReactionSystem`.

---

### MockMTKSystem

**Julia:**
```julia
MockMTKSystem(...)
```

**Julia:**
```julia
function MockMTKSystem(flat::FlattenedSystem;
```

> MockMTKSystem(flat::FlattenedSystem; name=:anonymous)

Construct a `MockMTKSystem` from a `FlattenedSystem`.

**Julia:**
```julia
function MockMTKSystem(model::Model;
```

> MockMTKSystem(model::Model; name=:anonymous)

Convenience constructor: flatten the model first, then build the
`MockMTKSystem` from the resulting `FlattenedSystem`.

---

### MockPDESystem

**Julia:**
```julia
MockPDESystem(...)
```

**Julia:**
```julia
function MockPDESystem(flat::FlattenedSystem;
```

> MockPDESystem(flat::FlattenedSystem; name=:anonymous)

Construct a `MockPDESystem` from a `FlattenedSystem`.

**Julia:**
```julia
function MockPDESystem(model::Model;
```

> MockPDESystem(model::Model; name=:anonymous)

Convenience constructor: flatten the model first, then build the
`MockPDESystem` from the resulting `FlattenedSystem`.

---

### Model

**Julia:**
```julia
Model(...)
```

**Julia:**
```julia
Model(...)
```

---

### Reaction

**Julia:**
```julia
Reaction(...)
```

**Julia:**
```julia
Reaction(...)
```

**Julia:**
```julia
function Reaction(reactants::Dict{String,Int}, products::Dict{String,Int}, rate::Expr; reversible=false)
```

> Reaction(reactants::Dict{String,Int}, products::Dict{String,Int}, rate::Expr; reversible=false) -> Reaction

Legacy constructor for backward compatibility.

---

### Section

**Julia:**
```julia
Section(...)
```

**Julia:**
```julia
Section(...)
```

---

### __init__

**Python:**
```python
def __init__(self):
```

> Initialize the unit validator.

**Python:**
```python
def __init__(self, message: str, from_version: str = "", to_version: str = ""):
```

**Python:**
```python
def __init__(self, validate_after_edit: bool = True):
```

> Initialize the ESM editor.

**Python:**
```python
def __init__(self, esm_file: EsmFile):
```

> Initialize the ESM explorer.

**Python:**
```python
def __init__(self, id: str, label: str, component_type: str, **metadata):
```

**Python:**
```python
def __init__(self, id: str, label: str, variable_type: str, **metadata):
```

**Python:**
```python
def __init__(self, source: str, target: str, label: str = "", coupling_type: str = "coupling", **metadata):
```

**Python:**
```python
def __init__(self, source: str, target: str, label: str = "", dependency_type: str = "dependency", **metadata):
```

**Python:**
```python
def __init__(self, esm_file: EsmFile):
```

> Initialize the scope validator.

**Python:**
```python
def __init__(self):
```

> Initialize the operator registry.

**Python:**
```python
def __init__(self, esm_file: EsmFile):
```

**Python:**
```python
def __init__(self, esm_file: EsmFile):
```

**Python:**
```python
def __init__(self):
```

**Python:**
```python
def __init__(self, data):
```

**Python:**
```python
def __init__(self, config):
```

**Python:**
```python
def __init__(self, config: Operator):
```

**Python:**
```python
def __init__(self, config: Operator):
```

**Python:**
```python
def __init__(self, config: Operator):
```

---

### __post_init__

**Python:**
```python
def __post_init__(self):
```

**Python:**
```python
def __post_init__(self):
```

**Python:**
```python
def __post_init__(self):
```

**Python:**
```python
def __post_init__(self):
```

---

### __str__

**Python:**
```python
def __str__(self):
```

**Python:**
```python
def __str__(self):
```

**Python:**
```python
def __str__(self):
```

---

### add_continuous_event

**Julia:**
```julia
add_continuous_event(...)
```

**Julia:**
```julia
function add_continuous_event(model::Model, event::ContinuousEvent)::Model
```

> add_continuous_event(model::Model, event::ContinuousEvent) -> Model

Add a continuous event to a model.

---

### add_coupling

**Julia:**
```julia
add_coupling(...)
```

**Julia:**
```julia
function add_coupling(file::EsmFile, entry::CouplingEntry)::EsmFile
```

> add_coupling(file::EsmFile, entry::CouplingEntry) -> EsmFile

Add a coupling entry to an ESM file.

---

### add_discrete_event

**Julia:**
```julia
add_discrete_event(...)
```

**Julia:**
```julia
function add_discrete_event(model::Model, event::DiscreteEvent)::Model
```

> add_discrete_event(model::Model, event::DiscreteEvent) -> Model

Add a discrete event to a model.

---

### add_equation

**Julia:**
```julia
add_equation(...)
```

**Julia:**
```julia
function add_equation(model::Model, equation::Equation)::Model
```

> add_equation(model::Model, equation::Equation) -> Model

Add a new equation to a model.

---

### add_reaction

**Julia:**
```julia
add_reaction(...)
```

**Julia:**
```julia
function add_reaction(system::ReactionSystem, reaction::Reaction)::ReactionSystem
```

> add_reaction(system::ReactionSystem, reaction::Reaction) -> ReactionSystem

Add a new reaction to a reaction system.

---

### add_species

**Julia:**
```julia
add_species(...)
```

**Julia:**
```julia
function add_species(system::ReactionSystem, name::String, species::Species)::ReactionSystem
```

> add_species(system::ReactionSystem, name::String, species::Species) -> ReactionSystem

Add a new species to a reaction system.

---

### add_variable

**Julia:**
```julia
add_variable(...)
```

**Julia:**
```julia
function add_variable(model::Model, name::String, variable::ModelVariable)::Model
```

> add_variable(model::Model, name::String, variable::ModelVariable) -> Model

Add a new variable to a model.

---

### adjacency

**Julia:**
```julia
adjacency(...)
```

**Julia:**
```julia
function adjacency(graph::Graph{N, E}, node::N) where {N, E}
```

> Get all adjacent nodes (both predecessors and successors).

---

### coerce_coupling_entry

**Julia:**
```julia
coerce_coupling_entry(...)
```

**Julia:**
```julia
function coerce_coupling_entry(data::Any)::CouplingEntry
```

> coerce_coupling_entry(data::Any) -> CouplingEntry

Coerce JSON data into concrete CouplingEntry subtype based on the 'type' field.

---

### coerce_event

**Julia:**
```julia
function coerce_event(data::Any)::EventType
```

> coerce_event(data::Any) -> EventType

Coerce JSON data into EventType (ContinuousEvent or DiscreteEvent).

**Julia:**
```julia
function coerce_event(data::AbstractDict)::CouplingEvent
```

> coerce_event(data::AbstractDict) -> CouplingEvent

Parse event coupling entry.

---

### component_graph

**Julia:**
```julia
component_graph(...)
```

**Julia:**
```julia
function component_graph(file::EsmFile)::Graph{ComponentNode, CouplingEdge}
```

> component_graph(file::EsmFile) -> Graph{ComponentNode, CouplingEdge}

Generate component-level graph showing systems and their couplings.

**Typescript:**
```typescript
export function component_graph(esmFile: EsmFile): ComponentGraph {
```

> Extract the system graph from an ESM file.

---

### compose

**Julia:**
```julia
compose(...)
```

**Julia:**
```julia
function compose(file::EsmFile, system_a::String, system_b::String)::EsmFile
```

> compose(file::EsmFile, system_a::String, system_b::String) -> EsmFile

Convenience function to create an operator_compose coupling entry linking two systems.

**Typescript:**
```typescript
export function compose(
```

> Compose two systems using a coupling entry
@param file ESM file
@param a First system name
@param b Second system name
@returns New ESM file with composition coupling added
/.

---

### contains

**Julia:**
```julia
contains(...)
```

**Julia:**
```julia
function contains(expr::NumExpr, var::String)::Bool
```

> contains(expr::Expr, var::String)::Bool

Check if an expression contains a specific variable name.

**Typescript:**
```typescript
export function contains(expr: Expr, varName: string): boolean {
```

> Check if an expression contains a specific variable
@param expr Expression to search
@param varName Variable name to look for
@returns True if the variable appears in the expression
/.

---

### differentiate

**Python:**
```python
def differentiate(self, x_values, y_values):
```

> Forward difference implementation.

**Typescript:**
```typescript
export function differentiate(expr: Expr, variable: string): DerivativeResult {
```

> Compute the symbolic derivative of an expression with respect to a variable
@param expr Expression to differentiate
@param variable Variable with respect to which to differentiate
@returns Derivative result with simplified form
/.

---

### evaluate

**Julia:**
```julia
evaluate(...)
```

**Julia:**
```julia
function evaluate(expr::NumExpr, bindings::Dict{String,Float64})::Float64
```

> evaluate(expr::Expr, bindings::Dict{String,Float64})::Float64

Numerically evaluate an expression using provided variable bindings.

**Typescript:**
```typescript
export function evaluate(expr: Expr, bindings: Map<string, number>): number {
```

> Evaluate an expression numerically with variable bindings
@param expr Expression to evaluate
@param bindings Map of variable names to their numeric values
@returns Numeric result
@throws Error if variables are unbound or evaluation fails
/.

---

### expression_graph

**Julia:**
```julia
expression_graph(...)
```

**Julia:**
```julia
function expression_graph(file::EsmFile)::Graph{VariableNode, DependencyEdge}
```

> expression_graph(file::EsmFile) -> Graph{VariableNode, DependencyEdge}
    expression_graph(model::Model) -> Graph{VariableNode, DependencyEdge}
    expression_graph(system::ReactionSystem) -> Graph{VariableNode, DependencyEdge}
    expression_graph(equation::Equation) -> Graph{VariableNode, DependencyEdge}
    expression_graph(reaction::Reaction) -> Graph{VariableNode, DependencyEdge}
    expression_graph(expr::Expr) -> Graph{VariableNode, DependencyEdge}

Generate expression-level dependency graph showing variable relationships.

---

### extract

**Julia:**
```julia
extract(...)
```

**Julia:**
```julia
function extract(file::EsmFile, component_name::String)::EsmFile
```

> extract(file::EsmFile, component_name::String) -> EsmFile

Extract a single component into a standalone ESM file.

**Typescript:**
```typescript
export function extract(
```

> Extract a specific component from an ESM file into a new file
@param file ESM file to extract from
@param componentName Name of the component to extract
@returns New ESM file containing only the specified component
@throws EntityNotFoundError if component not found
/.

---

### fixtures_dir

**Python:**
```python
def fixtures_dir(self):
```

> Get path to display fixtures.

**Python:**
```python
def fixtures_dir(self):
```

> Get path to validation fixtures.

**Python:**
```python
def fixtures_dir(self):
```

> Get path to fixtures.

**Python:**
```python
def fixtures_dir(self):
```

> Get path to test fixtures.

**Python:**
```python
def fixtures_dir(self):
```

> Get path to substitution fixtures.

---

### flatten

**Julia:**
```julia
flatten(...)
```

**Julia:**
```julia
function flatten(file::EsmFile)::FlattenedSystem
```

> flatten(file::EsmFile) -> FlattenedSystem

Flatten the coupled systems in `file` into a single symbolic representation
per spec §4.

**Julia:**
```julia
function flatten(model::Model; name::String="anonymous")::FlattenedSystem
```

> flatten(model::Model; name::String="anonymous") -> FlattenedSystem

Convenience: wrap a single Model in a synthetic EsmFile (with a default system
name) and run the full flattener.

**Julia:**
```julia
function flatten(rsys::ReactionSystem; name::String="anonymous")::FlattenedSystem
```

> flatten(rsys::ReactionSystem; name::String="anonymous") -> FlattenedSystem

Convenience: wrap a ReactionSystem in a synthetic EsmFile and flatten.

**Typescript:**
```typescript
export function flatten(file: EsmFile): FlattenedSystem {
```

> Flatten a multi-system ESM file into a single unified system.

---

### format_expression_ascii

**Julia:**
```julia
format_expression_ascii(...)
```

**Julia:**
```julia
function format_expression_ascii(expr::Expr)
```

> format_expression_ascii(expr::Expr) -> String

Format an expression as plain ASCII mathematical notation.

---

### format_node_label

**Julia:**
```julia
format_node_label(...)
```

**Julia:**
```julia
function format_node_label(name::String, node_type::String="")::String
```

> format_node_label(name::String, node_type::String="") -> String

Format node label with chemical subscript rendering if applicable.

---

### free_variables

**Julia:**
```julia
free_variables(...)
```

**Julia:**
```julia
function free_variables(expr::NumExpr)::Set{String}
```

> free_variables(expr::Expr)::Set{String}

Extract all free (unbound) variable names from an expression.

---

### get_expression_dimensions

**Julia:**
```julia
get_expression_dimensions(...)
```

**Julia:**
```julia
function get_expression_dimensions(expr::EarthSciSerialization.Expr, var_units::Dict{String, String})::Union{Unitful.Units, Nothing}
```

> Get the dimensions of an expression by propagating units through operations.

---

### get_stats

**Python:**
```python
def get_stats(self):
```

**Python:**
```python
def get_stats(self):
```

---

### infer_variable_units

**Julia:**
```julia
infer_variable_units(...)
```

**Julia:**
```julia
function infer_variable_units(var_name::String, equations::Vector{Equation}, known_units::Dict{String, String})::Union{String, Nothing}
```

> Infer appropriate units for a variable based on its usage in equations.

---

### interpolate

**Python:**
```python
def interpolate(self, x_values, y_values, x_new):
```

> Simple linear interpolation implementation.

**Python:**
```python
def interpolate(self, x_values, y_values, x_new):
```

> Spline interpolation implementation.

---

### is_valid_identifier

**Julia:**
```julia
is_valid_identifier(...)
```

**Julia:**
```julia
function is_valid_identifier(name::String)::Bool
```

> is_valid_identifier(name::String) -> Bool

Check if a string is a valid identifier (letters, numbers, underscores, no leading digit).

---

### load

**Julia:**
```julia
load(...)
```

**Julia:**
```julia
function load(path::String)::EsmFile
```

> load(path::String) -> EsmFile

Load and parse an ESM file from a file path.

**Julia:**
```julia
function load(io::IO)::EsmFile
```

> load(io::IO) -> EsmFile

Load and parse an ESM file from an IO stream.

**Typescript:**
```typescript
export function load(input: string | object): EsmFile {
```

> Load an ESM file from a JSON string or pre-parsed object

@param input - JSON string or pre-parsed JavaScript object
@returns Typed EsmFile object
@throws {ParseError} When JSON parsing fails or version is incompatible
@throws {SchemaValidationError} When schema validation fails
/.

---

### lower_reactions_to_equations

**Julia:**
```julia
lower_reactions_to_equations(...)
```

**Julia:**
```julia
function lower_reactions_to_equations(reactions::Vector{Reaction},
```

> lower_reactions_to_equations(reactions, species, domain=nothing) -> Vector{Equation}

Produce the ODE equations induced by a set of reactions using standard
mass-action kinetics: `d[X]/dt = Σ (stoich_ij * rate_j)`.

---

### main

**Python:**
```python
def main():
```

> Run all coupling error handling demonstrations.

**Python:**
```python
def main():
```

> Demonstrate mathematical operators functionality.

**Python:**
```python
def main():
```

> Main demonstration function.

**Python:**
```python
def main():
```

> Demonstrate operator registry functionality.

**Python:**
```python
def main():
```

> Run all demonstrations.

**Python:**
```python
def main():
```

> Run all performance optimization demos.

**Python:**
```python
def main():
```

> Run all demonstrations.

---

### map_variable

**Julia:**
```julia
map_variable(...)
```

**Julia:**
```julia
function map_variable(file::EsmFile, from::String, to::String; transform::String="identity")::EsmFile
```

> map_variable(file::EsmFile, from::String, to::String; transform::String="identity") -> EsmFile

Convenience function to create a variable_map coupling entry that forwards a
variable reference `from` into `to`.

---

### merge

**Julia:**
```julia
merge(...)
```

**Julia:**
```julia
function merge(file_a::EsmFile, file_b::EsmFile)::EsmFile
```

> merge(file_a::EsmFile, file_b::EsmFile) -> EsmFile

Merge two ESM files.

**Typescript:**
```typescript
export function merge(
```

> Merge two ESM files
@param fileA First ESM file
@param fileB Second ESM file
@returns New ESM file with merged content
/.

---

### migrate

**Python:**
```python
def migrate(esm_file, target_version: str):
```

> Migrate an ESM file to a target version.

**Typescript:**
```typescript
export function migrate(file: EsmFile, targetVersion: string): EsmFile {
```

> Migrate an ESM file from its current schema version to the target version.

---

### no

**Julia:**
```julia
no(...)
```

**Julia:**
```julia
no(...)
```

---

### objective

**Python:**
```python
def objective(params):
```

> Objective function for parameter estimation.

**Python:**
```python
def objective(x):
```

---

### operations

**Julia:**
```julia
operations(...)
```

**Julia:**
```julia
operations(...)
```

---

### parse_units

**Julia:**
```julia
parse_units(...)
```

**Julia:**
```julia
function parse_units(unit_str::String)::Union{Unitful.Units, Nothing}
```

> Parse a unit string into a Unitful.

---

### predecessors

**Julia:**
```julia
predecessors(...)
```

**Julia:**
```julia
function predecessors(graph::Graph{N, E}, node::N) where {N, E}
```

> Get nodes that point to this node.

---

### reference

**Julia:**
```julia
reference(...)
```

**Julia:**
```julia
reference(...)
```

---

### registerWebComponents

**Typescript:**
```typescript
export function registerWebComponents() {
```

**Typescript:**
```typescript
export function registerWebComponents() {
```

> Register all ESM editor web components
/.

---

### remove_coupling

**Julia:**
```julia
remove_coupling(...)
```

**Julia:**
```julia
function remove_coupling(file::EsmFile, index::Int)::EsmFile
```

> remove_coupling(file::EsmFile, index::Int) -> EsmFile

Remove a coupling entry by index.

---

### remove_equation

**Julia:**
```julia
remove_equation(...)
```

**Julia:**
```julia
function remove_equation(model::Model, index::Int)::Model
```

> remove_equation(model::Model, index::Int) -> Model
    remove_equation(model::Model, lhs_pattern::Expr) -> Model

Remove an equation from a model.

---

### remove_event

**Julia:**
```julia
remove_event(...)
```

**Julia:**
```julia
function remove_event(model::Model, name::String)::Model
```

> remove_event(model::Model, name::String) -> Model

Remove an event by name from a model.

---

### remove_reaction

**Julia:**
```julia
remove_reaction(...)
```

**Julia:**
```julia
function remove_reaction(system::ReactionSystem, id::String)::ReactionSystem
```

> remove_reaction(system::ReactionSystem, id::String) -> ReactionSystem

Remove a reaction by its ID.

---

### remove_species

**Julia:**
```julia
remove_species(...)
```

**Julia:**
```julia
function remove_species(system::ReactionSystem, name::String)::ReactionSystem
```

> remove_species(system::ReactionSystem, name::String) -> ReactionSystem

Remove a species from a reaction system.

---

### remove_variable

**Julia:**
```julia
remove_variable(...)
```

**Julia:**
```julia
function remove_variable(model::Model, name::String)::Model
```

> remove_variable(model::Model, name::String) -> Model

Remove a variable from a model.

---

### rename_variable

**Julia:**
```julia
rename_variable(...)
```

**Julia:**
```julia
function rename_variable(model::Model, old_name::String, new_name::String)::Model
```

> rename_variable(model::Model, old_name::String, new_name::String) -> Model

Rename a variable throughout the model.

---

### render_chemical_formula

**Julia:**
```julia
render_chemical_formula(...)
```

**Julia:**
```julia
function render_chemical_formula(formula::String)::String
```

> render_chemical_formula(formula::String) -> String

Convert chemical formula to format with subscripts for visualization.

---

### resolution

**Julia:**
```julia
resolution(...)
```

**Julia:**
```julia
resolution(...)
```

---

### resolve_qualified_reference

**Julia:**
```julia
resolve_qualified_reference(...)
```

**Julia:**
```julia
function resolve_qualified_reference(esm_file::EsmFile, reference::String)::ReferenceResolution
```

> resolve_qualified_reference(esm_file::EsmFile, reference::String) -> ReferenceResolution

Resolve a qualified reference string using hierarchical dot notation.

---

### resolve_subsystem_refs!

**Julia:**
```julia
resolve_subsystem_refs!(...)
```

**Julia:**
```julia
function resolve_subsystem_refs!(file::EsmFile, base_path::String)
```

> resolve_subsystem_refs!(file::EsmFile, base_path::String)

Resolve all subsystem references in-place.

---

### save

**Julia:**
```julia
save(...)
```

**Julia:**
```julia
function save(file::EsmFile, path::String)
```

> save(file::EsmFile, path::String)
    save(path::String, file::EsmFile)

Save an EsmFile object to a JSON file at the specified path.

**Julia:**
```julia
function save(file::EsmFile, io::IO)
```

> save(file::EsmFile, io::IO)

Save an EsmFile object to a JSON stream.

**Typescript:**
```typescript
export function save(file: EsmFile): string {
```

> Serialize an EsmFile object to a formatted JSON string

@param file - The EsmFile object to serialize
@returns Formatted JSON string representation
/.

---

### serialize_coupling_entry

**Julia:**
```julia
serialize_coupling_entry(...)
```

**Julia:**
```julia
function serialize_coupling_entry(entry::CouplingEntry)::Dict{String,Any}
```

> serialize_coupling_entry(entry::CouplingEntry) -> Dict{String,Any}

Serialize CouplingEntry to JSON-compatible format based on concrete type.

---

### serialize_event

**Julia:**
```julia
function serialize_event(event::EventType)::Dict{String,Any}
```

> serialize_event(event::EventType) -> Dict{String,Any}

Serialize EventType to JSON-compatible format.

**Julia:**
```julia
function serialize_event(entry::CouplingEvent)::Dict{String,Any}
```

> serialize_event(entry::CouplingEvent) -> Dict{String,Any}

Serialize event coupling entry.

---

### simplify

**Julia:**
```julia
simplify(...)
```

**Julia:**
```julia
function simplify(expr::NumExpr)::Expr
```

> simplify(expr::Expr)::Expr

Perform constant folding and algebraic simplification on an expression.

**Typescript:**
```typescript
export function simplify(expr: Expr): Expr {
```

> Simplify an expression using basic algebraic rules
@param expr Expression to simplify
@returns Simplified expression
/.

---

### substitute

**Julia:**
```julia
substitute(...)
```

**Julia:**
```julia
function substitute(expr::NumExpr, bindings::Dict{String,Expr})::Expr
```

> substitute(expr::Expr, bindings::Dict{String,Expr})::Expr

Recursively replace variables in an expression with provided bindings.

**Typescript:**
```typescript
export function substitute(
```

> Recursively substitute variable references in an expression with bound expressions.

---

### substitute_in_equations

**Julia:**
```julia
substitute_in_equations(...)
```

**Julia:**
```julia
function substitute_in_equations(model::Model, bindings::Dict{String, EarthSciSerialization.Expr})::Model
```

> substitute_in_equations(model::Model, bindings::Dict{String, Expr}) -> Model

Apply substitutions across all equations in a model.

---

### successors

**Julia:**
```julia
successors(...)
```

**Julia:**
```julia
function successors(graph::Graph{N, E}, node::N) where {N, E}
```

> Get nodes that this node points to.

---

### system

**Julia:**
```julia
system(...)
```

**Julia:**
```julia
system(...)
```

---

### test_empty_system

**Python:**
```python
def test_empty_system(self):
```

> Test handling of empty reaction system.

**Python:**
```python
def test_empty_system(self):
```

> Test empty reaction system returns empty matrix.

---

### test_required_fields_validation

**Python:**
```python
def test_required_fields_validation(self):
```

> Test that required fields (esm, metadata) are enforced.

**Python:**
```python
def test_required_fields_validation(self):
```

> Test that required fields are enforced for data loaders.

---

### test_source_and_sink_reactions

**Python:**
```python
def test_source_and_sink_reactions(self):
```

> Test source (null substrates) and sink (null products) reactions.

**Python:**
```python
def test_source_and_sink_reactions(self):
```

> Test reactions with no reactants (source) or no products (sink).

---

### to_ascii

**Julia:**
```julia
to_ascii(...)
```

**Julia:**
```julia
function to_ascii(target)
```

> to_ascii(target) -> String

Format target as plain ASCII mathematical notation.

---

### to_dot

**Julia:**
```julia
to_dot(...)
```

**Julia:**
```julia
function to_dot(graph::Graph{ComponentNode, CouplingEdge})::String
```

> Export graph to DOT format for Graphviz rendering.

---

### to_json

**Julia:**
```julia
to_json(...)
```

**Julia:**
```julia
function to_json(graph::Graph{N, E})::String where {N, E}
```

> Export graph to JSON adjacency list format.

---

### to_mermaid

**Julia:**
```julia
to_mermaid(...)
```

**Julia:**
```julia
function to_mermaid(graph::Graph{ComponentNode, CouplingEdge})::String
```

> Export graph to Mermaid format for markdown embedding.

---

### types

**Julia:**
```julia
types(...)
```

**Julia:**
```julia
types(...)
```

**Julia:**
```julia
types(...)
```

**Julia:**
```julia
types(...)
```

**Julia:**
```julia
types(...)
```

**Julia:**
```julia
types(...)
```

**Julia:**
```julia
types(...)
```

**Julia:**
```julia
types(...)
```

---

### validate

**Julia:**
```julia
validate(...)
```

**Julia:**
```julia
function validate(file::EsmFile)::ValidationResult
```

> validate(file::EsmFile) -> ValidationResult

Complete validation combining schema, structural, and unit validation.

**Typescript:**
```typescript
export function validate(data: string | object): ValidationResult {
```

> Validate ESM data and return structured validation result.

---

### validate_equation_dimensions

**Julia:**
```julia
validate_equation_dimensions(...)
```

**Julia:**
```julia
function validate_equation_dimensions(eq::Equation, var_units::Dict{String, String})::Bool
```

> Validate that an equation is dimensionally consistent.

---

### validate_file_dimensions

**Julia:**
```julia
validate_file_dimensions(...)
```

**Julia:**
```julia
function validate_file_dimensions(file::EsmFile)::Bool
```

> Validate dimensions for all components in an ESM file.

---

### validate_model_dimensions

**Julia:**
```julia
validate_model_dimensions(...)
```

**Julia:**
```julia
function validate_model_dimensions(model::Model)::Bool
```

> Validate dimensions for all equations in a model.

---

### validate_reaction_system_dimensions

**Julia:**
```julia
validate_reaction_system_dimensions(...)
```

**Julia:**
```julia
function validate_reaction_system_dimensions(rxn_sys::ReactionSystem)::Bool
```

> Validate dimensions for all reactions in a reaction system.

---

### validate_reference_syntax

**Julia:**
```julia
validate_reference_syntax(...)
```

**Julia:**
```julia
function validate_reference_syntax(reference::String)::Bool
```

> validate_reference_syntax(reference::String) -> Bool

Validate that a reference string follows proper dot notation syntax.

---

### validate_schema

**Julia:**
```julia
validate_schema(...)
```

**Julia:**
```julia
function validate_schema(data::Any)::Vector{SchemaError}
```

> validate_schema(data::Any) -> Vector{SchemaError}

Validate data against the ESM schema.

---

### validate_structural

**Julia:**
```julia
validate_structural(...)
```

**Julia:**
```julia
function validate_structural(file::EsmFile)::Vector{StructuralError}
```

> validate_structural(file::EsmFile) -> Vector{StructuralError}

Validate structural consistency of ESM file according to spec Section 3.

---

### validation

**Julia:**
```julia
validation(...)
```

**Julia:**
```julia
validation(...)
```

---

## Types Available in Multiple Languages

### AffectEquation

**Julia:**
```julia
struct AffectEquation
```

> AffectEquation(lhs::String, rhs::Expr)

Assignment equation for discrete events.

**Python:**
```python
class AffectEquation:
```

> Equation that affects a variable (assignment-like).

**Typescript:**
```typescript
export interface AffectEquation {
```

> An affect equation in an event: lhs is the target variable (string), rhs is an expression.

---

### BoundaryCondition

**Python:**
```python
class BoundaryCondition:
```

> Boundary condition specification.

**Typescript:**
```typescript
export interface BoundaryCondition {
```

> Boundary condition for one or more dimensions.

---

### ComponentNode

**Julia:**
```julia
struct ComponentNode
```

> Component-level node representing a model, reaction system, data loader, or operator.

**Python:**
```python
class ComponentNode:
```

> A component node representing models or reaction systems.

**Typescript:**
```typescript
export interface ComponentNode {
```

---

### ConflictingDerivativeError

**Julia:**
```julia
struct ConflictingDerivativeError <: Exception
```

> ConflictingDerivativeError

Raised when a species appears both as the left-hand side of an explicit
differential equation (`D(X, t) = .

**Python:**
```python
class ConflictingDerivativeError:
```

> Two systems define non-additive equations for the same dependent variable.

---

### ConnectorEquation

**Python:**
```python
class ConnectorEquation:
```

> Single equation in a connector system.

**Typescript:**
```typescript
export interface ConnectorEquation {
```

> A single equation in a ConnectorSystem linking two coupled systems.

---

### ContinuousEvent

**Julia:**
```julia
struct ContinuousEvent <: EventType
```

> ContinuousEvent <: EventType

Event triggered by zero-crossing of condition expressions.

**Python:**
```python
class ContinuousEvent:
```

> An event that occurs when a condition becomes true during continuous evolution.

**Typescript:**
```typescript
export interface ContinuousEvent {
```

> Fires when a condition expression crosses zero (root-finding).

---

### CoordinateTransform

**Python:**
```python
class CoordinateTransform:
```

> Coordinate transformation specification.

**Typescript:**
```typescript
export interface CoordinateTransform {
```

---

### CouplingCallback

**Julia:**
```julia
struct CouplingCallback <: CouplingEntry
```

> CouplingCallback <: CouplingEntry

Register a callback for simulation events.

**Typescript:**
```typescript
export interface CouplingCallback {
```

> Register a callback for simulation events.

---

### CouplingCouple

**Julia:**
```julia
struct CouplingCouple <: CouplingEntry
```

> CouplingCouple <: CouplingEntry

Bi-directional coupling via connector equations.

**Python:**
```python
class CouplingCouple:
```

> Coupling entry for couple type.

**Typescript:**
```typescript
export interface CouplingCouple {
```

> Bi-directional coupling via explicit ConnectorSystem equations.

---

### CouplingEdge

**Julia:**
```julia
struct CouplingEdge
```

> Edge representing coupling between components.

**Python:**
```python
class CouplingEdge:
```

> An edge representing coupling between components.

**Python:**
```python
class CouplingEdge:
```

> Represents a labeled edge in the coupling graph.

**Typescript:**
```typescript
export interface CouplingEdge {
```

---

### CouplingOperatorApply

**Julia:**
```julia
struct CouplingOperatorApply <: CouplingEntry
```

> CouplingOperatorApply <: CouplingEntry

Register an Operator to run during simulation.

**Typescript:**
```typescript
export interface CouplingOperatorApply {
```

> Register an Operator to run during simulation.

---

### CouplingOperatorCompose

**Julia:**
```julia
struct CouplingOperatorCompose <: CouplingEntry
```

> CouplingOperatorCompose <: CouplingEntry

Match LHS time derivatives and add RHS terms together.

**Typescript:**
```typescript
export interface CouplingOperatorCompose {
```

> Match LHS time derivatives and add RHS terms together.

---

### CouplingVariableMap

**Julia:**
```julia
struct CouplingVariableMap <: CouplingEntry
```

> CouplingVariableMap <: CouplingEntry

Replace a parameter in one system with a variable from another.

**Typescript:**
```typescript
export interface CouplingVariableMap {
```

> Replace a parameter in one system with a variable from another.

---

### CyclicPromotionError

**Julia:**
```julia
struct CyclicPromotionError <: Exception
```

> CyclicPromotionError

Defined for cross-language error-name parity.

**Python:**
```python
class CyclicPromotionError:
```

> Promotion rules form a cycle (A→B→…→A).

---

### DataLoader

**Julia:**
```julia
struct DataLoader
```

> DataLoader

Generic, runtime-agnostic description of an external data source.

**Python:**
```python
class DataLoader:
```

> Generic, runtime-agnostic description of an external data source.

**Typescript:**
```typescript
export interface DataLoader {
```

> A generic, runtime-agnostic description of an external data source.

---

### DataLoaderRegridding

**Julia:**
```julia
struct DataLoaderRegridding
```

> DataLoaderRegridding

Structural regridding configuration for a DataLoader.

**Python:**
```python
class DataLoaderRegridding:
```

> Structural regridding configuration for a data loader.

**Typescript:**
```typescript
export interface DataLoaderRegridding {
```

> Structural regridding configuration.

---

### DataLoaderSource

**Julia:**
```julia
struct DataLoaderSource
```

> DataLoaderSource

File discovery configuration for a DataLoader.

**Python:**
```python
class DataLoaderSource:
```

> File discovery configuration for a data loader.

**Typescript:**
```typescript
export interface DataLoaderSource {
```

> File discovery configuration.

---

### DataLoaderSpatial

**Julia:**
```julia
struct DataLoaderSpatial
```

> DataLoaderSpatial

Spatial grid description for a DataLoader.

**Python:**
```python
class DataLoaderSpatial:
```

> Spatial grid description for a data source.

**Typescript:**
```typescript
export interface DataLoaderSpatial {
```

> Spatial grid description for a data source.

---

### DataLoaderTemporal

**Julia:**
```julia
struct DataLoaderTemporal
```

> DataLoaderTemporal

Temporal coverage and record layout for a DataLoader.

**Python:**
```python
class DataLoaderTemporal:
```

> Temporal coverage and record layout for a data source.

**Typescript:**
```typescript
export interface DataLoaderTemporal {
```

> Temporal coverage and record layout for a data source.

---

### DataLoaderVariable

**Julia:**
```julia
struct DataLoaderVariable
```

> DataLoaderVariable

A variable exposed by a DataLoader, mapped from a source-file variable.

**Python:**
```python
class DataLoaderVariable:
```

> A variable exposed by a data loader, mapped from a source-file variable.

**Typescript:**
```typescript
export interface DataLoaderVariable {
```

> A variable exposed by a data loader, mapped from a source-file variable.

---

### DependencyEdge

**Julia:**
```julia
struct DependencyEdge
```

> Edge representing dependency between variables.

**Python:**
```python
class DependencyEdge:
```

> An edge representing mathematical dependencies.

**Typescript:**
```typescript
export interface DependencyEdge {
```

---

### DimensionPromotionError

**Julia:**
```julia
struct DimensionPromotionError <: Exception
```

> DimensionPromotionError

Raised during flatten when a variable or equation cannot be promoted from
its source domain to the target domain given the available `Interface` rules
(§4.

**Python:**
```python
class DimensionPromotionError:
```

> A variable or equation cannot be promoted given the available Interfaces.

---

### DiscreteEvent

**Julia:**
```julia
struct DiscreteEvent <: EventType
```

> DiscreteEvent <: EventType

Event triggered by discrete triggers with functional affects.

**Python:**
```python
class DiscreteEvent:
```

> An event that occurs at discrete time points.

---

### Domain

**Julia:**
```julia
struct Domain
```

> Domain

Spatial and temporal domain specification.

**Python:**
```python
class Domain:
```

> Comprehensive computational domain specification.

**Typescript:**
```typescript
export interface Domain {
```

> Spatiotemporal domain specification (DomainInfo).

---

### DomainExtentMismatchError

**Julia:**
```julia
struct DomainExtentMismatchError <: Exception
```

> DomainExtentMismatchError

Defined for cross-language error-name parity with the Rust `FlattenError`
taxonomy and the Python `flatten()` exception set.

**Python:**
```python
class DomainExtentMismatchError:
```

> Two domains coupled via ``identity`` have incompatible spatial extents.

---

### DomainUnitMismatchError

**Julia:**
```julia
struct DomainUnitMismatchError <: Exception
```

> DomainUnitMismatchError

Raised when coupling across an `Interface` requires a unit conversion that
was not declared by the user (§4.

**Python:**
```python
class DomainUnitMismatchError:
```

> An Interface coupling requires a unit conversion that was not declared.

---

### ESMError

**Julia:**
```julia
struct ESMError
```

> ESMError

Comprehensive error representation with diagnostics and suggestions.

**Python:**
```python
class ESMError:
```

> ESM validation or processing error.

**Typescript:**
```typescript
export interface ESMError {
```

---

### Equation

**Julia:**
```julia
struct Equation
```

> Equation(lhs::Expr, rhs::Expr, _comment::Union{String,Nothing}=nothing)

Mathematical equation with left-hand side and right-hand side expressions.

**Python:**
```python
class Equation:
```

> Mathematical equation with left and right hand sides.

**Python:**
```python
class Equation:
```

> Mathematical equation with left and right hand sides.

**Typescript:**
```typescript
export interface Equation {
```

> An equation: lhs = rhs (or lhs ~ rhs in MTK notation).

---

### ErrorCollector

**Julia:**
```julia
mutable struct ErrorCollector
```

> ErrorCollector

Collects and manages errors during ESM processing.

**Python:**
```python
class ErrorCollector:
```

> Collects errors and warnings during validation.

---

### ErrorContext

**Julia:**
```julia
struct ErrorContext
```

> ErrorContext

Additional context information for errors.

**Python:**
```python
class ErrorContext:
```

> Context information for errors.

**Typescript:**
```typescript
export interface ErrorContext {
```

---

### EsmCouplingGraphProps

**Typescript:**
```typescript
export interface EsmCouplingGraphProps {
```

> Web component wrapper for CouplingGraph

Usage:
<esm-coupling-graph
esm-file='{"components": [.

**Typescript:**
```typescript
export interface EsmCouplingGraphProps {
```

> Web component wrapper for CouplingGraph

Usage:
<esm-coupling-graph
esm-file='{"components": [.

---

### EsmFile

**Julia:**
```julia
struct EsmFile
```

> EsmFile

Main ESM file structure containing all components.

**Python:**
```python
class EsmFile:
```

> Root container for an ESM format file.

---

### EsmModelEditorProps

**Typescript:**
```typescript
export interface EsmModelEditorProps {
```

> Web component wrapper for ModelEditor

Usage:
<esm-model-editor
model='{"variables": {.

**Typescript:**
```typescript
export interface EsmModelEditorProps {
```

> Web component wrapper for ModelEditor

Usage:
<esm-model-editor
model='{"variables": {.

---

### ExprNode

**Python:**
```python
class ExprNode:
```

> A node in an expression tree.

**Python:**
```python
class ExprNode:
```

> A node in an expression tree.

---

### FixSuggestion

**Julia:**
```julia
struct FixSuggestion
```

> FixSuggestion

Actionable suggestion for fixing an error.

**Python:**
```python
class FixSuggestion:
```

> Suggestion for fixing an error.

**Typescript:**
```typescript
export interface FixSuggestion {
```

---

### FlattenMetadata

**Julia:**
```julia
struct FlattenMetadata
```

> FlattenMetadata

Provenance metadata for a flattened system.

**Python:**
```python
class FlattenMetadata:
```

> Provenance metadata for a FlattenedSystem.

**Typescript:**
```typescript
export interface FlattenMetadata {
```

> Metadata describing the origin of the flattened system.

---

### FlattenedEquation

**Python:**
```python
class FlattenedEquation:
```

> An equation in the flattened system, with namespaced Expr trees.

**Typescript:**
```typescript
export interface FlattenedEquation {
```

> A single equation in the flattened system, with dot-namespaced variable names.

---

### FlattenedSystem

**Julia:**
```julia
struct FlattenedSystem
```

> FlattenedSystem

A coupled ESM file flattened into a single symbolic representation.

**Python:**
```python
class FlattenedSystem:
```

> The result of flattening an EsmFile per spec §4.

**Typescript:**
```typescript
export interface FlattenedSystem {
```

> A fully flattened representation of a coupled ESM system.

---

### FunctionalAffect

**Julia:**
```julia
struct FunctionalAffect
```

> FunctionalAffect

Functional affect for discrete events.

**Python:**
```python
class FunctionalAffect:
```

> A functional effect applied during an event.

**Typescript:**
```typescript
export interface FunctionalAffect {
```

> Registered functional affect handler (alternative to symbolic affects).

---

### Graph

**Julia:**
```julia
struct Graph{N, E}
```

> Generic graph structure with nodes and edges.

**Python:**
```python
class Graph:
```

> Generic graph representation with nodes and edges.

**Typescript:**
```typescript
export interface Graph<N, E> {
```

---

### Interface

**Julia:**
```julia
struct Interface
```

> Interface

Defines the geometric relationship between two domains of potentially different
dimensionality.

**Typescript:**
```typescript
export interface Interface {
```

> Geometric connection between two domains of potentially different dimensionality.

---

### Metadata

**Julia:**
```julia
struct Metadata
```

> Metadata

Authorship, provenance, and description metadata.

**Python:**
```python
class Metadata:
```

> Metadata about the model or dataset.

**Typescript:**
```typescript
export interface Metadata {
```

> Authorship, provenance, and description.

---

### Model

**Julia:**
```julia
struct Model
```

> Model

ODE-based model component containing variables, equations, and optional subsystems.

**Python:**
```python
class Model:
```

> A mathematical model containing variables and equations.

**Typescript:**
```typescript
export interface Model {
```

> An ODE system — a fully specified set of time-dependent equations.

---

### ModelVariable

**Julia:**
```julia
struct ModelVariable
```

> ModelVariable

Structure defining a model variable with its type, default value, and optional expression.

**Python:**
```python
class ModelVariable:
```

> A variable in a mathematical model.

**Typescript:**
```typescript
export interface ModelVariable {
```

> A variable in an ODE model.

---

### Operator

**Julia:**
```julia
struct Operator
```

> Operator

Registered runtime operator (by reference).

**Python:**
```python
class Operator:
```

> A registered runtime operator (e.

**Typescript:**
```typescript
export interface Operator {
```

> A registered runtime operator (e.

---

### Parameter

**Julia:**
```julia
struct Parameter
```

> Parameter

Model parameter with name, default value, and optional metadata.

**Python:**
```python
class Parameter:
```

> A parameter for reaction systems.

**Typescript:**
```typescript
export interface Parameter {
```

> A parameter in a reaction system.

---

### Reaction

**Julia:**
```julia
struct Reaction
```

> Reaction

Chemical reaction with substrates, products, and rate expression.

**Python:**
```python
class Reaction:
```

> A chemical reaction.

**Typescript:**
```typescript
export interface Reaction {
```

> A single reaction in a reaction system.

---

### ReactionSystem

**Julia:**
```julia
struct ReactionSystem
```

> ReactionSystem

Collection of chemical reactions with associated species, supporting hierarchical composition.

**Python:**
```python
class ReactionSystem:
```

> A system of chemical reactions.

**Typescript:**
```typescript
export interface ReactionSystem {
```

> A reaction network — declarative representation of chemical or biological reactions.

---

### Reference

**Julia:**
```julia
struct Reference
```

> Reference

Academic citation or data source reference.

**Python:**
```python
class Reference:
```

> Bibliographic reference.

**Typescript:**
```typescript
export interface Reference {
```

> Academic citation or data source reference.

---

### SchemaError

**Julia:**
```julia
struct SchemaError
```

> SchemaError

Represents a validation error with detailed information.

**Typescript:**
```typescript
export interface SchemaError {
```

> Schema validation error with JSON Pointer path
/.

---

### SchemaValidationError

**Julia:**
```julia
struct SchemaValidationError <: Exception
```

> SchemaValidationError

Exception thrown when schema validation fails.

**Python:**
```python
class SchemaValidationError:
```

> Exception raised when schema validation fails.

---

### SimulationResult

**Python:**
```python
class SimulationResult:
```

> Result of a simulation run.

**Python:**
```python
class SimulationResult:
```

> Simulation result with rich display methods.

---

### SliceOutOfDomainError

**Julia:**
```julia
struct SliceOutOfDomainError <: Exception
```

> SliceOutOfDomainError

Defined for cross-language error-name parity; only raised if `slice` is ever
implemented at a higher tier in the Julia flatten pipeline.

**Python:**
```python
class SliceOutOfDomainError:
```

> A ``slice`` mapping reaches outside the source variable's domain.

---

### SpatialDimension

**Python:**
```python
class SpatialDimension:
```

> Spatial dimension specification.

**Typescript:**
```typescript
export interface SpatialDimension {
```

> Specification of a single spatial dimension.

---

### Species

**Julia:**
```julia
struct Species
```

> Species

Chemical species definition with name and optional properties.

**Python:**
```python
class Species:
```

> A chemical species in a reaction system.

**Typescript:**
```typescript
export interface Species {
```

> A reactive species in a reaction system.

---

### StoichiometryEntry

**Julia:**
```julia
struct StoichiometryEntry
```

> StoichiometryEntry

A species with its stoichiometric coefficient in a reaction.

**Typescript:**
```typescript
export interface StoichiometryEntry {
```

> A species with its stoichiometric coefficient in a reaction.

---

### StructuralError

**Julia:**
```julia
struct StructuralError
```

> StructuralError

Represents a structural validation error with detailed information.

**Typescript:**
```typescript
export interface StructuralError {
```

> Structural error type matching the format specification
/.

---

### SubsystemRefError

**Julia:**
```julia
struct SubsystemRefError <: Exception
```

> SubsystemRefError

Exception thrown when subsystem reference resolution fails.

**Python:**
```python
class SubsystemRefError:
```

> Exception raised when a subsystem reference cannot be resolved.

---

### UnitWarning

**Python:**
```python
class UnitWarning:
```

> Represents a unit validation warning.

**Typescript:**
```typescript
export interface UnitWarning {
```

> Unit validation warning
/.

---

### UnmappedDomainError

**Julia:**
```julia
struct UnmappedDomainError <: Exception
```

> UnmappedDomainError

Raised when two systems on different domains are coupled without an `Interface`
that defines their dimension mapping (§4.

**Python:**
```python
class UnmappedDomainError:
```

> A coupling references a variable whose domain has no mapping rule.

---

### UnsupportedMappingError

**Julia:**
```julia
struct UnsupportedMappingError <: Exception
```

> UnsupportedMappingError

Raised when an `Interface` requests a `dimension_mapping` type or regridding
strategy that is not supported by the current library tier (§4.

**Python:**
```python
class UnsupportedMappingError:
```

> A dimension-promotion mapping is not supported by this implementation tier.

---

### ValidationError

**Python:**
```python
class ValidationError:
```

> Represents a single validation error.

**Typescript:**
```typescript
export interface ValidationError {
```

> Validation error with structured details
/.

**Typescript:**
```typescript
export interface ValidationError {
```

---

### ValidationResult

**Julia:**
```julia
struct ValidationResult
```

> ValidationResult

Combined validation result containing schema errors, structural errors,
unit warnings, and overall validation status.

**Python:**
```python
class ValidationResult:
```

> Represents the result of validation.

**Typescript:**
```typescript
export interface ValidationResult {
```

> Structured validation result
/.

---

### VariableNode

**Julia:**
```julia
struct VariableNode
```

> Variable-level node for expression graphs.

**Python:**
```python
class VariableNode:
```

> A variable node representing mathematical variables or expressions.

**Typescript:**
```typescript
export interface VariableNode {
```

---

