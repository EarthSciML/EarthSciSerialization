# ESM Library Specification

**Companion Libraries for the EarthSciML Serialization Format — Version 0.1.0 Draft**

## 1. Overview

This document specifies the requirements and architecture for libraries that read, write, manipulate, validate, and optionally simulate models defined in the ESM format (`.esm` files). Each library must provide a consistent developer experience in its host language while mapping faithfully to the ESM JSON Schema.

**Companion schema:** The authoritative type definitions, operator enums, and structural constraints are in [`esm-schema.json`](esm-schema.json) (same directory as this document). This spec describes behavior, algorithms, and API surfaces; the schema is the single source of truth for field names, types, required properties, and allowed values.

### 1.1 Design Goals

1. **Fidelity** — Round-trip an `.esm` file through load → manipulate → save without information loss.
2. **Readability** — Render models as human-readable mathematical notation (Unicode, LaTeX, or MathML).
3. **Editability** — Programmatic manipulation of models: substitution, simplification, adding/removing components.
4. **Validation** — Schema validation, structural consistency checks, and unit analysis.
5. **Interoperability** — Libraries in different languages produce and consume identical `.esm` files.
6. **Simulation** (desired) — Convert ESM models into runnable ODE/SDE/jump problems where feasible.

### 1.2 Capability Tiers

Each library implementation is classified into tiers:

| Tier | Capabilities | Required for |
|---|---|---|
| **Core** | Parse, serialize, pretty-print, substitute, validate schema | All languages |
| **Analysis** | Unit checking, equation counting, stoichiometric matrix computation, conservation law detection | All languages |
| **Interactive** | Click-to-edit expressions, structural editing, undo/redo, coupling graph, web component export | `esm-editor` (SolidJS) |
| **Simulation** | Convert to native ODE system and solve numerically | Julia (MTK), Python (SymPy + SciPy), optionally others |
| **Full** | Bidirectional MTK/Catalyst conversion, coupled system assembly, operator dispatch | Julia only (initially) |

---

## 2. Common Architecture

All libraries share the same conceptual layering regardless of implementation language.

### 2.1 Layer Diagram

```
┌─────────────────────────────────────────────┐
│              User-Facing API                │
│  load() / save() / display() / substitute() │
├─────────────────────────────────────────────┤
│            Validation Layer                  │
│  schema / structural / units                 │
├─────────────────────────────────────────────┤
│          Expression Engine                   │
│  AST ↔ symbolic repr / pretty-print / eval   │
├─────────────────────────────────────────────┤
│        Data Model (Type System)              │
│  EsmFile, Model, ReactionSystem, Expression…│
├─────────────────────────────────────────────┤
│         JSON Parse / Serialize               │
│  Schema-aware deserialization                │
└─────────────────────────────────────────────┘
```

### 2.1a Error Handling

The `load()` function must **throw** (or return an error, in languages without exceptions) when given invalid JSON. Specifically:

- **Malformed JSON** (syntax errors): Throw a parse error immediately. Do not attempt recovery.
- **Valid JSON that fails schema validation**: Throw a validation error with the list of schema violations. Libraries must not silently accept invalid files.
- **Valid JSON that passes schema validation but fails structural validation**: `load()` succeeds (returns an `EsmFile`), but the structural issues are reported by the separate `validate()` function. This allows loading partially invalid files for inspection and repair.

### 2.2 Data Model

Every library must define typed representations for:

| ESM concept | Type name (suggested) | Notes |
|---|---|---|
| Top-level file | `EsmFile` | Contains all sections |
| Expression AST | `Expr` | Recursive: `Num`, `Var`, `Op` |
| Equation | `Equation` | `{lhs: Expr, rhs: Expr, _comment?: string}` |
| Affect equation | `AffectEquation` | `{lhs: string, rhs: Expr}` |
| Model variable | `ModelVariable` | `state`, `parameter`, or `observed` |
| Model | `Model` | Variables, equations, events |
| Species | `Species` | Units, default, description |
| Reaction | `Reaction` | Substrates, products, rate |
| Reaction system | `ReactionSystem` | Species, parameters, reactions, events |
| Continuous event | `ContinuousEvent` | Conditions, affects, affect_neg |
| Discrete event | `DiscreteEvent` | Trigger, affects, discrete_parameters |
| Functional affect | `FunctionalAffect` | Handler reference |
| Data loader | `DataLoader` | Registered by ID |
| Operator | `Operator` | Registered by ID |
| Coupling entry | `CouplingEntry` | Discriminated union on `type` |
| Domain | `Domain` | Temporal, spatial, BCs, ICs |
| Solver | `Solver` | Strategy + config |
| Reference | `Reference` | doi, citation, url, notes |
| Metadata | `Metadata` | Name, authors, tags |

#### 2.2.1 Optional Fields

Several data model types support optional fields for enhanced documentation and debugging:

**Equation `_comment` field**: The `_comment` field is an optional string that provides human-readable documentation about an equation's purpose or mathematical meaning. This field is commonly used in examples and test files to clarify the physical interpretation of equations.

Examples of usage:
- `"_comment": "Fast consumption of A: dA/dt = -k_fast*A + k_slow*B"`
- `"_comment": "Momentum equation x-direction with viscous terms and pressure gradient"`
- `"_comment": "Logistic equation: dp/dt = r*p*(1 - p/K)"`

The comment field is purely for documentation and has no effect on model behavior or validation. Libraries should preserve comments during round-trip serialization and may optionally display them in pretty-printed output or debugging interfaces.

### 2.3 Expression Engine Requirements

The expression engine is the heart of every library. It must support:

#### 2.3.1 Construction

- Build expressions programmatically: `Var("O3")`, `Op("+", [Var("a"), Num(1)])`.
- Parse from ESM JSON (the `Expression` type in the schema).

#### 2.3.2 Pretty-printing

Render an expression tree as a human-readable string. Multiple output formats:

| Format | Example output for `D(O3, t) = -k * O3 * NO + j * NO2` |
|---|---|
| Unicode | `∂O₃/∂t = −k·O₃·NO + j·NO₂` |
| LaTeX | `\frac{\partial \mathrm{O_3}}{\partial t} = -k \cdot \mathrm{O_3} \cdot \mathrm{NO} + j \cdot \mathrm{NO_2}` |
| ASCII | `d(O3)/dt = -k * O3 * NO + j * NO2` |
| Code (language-native) | Julia: `D(O3) ~ -k * O3 * NO + j * NO2` |

Minimum requirement: **Unicode** and **LaTeX**. Language-native code output is desired.

Pretty-printing must handle:

- Operator precedence and associativity (minimize parentheses).
- Subscripts for chemical species (O₃, NO₂, CH₂O).
- Fractions: display `a/b` as `\frac{a}{b}` in LaTeX.
- The `Pre` operator: render as `Pre(x)` or `x⁻` depending on format.
- Calculus operators: `D(x, t)` → `∂x/∂t`, `grad(x, y)` → `∂x/∂y`.

#### 2.3.3 Substitution

Replace a variable or subexpression with another expression:

```
substitute(expr, {"T": Num(298.15)})                    # variable → constant
substitute(expr, {"k1": Op("*", [Num(1.8e-12), ...])})  # variable → expression
substitute(expr, {"_var": Var("O3")})                    # placeholder → variable
```

Substitution must be recursive and handle hierarchical scoped references (`"Model.Subsystem.var"` — see the ESM format spec Section 4.3 for the full resolution algorithm).

#### 2.3.4 Structural Operations

- `free_variables(expr) → Set<string>` — all variable references in the expression.
- `free_parameters(expr) → Set<string>` — subset that are parameters (requires model context).
- `contains(expr, var) → bool` — whether a variable appears in the expression.
- `simplify(expr) → Expr` — optional algebraic simplification (language-dependent). At minimum, implementations should fold constant arithmetic (e.g., `2 + 3` → `5`, `x * 1` → `x`, `x + 0` → `x`, `x * 0` → `0`). Deeper algebraic simplification (factoring, trigonometric identities, etc.) is language-dependent and not required for conformance.
- `evaluate(expr, bindings: Map<string, number>) → number` — numerical evaluation. All variables and parameters must be present in `bindings`; if any variable is unbound, the function must raise an error listing the unbound variables. (Partial evaluation is the responsibility of `substitute`, not `evaluate`.)

#### 2.3.5 Serialization

Convert expression tree back to ESM JSON format (the inverse of parsing). Must produce output that validates against the schema and round-trips identically.

---

## 3. Validation

### 3.1 Schema Validation

Every library must validate an `.esm` file against the JSON Schema. This is the first validation pass and catches structural errors (missing required fields, wrong types, invalid enum values).

**Implementation:** Use the language's standard JSON Schema library:

| Language | Library |
|---|---|
| Julia | `JSONSchema.jl` |
| TypeScript | `ajv` |
| Python | `jsonschema` |
| Rust | `jsonschema` (crate) |
| Go | `gojsonschema` |

### 3.2 Structural Validation

Beyond schema correctness, validate mathematical and semantic consistency:

#### 3.2.1 Equation–Unknown Balance

For each model:

- Count state variables (type `"state"`) → `n_states`.
- Count equations whose LHS is a time derivative `D(var, t)` → `n_odes`.
- **Check:** `n_odes == n_states`. If not, report which variables lack equations or which equations lack corresponding state variables.

For each reaction system:

- The number of ODEs is determined automatically (one per species), so this check is inherently satisfied. Instead, verify:
  - Every species referenced in a reaction is declared in `species`.
  - Every parameter referenced in a rate expression is declared in `parameters`.

#### 3.2.2 Reference Integrity

- Every variable name referenced in an equation exists in the model's `variables` (or in a subsystem's variables, if using a scoped reference).
- Every scoped reference in coupling entries resolves to an actual variable by walking the subsystem hierarchy. A reference like `"A.B.C"` must resolve as: `A` is a top-level system, `B` is a subsystem of `A`, and `C` is a variable/species/parameter in `B`. The last dot-separated segment is always the variable name; all preceding segments form the system path. See the ESM format spec Section 4.3 for the full resolution algorithm.
- Every `discrete_parameters` entry in an event matches a declared parameter.
- Every `from`/`to` in coupling entries references an existing model, reaction system, data loader, or operator (including subsystems nested at any depth).
- Every `operator` in `operator_apply` coupling entries exists in the `operators` section.

#### 3.2.3 Event Consistency

- Continuous event conditions are expressions (not booleans) — they should be zero-crossing detectable.
- Discrete event `condition` triggers should produce boolean values (comparisons, logical ops).
- Every variable referenced in `affects` (both LHS and RHS) is declared in the owning model/reaction system (or uses valid scoped references for cross-system events).
- Functional affect `read_vars` and `read_params` reference declared variables.

#### 3.2.4 Reaction Consistency

- Every species in substrates/products is in `species`.
- Stoichiometries are positive integers.
- No reaction has both `substrates: null` and `products: null` (would be a null reaction).
- Rate expressions only reference declared parameters, species, or known functions.

### 3.3 Unit Validation

Unit validation checks dimensional consistency of equations. This is the most complex validation and may be approximate.

#### 3.3.1 Approach

1. Parse unit strings into a canonical dimensional representation (e.g., `"mol/mol/s"` → `{mol: 0, s: -1}` since mol/mol cancels).
2. Propagate dimensions through expressions:
   - Addition/subtraction: operands must have the same dimensions.
   - Multiplication: dimensions add.
   - Division: dimensions subtract.
   - `D(x, t)`: dimension of x divided by dimension of t.
   - Functions (exp, log, sin, …): argument must be dimensionless; result is dimensionless.
   - `^`: base dimensions multiplied by exponent (which must be dimensionless).
3. For each equation, verify LHS and RHS have the same dimensions.

#### 3.3.2 Unit Libraries

| Language | Recommended |
|---|---|
| Julia | `Unitful.jl` or `DynamicQuantities.jl` |
| TypeScript | `mathjs` units or custom lightweight parser |
| Python | `pint` |
| Rust | `uom` |

#### 3.3.3 Limitations

- ESM unit strings are free-form (e.g., `"mol/mol"`, `"cm^3/molec/s"`) and not standardized to a specific unit system. Libraries should parse common patterns but may need to accept unrecognized units as opaque strings.
- Cross-system unit validation (through coupling) requires resolving scoped references first.
- Some operators (registered by reference) have opaque semantics — their inputs/outputs are declared with units, but the internal transformation cannot be checked.

### 3.4 Validation API

Every library must expose:

```
validate(file: EsmFile) → ValidationResult
```

Where `ValidationResult` contains:

- `schema_errors: List<SchemaError>` — JSON Schema violations.
- `structural_errors: List<StructuralError>` — equation/unknown balance, reference integrity.
- `unit_warnings: List<UnitWarning>` — dimensional inconsistencies (warnings, not hard errors, because unit strings may be ambiguous).
- `is_valid: bool` — true if no schema or structural errors.

#### Error Type Structures

```
SchemaError:
  path: string          # JSON Pointer to the offending location (e.g., "/models/SuperFast/equations/0/rhs")
  message: string       # Human-readable description (e.g., "Required property 'op' is missing")
  keyword: string       # JSON Schema keyword that failed (e.g., "required", "enum", "type")

StructuralError:
  path: string          # JSON Pointer to the relevant component (e.g., "/models/SuperFast")
  code: string          # Machine-readable error code (see below)
  message: string       # Human-readable description
  details: Map<string, any>  # Additional context (e.g., {"variable": "O3", "expected_in": "variables"})

UnitWarning:
  path: string          # JSON Pointer to the equation or expression
  message: string       # Human-readable description
  lhs_units: string     # Inferred units of the LHS
  rhs_units: string     # Inferred units of the RHS
```

**Structural error codes:**

| Code | Description |
|---|---|
| `equation_count_mismatch` | Number of ODE equations does not match number of state variables |
| `undefined_variable` | Variable referenced in an equation is not declared |
| `undefined_species` | Species referenced in a reaction is not declared |
| `undefined_parameter` | Parameter referenced in a rate expression is not declared |
| `undefined_system` | Coupling entry references a nonexistent model, reaction system, data loader, or operator |
| `undefined_operator` | `operator_apply` references a nonexistent operator |
| `unresolved_scoped_ref` | Scoped reference (e.g., `"Model.Subsystem.var"`) cannot be resolved — a segment in the system path does not exist or the final variable is not declared |
| `invalid_discrete_param` | `discrete_parameters` entry does not match a declared parameter |
| `null_reaction` | Reaction has both `substrates: null` and `products: null` |
| `missing_observed_expr` | Observed variable is missing its `expression` field |
| `event_var_undeclared` | Variable in event affects/conditions is not declared |

---

## 4. Editing Operations

Beyond expression-level substitution, libraries must support model-level editing:

### 4.1 Variable Operations

- `add_variable(model, name, variable)` — add a new variable to a model.
- `remove_variable(model, name)` — remove a variable (and warn/error if referenced in equations).
- `rename_variable(model, old_name, new_name)` — rename everywhere: variables, equations, events, coupling references.

### 4.2 Equation Operations

- `add_equation(model, equation)` — append an equation.
- `remove_equation(model, index_or_lhs)` — remove by index or by LHS match.
- `substitute_in_equations(model, bindings)` — apply substitution across all equations in a model.

### 4.3 Reaction Operations

- `add_reaction(system, reaction)` — add a reaction to a reaction system.
- `remove_reaction(system, id)` — remove by reaction ID.
- `add_species(system, name, species)` — add a species.
- `remove_species(system, name)` — remove a species (warn if used in reactions).

### 4.4 Event Operations

- `add_continuous_event(model, event)` — add a continuous event.
- `add_discrete_event(model, event)` — add a discrete event.
- `remove_event(model, name)` — remove by event name.

### 4.5 Coupling Operations

- `add_coupling(file, entry)` — add a coupling rule.
- `remove_coupling(file, index)` — remove by index.
- `compose(file, system_a, system_b)` — convenience: create an `operator_compose` entry.
- `map_variable(file, from, to, transform)` — convenience: create a `variable_map` entry.

### 4.6 Model-Level Operations

- `merge(file_a, file_b) → EsmFile` — merge two ESM files, combining models, reaction systems, and coupling.
- `extract(file, component_name) → EsmFile` — extract a single model or reaction system into a standalone file.
- `derive_odes(reaction_system) → Model` — generate the ODE model from a reaction system's stoichiometry and rate laws.
- `stoichiometric_matrix(reaction_system) → Matrix` — compute the net stoichiometric matrix.

### 4.7 Coupling Resolution

Libraries that support simulation (Julia, Python) or coupled system assembly must implement coupling resolution — the process of combining individual models, reaction systems, data loaders, and operators into a single system according to the coupling rules. Libraries at the Core tier do not need to resolve coupling but must understand the semantics for validation and graph construction.

**Resolution order:** The order of entries in the `coupling` array does not affect the final result. Coupling rules are commutative — the same mathematical system is produced regardless of the order in which rules are applied. (This matches the behavior of EarthSciMLBase.jl, which is tested across all permutations of system ordering.)

However, for deterministic intermediate representations (e.g., variable naming), libraries should process coupling entries in array order.

#### 4.7.1 `operator_compose` Algorithm

`operator_compose` merges two ODE systems by matching time derivatives on the left-hand side and adding right-hand side terms together. This is the primary mechanism for adding physical processes (advection, diffusion, deposition) to chemical or dynamical systems.

**Algorithm:**

1. **Extract dependent variables.** For each equation in both systems, extract the dependent variable from the LHS:
   - If the LHS is `D(var, t)`, the dependent variable is `var`.
   - Otherwise, the dependent variable is the LHS expression itself.

2. **Apply translations.** If a `translate` map is provided, build a mapping from system A variable names to system B variable names (with optional conversion factors). Translations use scoped references (e.g., `"ChemModel.ozone": "PhotolysisModel.O3"`).

3. **Match equations.** For each equation in system A, find a matching equation in system B by comparing dependent variables:
   - **Direct match:** Both equations have `D(x, t)` on the LHS with the same variable name `x`.
   - **Translation match:** The translate map maps A's variable to B's variable.
   - **Placeholder expansion:** If system B's equation uses the `_var` placeholder (e.g., `D(_var, t) = ...`), it matches _every_ state variable in system A. The placeholder equation is cloned once per matched variable, with `_var` substituted for the actual variable name.

4. **Combine matched equations.** For each matched pair:
   - The final equation for variable `x` has the original LHS: `D(x, t)`.
   - The RHS is the sum of both systems' RHS expressions: `rhs_A + factor * rhs_B`, where `factor` is the conversion factor from the translate map (default 1).
   - Variables from system B that appear in the combined RHS are added to the merged system's variable list.

5. **Preserve unmatched equations.** Equations in either system that have no match are included in the merged system unchanged.

**Placeholder expansion example:** Given system A (a reaction system with species O₃, NO, NO₂) composed with system B (advection with equation `D(_var)/dt = -u·∂_var/∂x - v·∂_var/∂y`), the result contains three advection equations:

```
D(O₃)/dt  = [chemistry RHS for O₃]  + (-u·∂O₃/∂x  - v·∂O₃/∂y)
D(NO)/dt  = [chemistry RHS for NO]  + (-u·∂NO/∂x   - v·∂NO/∂y)
D(NO₂)/dt = [chemistry RHS for NO₂] + (-u·∂NO₂/∂x  - v·∂NO₂/∂y)
```

#### 4.7.2 `couple2` Semantics

`couple2` provides bidirectional coupling between two systems via a `ConnectorSystem` — a set of explicit equations that define how variables in one system affect the other.

In Julia, `couple2` uses multiple dispatch on `coupletype` metadata to select the coupling method. **In non-Julia languages, dispatch is not needed** because the ESM file's `connector` field already contains the fully specified coupling equations. The `coupletype_pair` field is informational (identifying which Julia dispatch method produced the coupling) but the `connector.equations` array is the complete specification.

**Resolution algorithm for `couple2`:**

1. Read the `connector.equations` array.
2. For each connector equation:
   - Resolve the `from` and `to` scoped references to their respective systems and variables.
   - Apply the coupling based on the `transform` type:
     - `additive`: Add the `expression` as a source/sink term to the target variable's ODE RHS.
     - `multiplicative`: Multiply the target variable's existing ODE RHS by the `expression`.
     - `replacement`: Replace the target variable's value with the `expression` (used for algebraic constraints).
3. Variables referenced across systems become shared — the coupled system includes both systems' variables.

#### 4.7.3 `variable_map` Resolution

`variable_map` replaces a parameter in one system with a variable provided by another system (typically a data loader).

1. Resolve the `from` scoped reference to the source system and variable.
2. Resolve the `to` scoped reference to the target system and parameter.
3. Apply the transform:
   - `param_to_var`: The target parameter is promoted from a constant to a time-varying variable whose value comes from the source. In the merged system, the parameter is removed from the target's parameter list and becomes a shared variable.
   - `identity`: Direct assignment without type change.
   - `additive`: The source value is added to the target variable's equation RHS.
   - `multiplicative`: The target variable's equation RHS is multiplied by the source value.
   - `conversion_factor`: Same as `param_to_var` but the source value is multiplied by the `factor` field before assignment.

#### 4.7.4 `operator_apply` and `callback` Resolution

These coupling types register runtime-specific components. Libraries record them in the coupled system metadata but cannot resolve their behavior (they are opaque references to runtime implementations). For validation, libraries verify that the referenced operator or callback ID exists in the file's `operators` section or is a known registered ID.

### 4.8 Graph Representations

Every library must be able to produce two distinct graph representations of an `.esm` file. These graphs are **data-only**: libraries return language-idiomatic adjacency structures (nodes, edges, connectivity) but do **not** render, lay out, or visualize the graph. Rendering is the sole concern of downstream consumers (`esm-editor`'s `<CouplingGraph>` component, CLI export to DOT/Mermaid, or user code).

#### 4.8.1 System Graph (Component-Level)

A directed graph where **nodes are model components** (models, reaction systems, data loaders, operators) and **edges are coupling rules**.

```
component_graph(file: EsmFile) → Graph<ComponentNode, CouplingEdge>
```

**Nodes:**

| Node type | Source |
|---|---|
| `model` | Each key in `models` |
| `reaction_system` | Each key in `reaction_systems` |
| `data_loader` | Each key in `data_loaders` |
| `operator` | Each key in `operators` |

Each node carries its name, type, and summary metadata (variable count, equation count, species count, etc.).

**Edges:**

Each coupling entry produces one or more directed edges:

| Coupling type | Edge(s) |
|---|---|
| `operator_compose` | Bidirectional edge between the two systems |
| `couple2` | Bidirectional edge between the two systems, labeled with coupletype pair |
| `variable_map` | Directed edge from source to target (e.g., `GEOSFP → SimpleOzone`), labeled with the mapped variable |
| `operator_apply` | Directed edge from operator to the system(s) it modifies |
| `callback` | Edge from callback to the system it targets |
| `event` (cross-system) | Directed edge(s) from condition variables' systems to affected variables' systems |

Each edge carries the coupling type, a human-readable label (e.g., `"T"` for a temperature variable map), and the full coupling entry for detail views.

**Example output** for the MinimalChemAdvection file:

```
Nodes: [SimpleOzone (reaction_system), Advection (model), GEOSFP (data_loader)]
Edges:
  SimpleOzone ←operator_compose→ Advection
  GEOSFP —[T]→ SimpleOzone          (variable_map)
  GEOSFP —[u]→ Advection            (variable_map)
  GEOSFP —[v]→ Advection            (variable_map)
```

This is the graph that `esm-editor`'s `<CouplingGraph>` component renders visually.

#### 4.8.2 Expression Graph (Variable-Level)

A directed graph where **nodes are variables and parameters** and **edges are mathematical dependencies** extracted from equations.

```
expression_graph(file: EsmFile) → Graph<VariableNode, DependencyEdge>
expression_graph(model: Model) → Graph<VariableNode, DependencyEdge>
expression_graph(system: ReactionSystem) → Graph<VariableNode, DependencyEdge>
expression_graph(equation: Equation) → Graph<VariableNode, DependencyEdge>
expression_graph(reaction: Reaction) → Graph<VariableNode, DependencyEdge>
expression_graph(expr: Expr) → Graph<VariableNode, DependencyEdge>
```

The function can be called at any level of granularity:

- **File:** Merges all systems and resolves coupling into cross-system edges.
- **Model / Reaction system:** Graph for a single component.
- **Equation:** Graph for one equation — the LHS variable as the target, all RHS free variables as sources.
- **Reaction:** Graph for one reaction — substrates, products, and rate parameters as nodes, stoichiometric and rate edges between them.
- **Expression:** Graph for an arbitrary expression — every variable in the expression becomes a node, and the tree structure is flattened into dependency edges. This is useful for inspecting a single rate law or a complex subexpression.

**Nodes:**

Every variable, parameter, and species that appears in any equation or reaction. Each node carries:

- `name: string` — variable name (scoped if from a file-level graph)
- `kind: "state" | "parameter" | "observed" | "species"` — the variable's role
- `units: string | null`
- `system: string` — which model/reaction system owns it

**Edges:**

For each equation `D(x)/dt = f(a, b, c, ...)`, create directed edges from each free variable in the RHS to the LHS variable:

- `a → x` with label `"D(x)/dt"` (meaning: `a` influences the time derivative of `x`)

For reaction systems, edges are derived from the stoichiometry:

- For reaction `NO + O₃ →[k] NO₂`: edges `NO → NO₂`, `O₃ → NO₂`, `NO → NO` (self-loss), `O₃ → O₃` (self-loss), `k → NO₂`, `k → NO`, `k → O₃`.

More precisely, for each reaction, every species and parameter appearing in the rate expression or as a substrate gets an edge to every species whose concentration changes.

Edges carry:

- `source: string` — the influencing variable
- `target: string` — the influenced variable
- `relationship: "additive" | "multiplicative" | "rate" | "stoichiometric"` — how the dependency arises
- `equation_index: number | null` — which equation/reaction produced this edge
- `expression: Expr | null` — the relevant subexpression (optional, for detail views)

**Coupled file-level graph:** When called on a full `EsmFile`, the expression graph resolves coupling rules to create cross-system edges. A `variable_map` from `GEOSFP.T` to `SimpleOzone.T` merges those into a single node (or creates an identity edge, depending on the `merge_coupled` option). An `operator_compose` adds the operator model's RHS dependencies to the target system's variables.

**Example output** for the SimpleOzone reaction system:

```
Nodes: [O₃ (species), NO (species), NO₂ (species), T (param), jNO₂ (param)]
Edges:
  NO  → O₃  (stoichiometric, R1: loss)
  O₃  → O₃  (stoichiometric, R1: loss)
  NO  → NO₂ (stoichiometric, R1: production)
  O₃  → NO₂ (stoichiometric, R1: production)
  T   → O₃  (rate, R1: k(T) in rate expression)
  T   → NO₂ (rate, R1: k(T) in rate expression)
  NO₂ → NO  (stoichiometric, R2: production)
  NO₂ → O₃  (stoichiometric, R2: production)
  jNO₂→ NO  (rate, R2)
  jNO₂→ O₃  (rate, R2)
```

#### 4.8.3 Graph Data Structure

Libraries should return graphs in their language's idiomatic structure. The minimum interface:

```
Graph<N, E>:
  nodes: List<N>
  edges: List<{source: N, target: N, data: E}>
  adjacency(node: N) → List<{neighbor: N, edge: E}>
  predecessors(node: N) → List<N>
  successors(node: N) → List<N>
```

Libraries should also support serializing graphs to common interchange formats (as strings, not rendered images):

- **DOT** (Graphviz) — for piping to `dot` or other layout engines
- **JSON adjacency list** — for web consumption
- **Mermaid** — for embedding in Markdown documentation

---

## 5. Language-Specific Libraries

### 5.1 Julia — `ESMFormat.jl`

**Tier: Full**

Julia is the primary language for EarthSciML and has the richest integration story. This library bridges ESM files and the ModelingToolkit/Catalyst/EarthSciML ecosystem.

#### 5.1.1 Dependencies

- `JSON3.jl` — JSON parsing/serialization
- `JSONSchema.jl` — schema validation
- `ModelingToolkit.jl` — symbolic ODE systems
- `Catalyst.jl` — reaction networks
- `Unitful.jl` or `DynamicQuantities.jl` — unit checking
- `EarthSciMLBase.jl` — coupled system assembly (for Full tier)

#### 5.1.2 Core API

```julia
using ESMFormat

# Load and save
file = ESMFormat.load("model.esm")
ESMFormat.save(file, "model_v2.esm")

# Pretty-print a model
display(file.models["SuperFast"])
# Output:
#   ∂O₃/∂t = −k_NO_O₃·O₃·NO·M + jNO₂·NO₂
#   ∂NO₂/∂t = k_NO_O₃·O₃·NO·M − jNO₂·NO₂

# LaTeX
ESMFormat.to_latex(file.models["SuperFast"])

# Print entire file summary
show(file)
# Output:
#   ESM v0.1.0: MinimalChemAdvection
#   Models: Advection (2 params, 1 eq)
#   Reactions: SimpleOzone (3 species, 2 params, 2 rxns)
#   Data Loaders: GEOSFP (u, v, T)
#   Coupling: 4 rules
#   Domain: lon [-130, -100], 2024-05-01 to 2024-05-03

# Validation
result = ESMFormat.validate(file)
result.is_valid          # true
result.structural_errors # []
result.unit_warnings     # [UnitWarning("k_NO_O3 units cm^3/molec/s may be inconsistent...")]

# Substitution
new_model = substitute(file.models["SuperFast"], Dict("T" => 300.0))

# Derive ODEs from reactions
odes = derive_odes(file.reaction_systems["SimpleOzone"])

# Stoichiometric matrix
S = stoichiometric_matrix(file.reaction_systems["SimpleOzone"])
```

#### 5.1.3 MTK/Catalyst Conversion (Full Tier)

The key capability unique to Julia: bidirectional conversion between ESM and live MTK/Catalyst objects.

```julia
# ESM → MTK
sys = to_mtk_system(file.models["SuperFast"])
# Returns an ODESystem with symbolic variables, equations, and events

# ESM → Catalyst
rsys = to_catalyst_system(file.reaction_systems["SimpleOzone"])
# Returns a ReactionSystem with species, parameters, reactions

# MTK → ESM
model = from_mtk_system(my_ode_system; name="MyModel")
# Extracts equations, variables, parameters, events from an ODESystem

# Catalyst → ESM
rxn_sys = from_catalyst_system(my_reaction_system; name="MyReactions")

# Full coupled system
coupled = to_coupled_system(file)
# Returns an EarthSciMLBase.CoupledSystem with all coupling rules applied
# This handles: operator_compose, couple2, variable_map, operator_apply

# Simulate
using OrdinaryDiffEq
prob = ODEProblem(coupled, file.domain)
sol = solve(prob, Tsit5())
```

#### 5.1.4 Expression Mapping

| ESM AST | MTK/Symbolics.jl |
|---|---|
| `{"op": "D", "args": ["O3"], "wrt": "t"}` | `Differential(t)(O3)` |
| `{"op": "+", "args": ["a", "b"]}` | `a + b` |
| `{"op": "exp", "args": ["x"]}` | `exp(x)` |
| `{"op": "Pre", "args": ["x"]}` | `Pre(x)` |
| `{"op": "grad", "args": ["x"], "dim": "y"}` | `Differential(y)(x)` |
| `{"op": "ifelse", "args": [cond, a, b]}` | `ifelse(cond, a, b)` |
| `"O3"` (string) | `@variables O3(t)` |
| `3.14` (number) | `3.14` (literal) |

#### 5.1.5 Event Mapping

| ESM Event | MTK Callback |
|---|---|
| Continuous event | `SymbolicContinuousCallback` |
| Discrete event (condition) | `SymbolicDiscreteCallback` with boolean condition |
| Discrete event (periodic) | `SymbolicDiscreteCallback` with `PeriodicCallback` |
| Discrete event (preset_times) | `SymbolicDiscreteCallback` with `PresetTimeCallback` |
| `affect_neg` | `SymbolicContinuousCallback(conditions, affect, affect_neg=...)` |
| `discrete_parameters` | `SymbolicDiscreteCallback(...; discrete_parameters=[p])` |
| Functional affect | `(affect!, [vars...], [params...], [discretes...], ctx)` tuple registered by `handler_id` |

---

### 5.2 TypeScript / SolidJS — `esm-format` + `esm-editor`

**Tier: Core + Analysis (esm-format), Interactive Editing (esm-editor)**

The web story is split into two packages with a clean dependency boundary:

- **`esm-format`** — Pure TypeScript, zero framework dependencies. Types, parsing, validation, substitution, LaTeX/Unicode string generation. Usable in any JS/TS environment (Node, Deno, Bun, browser, web workers).
- **`esm-editor`** — SolidJS-based interactive expression and model editor. Renders the AST directly as clickable, editable DOM elements. Exported as both Solid components and framework-agnostic web components.

#### 5.2.1 Why SolidJS for the Editor

The expression editor is fundamentally a tree of reactive nodes. When a user clicks a variable in a 200-term equation and replaces it, only that node and its ancestors need to update. This maps directly to Solid's reactivity model:

- **Granular reactivity:** Each AST node is a signal. Editing one node updates only its DOM element — no virtual DOM diffing of the entire expression tree.
- **`createStore` with path-based updates:** `setStore("args", 1, "args", 0, "op", "+")` maps naturally to AST path manipulation.
- **No re-render cascade:** React would re-render the whole expression tree on any edit (or require extensive `memo` boundaries at every node). Solid updates in place.
- **Small bundle:** The editor component adds ~7KB gzipped (Solid runtime) vs ~40KB+ (React).
- **Web component export:** Solid components compile to native custom elements via `solid-element`, making them embeddable in React, Vue, Svelte, plain HTML, or the seshat.pub platform without framework coupling.

#### 5.2.2 `esm-format` — Pure TypeScript Library

**Dependencies:** `ajv` (schema validation). No framework, no DOM.

```
esm-format/
├── src/
│   ├── types.ts          # TypeScript type definitions matching JSON Schema
│   ├── parse.ts          # JSON → typed EsmFile
│   ├── serialize.ts      # EsmFile → JSON
│   ├── expression.ts     # Expr type, construction, traversal
│   ├── pretty-print.ts   # Unicode, LaTeX, ASCII string formatters
│   ├── substitute.ts     # Expression and model-level substitution
│   ├── validate.ts       # Schema + structural + unit validation
│   ├── units.ts          # Unit parsing and dimensional analysis
│   ├── reactions.ts      # Stoichiometric matrix, ODE derivation
│   ├── edit.ts           # Model editing operations
│   ├── codegen.ts        # Julia/Python code generation from ESM
│   └── index.ts          # Public API
├── schema/
│   └── esm.schema.json   # Bundled JSON Schema
├── tests/
└── package.json
```

**Core API:**

```typescript
import {
  load, save, validate,
  substitute, freeVariables,
  deriveODEs, stoichiometricMatrix,
  toLatex, toUnicode, toAscii,
  type EsmFile, type Expr, type Model
} from 'esm-format';

// Parse from JSON string or object
const file: EsmFile = load(jsonString);

// Serialize back
const json: string = save(file);

// Pretty-print to strings (no DOM, no framework)
console.log(toUnicode(file.models!['SuperFast']));
// ∂O₃/∂t = −k_NO_O₃·O₃·NO·M + jNO₂·NO₂

const latex: string = toLatex(file.models!['SuperFast']);
// \frac{\partial \mathrm{O_3}}{\partial t} = ...

// Validate
const result = validate(file);
console.log(result.isValid);           // true
console.log(result.structuralErrors);  // []

// Substitute
const modified = substitute(file.models!['SuperFast'], { T: 300.0 });

// Free variables in an expression
const vars: Set<string> = freeVariables(expr);

// Derive ODEs from reactions
const odeModel: Model = deriveODEs(file.reactionSystems!['SimpleOzone']);

// Stoichiometric matrix
const S: number[][] = stoichiometricMatrix(file.reactionSystems!['SimpleOzone']);

// Generate Julia code for backend simulation
const juliaCode: string = toJuliaCode(file);
```

**Type definitions:**

```typescript
// Expression AST
type Expr = number | string | ExprNode;

interface ExprNode {
  op: string;
  args: Expr[];
  wrt?: string;  // for D
  dim?: string;  // for grad
}

// Discriminated union for coupling
type CouplingEntry =
  | { type: 'operator_compose'; systems: [string, string]; translate?: Record<string, TranslateTarget>; description?: string }
  | { type: 'couple2'; systems: [string, string]; coupletype_pair: [string, string]; connector: Connector; description?: string }
  | { type: 'variable_map'; from: string; to: string; transform: string; factor?: number; description?: string }
  | { type: 'operator_apply'; operator: string; description?: string }
  | { type: 'callback'; callback_id: string; config?: Record<string, unknown>; description?: string }
  | { type: 'event'; event_type: 'continuous' | 'discrete'; /* ... */ };

// Discrete event trigger - discriminated union
type DiscreteEventTrigger =
  | { type: 'condition'; expression: Expr }
  | { type: 'periodic'; interval: number; initial_offset?: number }
  | { type: 'preset_times'; times: number[] };
```

Types should be auto-generated from the JSON Schema where possible (using `json-schema-to-typescript`), then augmented with utility functions.

#### 5.2.3 `esm-editor` — SolidJS Interactive Editor

**Dependencies:** `solid-js`, `solid-element` (web component export), `esm-format` (peer dependency).

```
esm-editor/
├── src/
│   ├── components/
│   │   ├── ExpressionNode.tsx    # Core: renders a single AST node
│   │   ├── ExpressionEditor.tsx  # Composes nodes into a full expression
│   │   ├── EquationEditor.tsx    # LHS = RHS with editable sides
│   │   ├── ModelEditor.tsx       # Full model: variables + equations + events
│   │   ├── ReactionEditor.tsx    # Reaction system editor
│   │   ├── CouplingGraph.tsx     # Visual coupling diagram
│   │   ├── ValidationPanel.tsx   # Live validation feedback
│   │   └── FileSummary.tsx       # Overview of entire ESM file
│   ├── primitives/
│   │   ├── ast-store.ts          # Solid store wrapping EsmFile
│   │   ├── selection.ts          # Selected AST node tracking
│   │   ├── highlighted-var.ts    # Cross-equation variable highlight on hover
│   │   ├── history.ts            # Undo/redo stack
│   │   └── validation.ts         # Reactive validation signals
│   ├── layout/
│   │   ├── fraction.tsx          # CSS fraction layout
│   │   ├── superscript.tsx       # Exponent positioning
│   │   ├── subscript.tsx         # Chemical subscript
│   │   ├── radical.tsx           # Square root rendering
│   │   └── delimiters.tsx        # Parentheses with auto-sizing
│   ├── web-components.ts         # Custom element registration
│   └── index.ts                  # Public API
├── tests/
└── package.json
```

#### 5.2.4 `ExpressionNode` — The Core Component

Every AST node renders as a Solid component that knows its own path, handles click/hover events, and uses CSS for math-like layout. This is the key design — no KaTeX, no MathJax, no static rendering. The math _is_ the editor.

```tsx
// Conceptual structure — each AST node is an interactive component
import { Component, Show, For, createSignal } from 'solid-js';
import type { Expr, ExprNode } from 'esm-format';

interface ExpressionNodeProps {
  expr: Expr;                      // reactive (from Solid store)
  path: (string | number)[];       // AST path for this node
  highlightedVars: Accessor<Set<string>>;   // currently highlighted equivalence class
  onHoverVar: (name: string | null) => void; // set/clear hovered variable
  onSelect: (path: (string | number)[]) => void;
  onReplace: (path: (string | number)[], newExpr: Expr) => void;
}

const ExpressionNodeComponent: Component<ExpressionNodeProps> = (props) => {
  const [hovered, setHovered] = createSignal(false);

  // Number literal
  if (typeof props.expr === 'number') {
    return (
      <span
        class="esm-num"
        classList={{ 'esm-hovered': hovered() }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={() => props.onSelect(props.path)}
      >
        {formatNumber(props.expr)}
      </span>
    );
  }

  // Variable reference
  if (typeof props.expr === 'string') {
    const isHighlighted = () => props.highlightedVars().has(props.expr);
    return (
      <span
        class="esm-var"
        classList={{
          'esm-hovered': hovered(),
          'esm-var-highlighted': isHighlighted(),
        }}
        onMouseEnter={() => { setHovered(true); props.onHoverVar(props.expr); }}
        onMouseLeave={() => { setHovered(false); props.onHoverVar(null); }}
        onClick={() => props.onSelect(props.path)}
      >
        {renderChemicalName(props.expr)}  {/* O3 → O₃ */}
      </span>
    );
  }

  // Operator node — dispatch to layout components
  return <OperatorLayout node={props.expr} path={props.path} {...props} />;
};
```

**Layout components** handle the visual math rendering:

```tsx
// Fraction layout for division
const FractionLayout: Component<{num: Expr; den: Expr; path: ...}> = (props) => (
  <span class="esm-frac">
    <span class="esm-frac-num">
      <ExpressionNodeComponent expr={props.num} path={[...props.path, 'args', 0]} />
    </span>
    <span class="esm-frac-bar" />
    <span class="esm-frac-den">
      <ExpressionNodeComponent expr={props.den} path={[...props.path, 'args', 1]} />
    </span>
  </span>
);

// Derivative layout: ∂O₃/∂t rendered as fraction
const DerivativeLayout: Component<{node: ExprNode; path: ...}> = (props) => (
  <span class="esm-deriv">
    <span class="esm-frac">
      <span class="esm-frac-num">∂<ExpressionNodeComponent expr={props.node.args[0]} ... /></span>
      <span class="esm-frac-bar" />
      <span class="esm-frac-den">∂{props.node.wrt}</span>
    </span>
  </span>
);
```

**CSS handles math typography** — no canvas, no SVG, just styled spans:

```css
.esm-frac {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  vertical-align: middle;
}
.esm-frac-bar {
  width: 100%;
  height: 1px;
  background: currentColor;
  margin: 1px 0;
}
.esm-frac-num, .esm-frac-den {
  padding: 0 2px;
  font-size: 0.85em;
}
.esm-var {
  font-style: italic;
  cursor: pointer;
  transition: background 0.1s ease;
}
.esm-var:hover, .esm-hovered {
  background: rgba(59, 130, 246, 0.1);
  border-radius: 2px;
}
.esm-var-highlighted {
  background: rgba(250, 204, 21, 0.25);
  border-radius: 2px;
  box-shadow: 0 0 0 1px rgba(250, 204, 21, 0.5);
}
.esm-var-highlighted.esm-hovered {
  background: rgba(250, 204, 21, 0.4);
}
.esm-selected {
  background: rgba(59, 130, 246, 0.2);
  outline: 1px solid rgb(59, 130, 246);
  border-radius: 2px;
}
.esm-num {
  font-variant-numeric: tabular-nums;
  cursor: pointer;
}
```

#### 5.2.5 Interaction Model

**Variable hover highlighting:** Hovering over any variable name highlights _every_ occurrence of that variable across all visible equations. This works across equation boundaries — hover `O₃` in one equation and every `O₃` in the model lights up in yellow. The highlight is driven by a `highlightedVars` signal shared across all `ExpressionNode` instances:

```typescript
import { createSignal, createMemo } from 'solid-js';
import type { EsmFile } from 'esm-format';

// Build equivalence classes from coupling rules at file load / on coupling change
function buildVarEquivalences(file: EsmFile): Map<string, Set<string>> {
  const groups = new UnionFind<string>();

  for (const entry of file.coupling ?? []) {
    if (entry.type === 'variable_map') {
      // GEOSFP.T → SimpleOzone.T means these are the same quantity
      groups.union(entry.from, entry.to);
    }
    if (entry.type === 'operator_compose' && entry.translate) {
      for (const [from, to] of Object.entries(entry.translate)) {
        const toVar = typeof to === 'string' ? to : to.var;
        groups.union(from, toVar);
      }
    }
  }

  // Return a map: any variable name → all equivalent names
  return groups.toEquivalenceMap();
}

// One signal per editor scope
const equivalences = createMemo(() => buildVarEquivalences(file));
const [hoveredVar, setHoveredVar] = createSignal<string | null>(null);

// The set of names to highlight — includes all equivalent variables
const highlightedVars = createMemo(() => {
  const v = hoveredVar();
  if (!v) return new Set<string>();
  return equivalences().get(v) ?? new Set([v]);
});

// Each ExpressionNode checks membership in the set
// isHighlighted = () => highlightedVars().has(props.expr)
```

**Highlighting passes through equalities.** The coupling section defines which variables across different models refer to the same physical quantity. When `variable_map` maps `GEOSFP.T` to `SimpleOzone.T`, or `operator_compose` translates `SuperFast.O3` to `Advection._var`, these form equivalence classes. Hovering any member of an equivalence class highlights all members that are currently visible.

Concretely: if the file contains `{ "type": "variable_map", "from": "GEOSFP.T", "to": "SimpleOzone.T" }`, then hovering `T` in the SimpleOzone model also highlights `T` in the GEOSFP data loader panel and `GEOSFP.T` / `SimpleOzone.T` in the coupling graph. The user sees the full data flow path for that quantity.

Equivalence classes are computed once (and reactively recomputed when coupling rules change) using a union-find structure. The `highlightedVars` memo produces a `Set<string>` so that each `ExpressionNode`'s `isHighlighted()` check is an O(1) set lookup, not a traversal.

The highlight scoping is configurable:
- **Model scope** (default): Highlight within the current model or reaction system. Equivalences are not resolved — only literal name matches.
- **File scope:** Highlight across all models with equivalence resolution. This is the mode where hovering `T` in one model lights up every coupled `T` everywhere. This is the most useful mode for understanding data flow.
- **Equation scope:** Highlight only within the current equation.

Scoped references are normalized: both `O3` (bare) and `SimpleOzone.O3` (qualified) are recognized as the same variable when the context model is `SimpleOzone`. For subsystems, the full path is used: `SimpleOzone.GasPhase.O3` refers to variable `O3` in subsystem `GasPhase` of `SimpleOzone`.

**Selection:** Click any AST node to select it. The selected node is highlighted and its AST path is exposed. A detail panel shows the node's type, value, parent context, and available actions.

**Inline editing:** Double-click a number to type a new value. Double-click a variable to get an autocomplete dropdown of available variables. Changes propagate through the Solid store and trigger revalidation.

**Structural editing:** Select a node, then:
- **Replace:** Type a new expression or pick from a palette.
- **Wrap:** Wrap the selected node in an operator (e.g., select `O3`, click "negate" → `−O3`).
- **Unwrap:** If the selected node is a unary op, replace it with its argument.
- **Delete:** Remove a term from a sum/product (adjusting the parent node).
- **Drag-and-drop:** Reorder terms in commutative operations (addition, multiplication).

**Expression palette:** A sidebar with common operations — derivatives, common functions, arithmetic operators, chemical species from the current model. Drag from palette to expression to insert.

**Store architecture:**

```typescript
import { createStore, produce } from 'solid-js/store';
import type { EsmFile } from 'esm-format';
import { validate } from 'esm-format';

const [file, setFile] = createStore<EsmFile>(loadedFile);

// Path-based update — only the affected node re-renders
function replaceNode(path: (string | number)[], newExpr: Expr) {
  setFile(...pathToStoreArgs(path), newExpr);
  // Solid automatically updates only the affected ExpressionNode
}

// Example: replace the rate of reaction R1
setFile('reaction_systems', 'SimpleOzone', 'reactions', 0, 'rate', {
  op: '*',
  args: [2.0e-12, { op: 'exp', args: [{ op: '/', args: [-1400, 'T'] }] }]
});

// Validation runs reactively
const validationResult = createMemo(() => validate(file));
```

**Undo/redo:**

```typescript
import { createUndoHistory } from './primitives/history';

const { undo, redo, canUndo, canRedo } = createUndoHistory(file, setFile);
// Each setFile call is automatically captured as a history entry
```

#### 5.2.6 Web Component Export

`esm-editor` components are exported as standard web components via `solid-element`, making them embeddable in any framework:

```typescript
// web-components.ts
import { customElement } from 'solid-element';
import { ExpressionEditor } from './components/ExpressionEditor';
import { ModelEditor } from './components/ModelEditor';

customElement('esm-expression-editor', { expr: {}, onChange: () => {} }, ExpressionEditor);
customElement('esm-model-editor', { model: {}, onChange: () => {} }, ModelEditor);
customElement('esm-file-editor', { file: {}, onChange: () => {} }, FileEditor);
```

Usage in plain HTML:
```html
<esm-expression-editor
  expr='{"op": "+", "args": ["a", "b"]}'
  onchange="handleChange(event.detail)"
/>
```

Usage in React (via wrapper or directly as custom element):
```jsx
<esm-model-editor
  ref={el => { el.model = myModel; el.addEventListener('change', handleChange); }}
/>
```

Usage in the seshat.pub platform or any other framework — no adapter needed.

#### 5.2.7 Higher-Level Editor Components

Beyond individual expressions, `esm-editor` provides composed editors for entire sections:

**`<ModelEditor>`** — Displays all equations in a model with editable variables panel, equation list, and event editor. Variables show type badges (state/parameter/observed) and units.

**`<ReactionEditor>`** — Reaction system editor showing reactions in chemical notation (`NO + O₃ →[k₁] NO₂`) with clickable rate expressions. Add/remove reactions via UI.

**`<CouplingGraph>`** — Visual directed graph of model components and their coupling relationships. Nodes are models/reaction systems/data loaders; edges are coupling entries. Click an edge to edit the coupling rule. Consumes the data-only graph structure from `esm-format`'s `component_graph()` and handles layout and rendering internally (e.g., using `d3-force` for layout, Solid for DOM rendering).

**`<FileSummary>`** — Read-only overview panel showing the structured summary (as specified in Section 6.3 of this document), with links that scroll to / select the relevant editor section.

**`<ValidationPanel>`** — Reactive panel showing schema errors, structural errors, and unit warnings. Updates live as the user edits. Clicking an error highlights the offending node in the expression editor.

#### 5.2.8 Code Generation

The pure `esm-format` library (not the editor) provides code generation for backend simulation. Code generation covers **models and reaction systems** — their variables, parameters, equations, reactions, and events. Coupling, domain, and solver configuration are emitted as structured comments or stubs that the user can complete manually.

**Scope:** Code generation must handle:

- Model variables (state, parameter, observed) with units and defaults.
- Model equations (ODE equations with full expression translation).
- Reaction system species, parameters, and reactions.
- Events (continuous and discrete) with affect equations.

Code generation does **not** need to handle (these are emitted as TODO comments):

- Coupling resolution (the generated code defines individual systems; the user composes them).
- Domain and solver setup (emitted as commented-out boilerplate with values from the file).
- Data loaders and operators (runtime-specific; emitted as placeholder comments with the loader/operator ID).

```typescript
import { toJuliaCode, toPythonCode } from 'esm-format';

// Generate a self-contained Julia script
const julia: string = toJuliaCode(file);
// Output:
//   using ModelingToolkit, Catalyst, EarthSciMLBase, OrdinaryDiffEq
//   @parameters T = 298.15 [unit = u"K"] jNO2 = 0.005 [unit = u"1/s"]
//   @species O3(t) = 40e-9 NO(t) = 0.1e-9 NO2(t) = 1e-9
//   rxs = [
//     Reaction(1.8e-12 * exp(-1370/T), [NO, O3], [NO2]),
//     Reaction(jNO2, [NO2], [NO, O3]),
//   ]
//   @named sys = ReactionSystem(rxs, t)
//   # TODO: Coupling — operator_compose(SimpleOzone, Advection)
//   # TODO: Domain — lon [-130, -100], 2024-05-01 to 2024-05-03
//   # TODO: Solver — strang_threads(Rosenbrock23, dt=1.0)

// Generate a self-contained Python script
const python: string = toPythonCode(file);
// Output:
//   import esm_format as esm
//   file = esm.load_string('''...''')
//   solution = esm.simulate(file, tspan=(0, 86400), ...)
```

**Expression-to-code mapping:**

| ESM AST | Julia output | Python output |
|---|---|---|
| `{"op": "+", "args": ["a", "b"]}` | `a + b` | `a + b` |
| `{"op": "*", "args": ["k", "A", "B"]}` | `k * A * B` | `k * A * B` |
| `{"op": "D", "args": ["O3"], "wrt": "t"}` | `D(O3)` | `Derivative(O3(t), t)` |
| `{"op": "exp", "args": [x]}` | `exp(x)` | `sp.exp(x)` |
| `{"op": "ifelse", "args": [c, a, b]}` | `ifelse(c, a, b)` | `sp.Piecewise((a, c), (b, True))` |
| `{"op": "Pre", "args": ["x"]}` | `Pre(x)` | `Function('Pre')(x)` |
| `{"op": "^", "args": ["x", 2]}` | `x^2` | `x**2` |
| `{"op": "grad", "args": ["x"], "dim": "y"}` | `Differential(y)(x)` | `sp.Derivative(x, y)` |

---

### 5.3 Python — `esm_format`

**Tier: Core + Analysis + Simulation**

Python provides simulation capability via SymPy for symbolic manipulation and SciPy for numerical integration.

#### 5.3.1 Dependencies

- `jsonschema` — schema validation
- `sympy` — symbolic math, expression representation, ODE solving
- `scipy` — numerical ODE integration (`solve_ivp`)
- `pint` — unit validation
- `numpy` — numerical arrays

#### 5.3.2 Package Structure

```
esm_format/
├── __init__.py
├── types.py          # Dataclass definitions for ESM types
├── parse.py          # JSON → dataclasses
├── serialize.py      # Dataclasses → JSON
├── expression.py     # Expr ↔ SymPy conversion, pretty-print
├── substitute.py     # Substitution operations
├── validate.py       # Schema + structural + unit validation
├── units.py          # Pint-based unit checking
├── reactions.py      # Stoichiometric matrix, ODE derivation
├── edit.py           # Model editing operations
├── simulate.py       # SymPy → SciPy ODE solver bridge
└── display.py        # IPython/Jupyter display integration
```

#### 5.3.3 Core API

```python
import esm_format as esm

# Load and save
file = esm.load("model.esm")
esm.save(file, "model_v2.esm")

# Pretty-print (uses sympy.pretty or LaTeX)
print(esm.to_unicode(file.models["SuperFast"]))
# ∂O₃/∂t = −k_NO_O₃·O₃·NO·M + jNO₂·NO₂

print(esm.to_latex(file.models["SuperFast"]))
# \frac{\partial O_3}{\partial t} = ...

# In Jupyter notebooks — rich display
file.models["SuperFast"]  # renders LaTeX equations inline

# Validate
result = esm.validate(file)
assert result.is_valid
print(result.unit_warnings)

# Substitute
modified = esm.substitute(file.models["SuperFast"], {"T": 300.0})

# Derive ODEs
ode_model = esm.derive_odes(file.reaction_systems["SimpleOzone"])
```

#### 5.3.4 SymPy Integration

The Python library converts ESM expressions to SymPy `Expr` objects and back:

| ESM AST | SymPy |
|---|---|
| `{"op": "D", "args": ["O3"], "wrt": "t"}` | `Derivative(O3(t), t)` |
| `{"op": "+", "args": ["a", "b"]}` | `a + b` |
| `{"op": "exp", "args": [{"op": "/", "args": [-1370, "T"]}]}` | `exp(-1370/T)` |
| `{"op": "Pre", "args": ["x"]}` | `Function('Pre')(x)` (custom) |
| `{"op": "*", "args": [1.8e-12, "O3", "NO"]}` | `1.8e-12 * O3 * NO` |
| `{"op": "ifelse", "args": [c, a, b]}` | `Piecewise((a, c), (b, True))` |
| `"O3"` (string) | `Symbol('O3')` or `Function('O3')(t)` |

```python
# Convert ESM expression to SymPy
sympy_expr = esm.to_sympy(esm_expression)

# Convert SymPy expression back to ESM
esm_expr = esm.from_sympy(sympy_expr)

# Use SymPy's simplify
simplified = esm.simplify(esm_expression)  # wraps sympy.simplify

# Symbolic Jacobian
J = esm.jacobian(file.models["SuperFast"])  # returns SymPy Matrix
```

#### 5.3.5 Simulation via SciPy

For ODE models and reaction systems, the Python library can generate a numerical RHS function and solve:

```python
# Simulate a model
solution = esm.simulate(
    file,
    tspan=(0, 86400),      # 1 day in seconds
    parameters={"T": 298.15, "jNO2": 0.005},
    initial_conditions={"O3": 40e-9, "NO": 0.1e-9, "NO2": 1e-9},
    method="BDF",           # scipy.integrate.solve_ivp method
)

# solution is a scipy OdeResult-like object
print(solution.t)     # time points
print(solution.y)     # state trajectories
print(solution.vars)  # ["O3", "NO", "NO2"]

# Plot
solution.plot()  # matplotlib integration
```

**Implementation approach:**

1. Resolve all coupling (`variable_map`, `operator_compose`) to produce a single combined ODE system.
2. Convert all expressions to SymPy.
3. For reaction systems, generate mass-action ODEs from stoichiometry.
4. Use `sympy.lambdify()` to create a fast NumPy-callable RHS function.
5. Optionally generate a symbolic Jacobian and lambdify it for stiff solvers.
6. Call `scipy.integrate.solve_ivp()`.

**Event handling in SciPy:**

| ESM event type | SciPy mechanism |
|---|---|
| Continuous event | `solve_ivp` `events` parameter (zero-crossing functions) |
| Discrete (condition) | Manual stepping with condition check |
| Discrete (periodic) | Manual stepping at fixed intervals |
| Discrete (preset_times) | Use `t_eval` combined with manual affect application |

Since SciPy's event handling is less sophisticated than DifferentialEquations.jl, the Python simulation tier has limitations:

- Direction-dependent affects (`affect_neg`) require custom zero-crossing direction detection.
- Discrete events with complex triggers require manual integration loop management.
- Functional affects are not supported (they are runtime-specific).
- Spatial operators (grad, laplacian) are not supported — simulation is limited to 0D (box model) ODE systems.

#### 5.3.6 Jupyter Integration

```python
# In Jupyter, ESM objects have rich _repr_latex_ methods
file.models["SuperFast"]  # renders equations as LaTeX

# Interactive model explorer
esm.explore(file)  # widget showing models, reactions, coupling graph
```

---

### 5.4 Rust — `esm-format`

**Tier: Core + Analysis**

Rust provides a high-performance, memory-safe implementation suitable for CLI tools, WASM compilation (for web), and embedding in other systems.

#### 5.4.1 Dependencies

- `serde` + `serde_json` — serialization
- `jsonschema` — schema validation
- `wasm-bindgen` — optional, for WASM target

#### 5.4.2 Crate Structure

```
esm-format/
├── src/
│   ├── lib.rs
│   ├── types.rs        # Struct definitions with serde derives
│   ├── expression.rs   # Expr enum, pretty-print, substitution
│   ├── validate.rs     # Schema + structural validation
│   ├── units.rs        # Unit parsing and checking
│   ├── reactions.rs    # Stoichiometric matrix
│   ├── edit.rs         # Editing operations
│   └── display.rs      # Unicode/LaTeX formatters
├── Cargo.toml
└── tests/
```

#### 5.4.3 Key Design Decisions

**Expression type as an enum:**

```rust
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum Expr {
    Num(f64),
    Var(String),
    Node(ExprNode),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ExprNode {
    pub op: String,
    pub args: Vec<Expr>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub wrt: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub dim: Option<String>,
}
```

**Coupling as a tagged enum:**

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum CouplingEntry {
    #[serde(rename = "operator_compose")]
    OperatorCompose { systems: [String; 2], translate: Option<HashMap<String, TranslateTarget>>, description: Option<String> },
    #[serde(rename = "variable_map")]
    VariableMap { from: String, to: String, transform: String, description: Option<String> },
    // ... etc
}
```

#### 5.4.4 WASM Target

The Rust library can be compiled to WASM and used by the TypeScript library for performance-critical operations (validation, large expression manipulation). The TypeScript library would use the pure-TS implementation by default but optionally delegate to WASM:

```typescript
import { validate } from 'esm-format';
import { validate as validateWasm } from 'esm-format-wasm'; // optional fast path
```

#### 5.4.5 CLI Tool

The Rust crate should also produce a CLI binary:

```bash
# Validate an ESM file
esm validate model.esm

# Pretty-print
esm display model.esm
esm display model.esm --format=latex

# Extract a single model
esm extract model.esm --component=SuperFast > superfast.esm

# Diff two ESM files (semantic diff)
esm diff model_v1.esm model_v2.esm

# Generate stoichiometric matrix
esm stoich model.esm --system=SimpleOzone

# System graph (component-level)
esm graph model.esm                          # DOT format to stdout
esm graph model.esm --format=mermaid         # Mermaid format
esm graph model.esm --format=json            # JSON adjacency list
esm graph model.esm | dot -Tsvg > graph.svg  # pipe to Graphviz

# Expression graph (variable-level)
esm graph model.esm --level=expression                           # all systems merged
esm graph model.esm --level=expression --system=SimpleOzone      # single system
esm graph model.esm --level=expression --format=mermaid

# Convert between formats
esm convert model.esm --to=messagepack  # future binary format
```

---

### 5.5 Go — `esm-format` (Optional)

**Tier: Core**

Go is useful for server-side tooling, CI/CD validation, and API backends.

#### 5.5.1 Minimal Scope

- Parse/serialize ESM files using standard `encoding/json`.
- Schema validation via `gojsonschema`.
- Pretty-print to Unicode and LaTeX.
- Structural validation (equation counting, reference checks).
- Substitution.

No simulation capability. The Go library serves as a validation and transformation layer in backend services.

---

## 6. Display Format Specification

All libraries must produce identical output for a given display format when given the same input. This section specifies the exact rendering rules.

### 6.1 Unicode Display

**Chemical species subscripts:** Digits following chemical element symbols become subscripts. Libraries must use an **element-aware tokenizer** that recognizes chemical element symbols (one uppercase letter optionally followed by one lowercase letter, matching entries in the periodic table) and subscripts trailing digits.

**Algorithm:**

1. Split the name on underscores into segments (e.g., `k_NO_O3` → `["k", "NO", "O3"]`).
2. For each segment, scan left-to-right matching the pattern `[A-Z][a-z]?` against a lookup table of chemical element symbols (H, He, Li, Be, B, C, N, O, F, Ne, Na, Mg, Al, Si, P, S, Cl, Ar, K, Ca, …all 118 elements).
3. If a match is found and is immediately followed by one or more digits, convert those digits to Unicode subscript characters (₀₁₂₃₄₅₆₇₈₉).
4. If a segment does not start with a recognized element symbol, leave it unchanged (e.g., `k` → `k`, `var2` → `var2`).
5. Rejoin segments with underscores (for Unicode) or `\_` (for LaTeX).

| Input | Output | Reasoning |
|---|---|---|
| `O3` | `O₃` | `O` is oxygen, `3` subscripted |
| `NO2` | `NO₂` | `N` is nitrogen, `O` is oxygen, `2` follows `O` |
| `CH2O` | `CH₂O` | `C` is carbon, `H` is hydrogen, `2` follows `H`, `O` is oxygen |
| `H2O2` | `H₂O₂` | Both digit groups follow element symbols |
| `k_NO_O3` | `k_NO_O₃` | `k` is not an element, `N`/`O` are elements, `3` follows `O` |
| `var2` | `var2` | `V` could be vanadium but `va` is not followed by a digit after an element match; `var` doesn't start with a valid element+digit pattern |
| `T` | `T` | No trailing digits |
| `jNO2` | `jNO₂` | `j` is not an element, skip; `N` is nitrogen, `O` is oxygen, `2` follows `O` |

**Note:** The element lookup table must be included in each library (a static list of 118 symbol strings). The algorithm is greedy — it tries to match two-character element symbols before one-character symbols (e.g., `Ca` matches calcium before `C` matches carbon).

**Number formatting:** Numbers in Unicode display use the following rules:

| Condition | Format | Example |
|---|---|---|
| Integer (no fractional part) | Plain integer | `3`, `−1`, `1000` |
| Decimal, 1–4 significant digits | Decimal notation | `0.005`, `298.15` |
| \|value\| < 0.01 or \|value\| ≥ 10000 | Scientific notation with Unicode superscripts | `1.8×10⁻¹²`, `2.46×10¹⁹` |
| Exactly 0.0 | `0` | `0` |

For LaTeX, use `\times 10^{...}` for scientific notation. For ASCII, use `e` notation (e.g., `1.8e-12`).

**Operators:**

| AST | Unicode |
|---|---|
| `D(x, t)` | `∂x/∂t` |
| `grad(x, y)` | `∂x/∂y` |
| `a * b` | `a·b` |
| `-a` (unary) | `−a` (minus sign, not hyphen) |
| `a + (-b)` | `a − b` |
| `Pre(x)` | `Pre(x)` |

**Precedence rules** (highest to lowest):

1. Function application: `f(x)`
2. Exponentiation: `x^n` → `xⁿ` (for small integer exponents) or `x^(expr)`
3. Unary minus: `−x`
4. Multiplication/Division: `a·b`, `a/b`
5. Addition/Subtraction: `a + b`, `a − b`

Parentheses are only added when necessary for disambiguation.

### 6.2 LaTeX Display

Follow standard LaTeX math conventions. Fractions use `\frac{}{}`, derivatives use `\frac{\partial}{\partial t}`, species names use `\mathrm{}`.

### 6.3 Model Summary Display

When displaying a full model or file, show a structured summary:

```
ESM v0.1.0: MinimalChemAdvection
  "O3-NO-NO2 chemistry with advection and external meteorology"
  Authors: Chris Tessum

  Reaction Systems:
    SimpleOzone (3 species, 3 parameters, 2 reactions)
      R1: NO + O₃ → NO₂    rate: 1.8×10⁻¹² · exp(−1370/T) · M
      R2: NO₂ → NO + O₃    rate: jNO₂

  Models:
    Advection (2 parameters, 1 equation)
      ∂_var/∂t = −u_wind·∂_var/∂x − v_wind·∂_var/∂y

  Data Loaders:
    GEOSFP: u, v, T (gridded_data)

  Coupling:
    1. operator_compose: SimpleOzone + Advection
    2. variable_map: GEOSFP.T → SimpleOzone.T
    3. variable_map: GEOSFP.u → Advection.u_wind
    4. variable_map: GEOSFP.v → Advection.v_wind

  Domain: lon [−130, −100] (Δ0.3125°), 2024-05-01 to 2024-05-03
  Solver: strang_threads (Rosenbrock23, dt=1.0)
```

---

## 7. Testing Requirements

### 7.1 Conformance Test Suite

A language-independent test suite ensures all libraries produce consistent results. The test suite is a collection of `.esm` files paired with expected outputs:

```
tests/
├── valid/
│   ├── minimal_chemistry.esm          # minimal valid file
│   ├── full_coupled.esm               # exercises all sections
│   ├── events_all_types.esm           # all event variants
│   ├── reaction_system_only.esm       # no models section
│   └── model_only.esm                 # no reaction_systems section
├── invalid/
│   ├── missing_esm_version.esm        # schema error
│   ├── unknown_variable_ref.esm       # structural error
│   ├── equation_count_mismatch.esm    # more states than equations
│   ├── invalid_trigger_type.esm       # bad discrete event trigger
│   └── circular_coupling.esm          # coupling references nonexistent system
├── display/
│   ├── expr_precedence.json           # expression → expected Unicode/LaTeX
│   ├── chemical_subscripts.json       # species name → expected display
│   └── model_summary.json            # file → expected summary string
├── substitution/
│   ├── simple_var_replace.json        # input expr + bindings → expected output
│   ├── nested_substitution.json
│   └── scoped_reference.json
├── graphs/
│   ├── system_graph.json              # file → expected nodes + edges (component level)
│   ├── expression_graph.json          # file → expected nodes + edges (variable level)
│   ├── coupled_expression_graph.json  # file with coupling → merged variable graph
│   └── expected_dot/                  # expected DOT output for each test case
│       ├── system_graph.dot
│       └── expression_graph.dot
└── simulation/
    ├── box_model_ozone.esm            # simple ODE, expected trajectory
    ├── bouncing_ball.esm              # continuous events
    └── expected/
        ├── box_model_ozone.csv        # t, O3, NO, NO2 columns
        └── bouncing_ball.csv
```

### 7.2 Test Fixture Authoring

The conformance test suite must be authored as a standalone, language-independent artifact stored in the `EarthSciSerialization` repository alongside the schema and specs. Test fixtures are **not** generated from any single library implementation — they are the canonical source of truth.

**Minimum fixture set for Phase 1 (required before cross-language conformance testing):**

1. **`valid/minimal_chemistry.esm`** — The `MinimalChemAdvection` example from the format spec (Section 13). This is the baseline test: every library must parse, validate, pretty-print, and round-trip this file identically.
2. **`valid/events_all_types.esm`** — A file exercising continuous events (with `affect_neg`, `root_find`), discrete events (condition, periodic, preset_times), discrete parameters, and a functional affect.
3. **`invalid/missing_esm_version.esm`** and **`invalid/unknown_variable_ref.esm`** — Minimal files that fail schema and structural validation respectively, with expected error codes documented in a companion `expected_errors.json`.
4. **`display/expr_precedence.json`** — Array of `{input: Expression, unicode: string, latex: string}` triples covering: operator precedence (nested `+`/`*`/`^`), chemical subscripts, derivatives, Pre operator, scientific notation numbers.
5. **`substitution/simple_var_replace.json`** — Array of `{input: Expression, bindings: object, expected: Expression}` triples.

Each expected output must be reviewed and agreed upon before being committed, since it defines the conformance standard.

### 7.3 Round-Trip Tests

For every valid `.esm` file: `load(save(load(file))) == load(file)`. JSON key ordering and whitespace may differ, but the parsed data model must be identical.

### 7.4 Cross-Language Tests

Periodically, the CI runs the same test suite across Julia, TypeScript, Python, and Rust and compares outputs. Failures indicate divergence in rendering or validation logic.

---

## 8. Versioning and Compatibility

### 8.1 Schema Version

The `"esm"` field in each file specifies the schema version. Libraries must:

- Reject files with a major version they don't support.
- Accept files with a minor version ≤ their supported minor version (backward compatible).
- Warn on files with a higher minor version (forward compatible — unknown fields ignored). Since the JSON Schema uses `additionalProperties: false` for strict validation at a specific version, libraries must **skip JSON Schema validation** for files whose minor version exceeds the library's supported version and rely on structural validation only.

### 8.2 Library Versions

Libraries follow semver independently of the schema version. Each library's documentation specifies which schema versions it supports.

### 8.3 Migration

When the schema version changes, each library should provide a migration function:

```
migrate(file: EsmFile, target_version: string) → EsmFile
```

---

## 9. Implementation Priority

### Phase 1: Foundation (All Languages)

1. Type definitions / data model.
2. JSON parse / serialize with schema validation.
3. Expression pretty-printing (Unicode + LaTeX).
4. Expression substitution.
5. Structural validation (equation counting, reference integrity).
6. Round-trip tests passing.

### Phase 2: Analysis

7. Unit parsing and dimensional checking.
8. `derive_odes` from reaction systems.
9. `stoichiometric_matrix` computation.
10. System graph (component-level) and expression graph (variable-level).
11. Graph export (DOT, Mermaid, JSON).
12. Model editing operations.
13. Conformance test suite passing across all languages.

### Phase 3: Simulation

14. Julia: MTK/Catalyst bidirectional conversion.
15. Julia: coupled system assembly.
16. Python: SymPy expression conversion.
17. Python: SciPy-backed box model simulation.
18. Python: event handling in simulation.

### Phase 4: Ecosystem

19. Rust: WASM compilation for web use.
20. Rust: CLI tool.
21. `esm-format`: Julia and Python code generation.
22. `esm-editor`: `ExpressionNode` component with click-to-select, hover highlight, CSS math layout.
23. `esm-editor`: Inline editing (double-click numbers/variables), autocomplete.
24. `esm-editor`: Structural editing (wrap/unwrap/delete/drag-reorder).
25. `esm-editor`: Expression palette sidebar.
26. `esm-editor`: `ModelEditor`, `ReactionEditor` composed components.
27. `esm-editor`: `CouplingGraph` visualization.
28. `esm-editor`: `ValidationPanel` with error-to-node linking.
29. `esm-editor`: Undo/redo history.
30. `esm-editor`: Web component export via `solid-element`.
31. Julia: full EarthSciML integration (data loaders, operators, spatial simulation).

---

## 10. Outstanding Issues

The following items are acknowledged gaps in this specification. They do not block Phase 1 or Phase 2 implementation and will be addressed in subsequent revisions.

| Issue | Affected area | Notes |
|---|---|---|
| `derive_odes` algorithm not fully specified | Section 4.6 | Standard mass-action kinetics ODE generation from stoichiometry + rate laws. Need to specify handling of source reactions (null substrates), sink reactions (null products), and constraint equations. |
| Stoichiometric matrix convention not stated | Section 4.6 | Must specify: species × reactions (rows × columns), net stoichiometry (products − substrates). |
| Expression graph edge rules for reactions are ambiguous | Section 4.8.2 | The rule for which nodes get edges (self-loops, rate parameter edges) needs a precise algorithm, not just an example. |
| Unit string parsing grammar undefined | Section 3.3 | Unit strings are free-form. A formal grammar or recognized-token list (including `molec`, `ppb`, `ppm`) would improve cross-language consistency. |
| Python simulation with spatial operators | Section 5.3.5 | Coupling resolution with `operator_compose` involving spatial derivatives (grad, laplacian) is not meaningful for 0D simulation. The spec should clarify that Python simulation skips spatial terms or raises an error. |
| Code generation templates underspecified | Section 5.2.8 | Exact rules for emitting parameter defaults, unit strings (Julia `u"..."`, Python `pint`), and boilerplate structure need more detail. |
| `esm-editor` CSS theming / dark mode | Section 5.2.4 | No specification for CSS custom properties or theme customization. |
| Concurrency / thread safety | All libraries | Not addressed. Relevant for Julia (multi-threaded solvers) and Rust (Send/Sync bounds). |

---

## 11. Summary Table

| Capability | Julia | TS `esm-format` | Solid `esm-editor` | Python | Rust | Go |
|---|---|---|---|---|---|---|
| Parse / serialize | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Schema validation | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Unicode pretty-print | ✓ | ✓ (string) | ✓ (DOM) | ✓ | ✓ | ✓ |
| LaTeX pretty-print | ✓ | ✓ (string) | — | ✓ | ✓ | ✓ |
| Substitution | ✓ | ✓ | ✓ (interactive) | ✓ | ✓ | ✓ |
| Structural validation | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Unit validation | ✓ | ✓ | — | ✓ | ✓ | — |
| Derive ODEs from reactions | ✓ | ✓ | — | ✓ | ✓ | — |
| Stoichiometric matrix | ✓ | ✓ | — | ✓ | ✓ | — |
| System graph (component) | ✓ | ✓ | ✓ (visual) | ✓ | ✓ | ✓ |
| Expression graph (variable) | ✓ | ✓ | ✓ (visual) | ✓ | ✓ | ✓ |
| Graph export (DOT/Mermaid) | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Model editing (programmatic) | ✓ | ✓ | — | ✓ | ✓ | — |
| Click-to-edit expressions | — | — | ✓ | — | — | — |
| Drag-and-drop reordering | — | — | ✓ | — | — | — |
| Expression palette | — | — | ✓ | — | — | — |
| Undo/redo | — | — | ✓ | — | — | — |
| Coupling graph visualization | — | — | ✓ | — | — | — |
| Live validation panel | — | — | ✓ | — | — | — |
| Web component export | — | — | ✓ | — | — | — |
| MTK ↔ ESM conversion | ✓ | — | — | — | — | — |
| Catalyst ↔ ESM conversion | ✓ | — | — | — | — | — |
| Coupled system assembly | ✓ | — | — | — | — | — |
| 0D simulation (box model) | ✓ | — | — | ✓ | — | — |
| Spatial simulation | ✓ | — | — | — | — | — |
| Event simulation | ✓ | — | — | partial | — | — |
| WASM target | — | — | — | — | ✓ | — |
| CLI tool | — | — | — | — | ✓ | — |
| Julia code generation | — | ✓ | — | — | — | — |
| Python code generation | — | ✓ | — | — | — | — |
| Jupyter integration | — | — | — | ✓ | — | — |
