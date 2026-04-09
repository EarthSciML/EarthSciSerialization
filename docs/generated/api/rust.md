# Rust API Reference

Complete API reference for the ESM Format Rust library.

## Functions

### add_continuous_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:442`

**Signature:**
```rust
pub fn add_continuous_event(model: &Model, event: ContinuousEvent) -> EditResult<Model> {
```

**Description:**
Add a continuous event to a model

# Arguments

* `model` - The model to modify
* `event` - The continuous event to add

# Returns

* `EditResult<Model>` - New model with the added continuous event

**Available in other languages:**
- [Julia](julia.md#add_continuous_event)
- [Julia](julia.md#add_continuous_event)

---

### add_coupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:494`

**Signature:**
```rust
pub fn add_coupling(esm_file: &EsmFile, coupling: CouplingEntry) -> EditResult<EsmFile> {
```

**Description:**
Add a coupling entry to an ESM file

# Arguments

* `esm_file` - The ESM file to modify
* `coupling` - The coupling entry to add

# Returns

* `EditResult<EsmFile>` - New ESM file with the added coupling entry

**Available in other languages:**
- [Julia](julia.md#add_coupling)
- [Julia](julia.md#add_coupling)

---

### add_discrete_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:390`

**Signature:**
```rust
pub fn add_discrete_event(model: &Model, event: DiscreteEvent) -> EditResult<Model> {
```

**Description:**
Add a discrete event to a model

# Arguments

* `model` - The model to modify
* `event` - The discrete event to add

# Returns

* `EditResult<Model>` - New model with the added discrete event

**Available in other languages:**
- [Julia](julia.md#add_discrete_event)
- [Julia](julia.md#add_discrete_event)

---

### add_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:155`

**Signature:**
```rust
pub fn add_equation(model: &Model, equation: Equation) -> EditResult<Model> {
```

**Description:**
Add an equation to a model

# Arguments

* `model` - The model to modify
* `equation` - The equation to add

# Returns

* `EditResult<Model>` - New model with the added equation

**Available in other languages:**
- [Julia](julia.md#add_equation)
- [Julia](julia.md#add_equation)

---

### add_model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:58`

**Signature:**
```rust
pub fn add_model(esm_file: &EsmFile, model_id: &str, model: Model) -> EditResult<EsmFile> {
```

**Description:**
Add a new model to an ESM file

# Arguments

* `esm_file` - The ESM file to modify
* `model_id` - Unique identifier for the new model
* `model` - The model to add

# Returns

* `EditResult<EsmFile>` - New ESM file with the added model

---

### add_reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:291`

**Signature:**
```rust
pub fn add_reaction(system: &ReactionSystem, reaction: Reaction) -> EditResult<ReactionSystem> {
```

**Description:**
Add a reaction to a reaction system

# Arguments

* `system` - The reaction system to modify
* `reaction` - The reaction to add

# Returns

* `EditResult<ReactionSystem>` - New reaction system with the added reaction

**Available in other languages:**
- [Julia](julia.md#add_reaction)
- [Julia](julia.md#add_reaction)

---

### add_reaction_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:213`

**Signature:**
```rust
pub fn add_reaction_system(esm_file: &EsmFile, system_id: &str, system: ReactionSystem) -> EditResult<EsmFile> {
```

**Description:**
Add a reaction system to an ESM file

# Arguments

* `esm_file` - The ESM file to modify
* `system_id` - Unique identifier for the new reaction system
* `system` - The reaction system to add

# Returns

* `EditResult<EsmFile>` - New ESM file with the added reaction system

---

### add_species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:244`

**Signature:**
```rust
pub fn add_species(system: &ReactionSystem, species: Species) -> EditResult<ReactionSystem> {
```

**Description:**
Add a species to a reaction system

# Arguments

* `system` - The reaction system to modify
* `species` - The species to add

# Returns

* `EditResult<ReactionSystem>` - New reaction system with the added species

**Available in other languages:**
- [Julia](julia.md#add_species)
- [Julia](julia.md#add_species)

---

### add_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:114`

**Signature:**
```rust
pub fn add_variable(model: &Model, var_name: &str, variable: ModelVariable) -> EditResult<Model> {
```

**Description:**
Add a variable to a model

# Arguments

* `model` - The model to modify
* `var_name` - Name of the new variable
* `variable` - The variable to add

# Returns

* `EditResult<Model>` - New model with the added variable

**Available in other languages:**
- [Julia](julia.md#add_variable)
- [Julia](julia.md#add_variable)

---

### add_vectors_simd

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:162`

**Signature:**
```rust
pub fn add_vectors_simd(a: &[f64], b: &[f64], result: &mut [f64]) -> Result<(), PerformanceError> {
```

**Description:**
SIMD-optimized vector addition

---

### alloc_slice

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:264`

**Signature:**
```rust
pub fn alloc_slice<T>(&self, len: usize) -> &mut [T]
```

**Description:**
Allocate a slice for storing intermediate results

---

### allocated_bytes

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:277`

**Signature:**
```rust
pub fn allocated_bytes(&self) -> usize {
```

**Description:**
Get current allocated bytes

---

### analyze_conservation_violation_simd

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/reactions.rs:845`

**Signature:**
```rust
pub fn analyze_conservation_violation_simd(
```

---

### base

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/units.rs:57`

**Signature:**
```rust
pub fn base(dimension: Dimension, power: i32, scale: f64) -> Self {
```

**Description:**
Create a unit with a single dimension

**Available in other languages:**
- [Python](python.md#base)
- [Python](python.md#base)
- [Python](python.md#base)
- [Python](python.md#base)
- [Python](python.md#base)
- [Python](python.md#base)
- [Python](python.md#base)
- [Python](python.md#base)
- [Python](python.md#base)

---

### benchmark_parsing

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:291`

**Signature:**
```rust
pub fn benchmark_parsing(json_str: &str, iterations: u32) -> Result<f64, JsValue> {
```

---

### can_migrate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/migration.rs:206`

**Signature:**
```rust
pub fn can_migrate(from_version: &str, to_version: &str) -> bool {
```

**Description:**
Check if migration is supported between two versions

**Available in other languages:**
- [Julia](julia.md#can_migrate)

---

### check_dimensional_consistency

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/units.rs:255`

**Signature:**
```rust
pub fn check_dimensional_consistency(lhs_unit: &Unit, rhs_unit: &Unit) -> Result<(), UnitError> {
```

**Description:**
Check dimensional consistency of an equation

# Arguments

* `lhs_unit` - Units of the left-hand side
* `rhs_unit` - Units of the right-hand side

# Returns

* `Result<(), UnitError>` - Ok if consistent, error otherwise

---

### component_exists

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:183`

**Signature:**
```rust
pub fn component_exists(esm_file: &EsmFile, component_id: &str) -> bool {
```

**Description:**
Check if a component exists in the ESM file

# Arguments

* `esm_file` - The ESM file to check
* `component_id` - The component ID to look for

# Returns

* `true` if the component exists, `false` otherwise

---

### component_graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:257`

**Signature:**
```rust
pub fn component_graph(json_str: &str) -> Result<JsValue, JsValue> {
```

**Available in other languages:**
- [Julia](julia.md#component_graph)
- [Julia](julia.md#component_graph)
- [Typescript](typescript.md#component_graph)

---

### component_graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:60`

**Signature:**
```rust
pub fn component_graph(esm_file: &EsmFile) -> ComponentGraph {
```

**Description:**
Build a component graph from an ESM file

# Arguments

* `esm_file` - The ESM file to analyze

# Returns

* Component graph showing structure and coupling

**Available in other languages:**
- [Julia](julia.md#component_graph)
- [Julia](julia.md#component_graph)
- [Typescript](typescript.md#component_graph)

---

### compute_batch_conservation_weights_simd

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/reactions.rs:816`

**Signature:**
```rust
pub fn compute_batch_conservation_weights_simd(
```

---

### compute_conservation_weights_simd

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/reactions.rs:787`

**Signature:**
```rust
pub fn compute_conservation_weights_simd(
```

---

### compute_stoichiometric_matrix

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:242`

**Signature:**
```rust
pub fn compute_stoichiometric_matrix(reaction_system_str: &str) -> Result<JsValue, JsValue> {
```

---

### compute_stoichiometric_matrix_parallel

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:96`

**Signature:**
```rust
pub fn compute_stoichiometric_matrix_parallel(
```

**Description:**
Parallel stoichiometric matrix computation

---

### contains

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/expression.rs:47`

**Signature:**
```rust
pub fn contains(expr: &Expr, var_name: &str) -> bool {
```

**Description:**
Check if an expression contains a specific variable

# Arguments

* `expr` - The expression to search
* `var_name` - The variable name to look for

# Returns

* `true` if the variable is found, `false` otherwise

**Available in other languages:**
- [Julia](julia.md#contains)
- [Julia](julia.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Python](python.md#contains)
- [Typescript](typescript.md#contains)

---

### convert_units

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/units.rs:276`

**Signature:**
```rust
pub fn convert_units(value: f64, from_unit: &Unit, to_unit: &Unit) -> Result<f64, UnitError> {
```

**Description:**
Convert between compatible units

# Arguments

* `value` - Value to convert
* `from_unit` - Source unit
* `to_unit` - Target unit

# Returns

* `Result<f64, UnitError>` - Converted value or error

**Available in other languages:**
- [Python](python.md#convert_units)
- [Python](python.md#convert_units)

---

### create_compact_expression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:226`

**Signature:**
```rust
pub fn create_compact_expression(expr_str: &str) -> Result<JsValue, JsValue> {
```

---

### derive_odes

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/reactions.rs:51`

**Signature:**
```rust
pub fn derive_odes(system: &ReactionSystem) -> Result<Model, DeriveError> {
```

**Description:**
Generate ODE model from a reaction system

Converts a reaction system into an ODE model with species as state variables
and reactions contributing to their derivatives using mass action kinetics.

Mass action kinetics: rate law = k * product(substrates^stoichiometry)
Net stoichiometry = products - substrates
d[species]/dt = sum(net_stoichiometry * rate_law)

# Arguments

* `system` - The reaction system to convert

# Returns

* `Result<Model, DeriveError>` - ODE model with species as state variables, or error

# Errors

Returns `DeriveError` for invalid stoichiometry, missing rate laws, or unit conversion issues.

**Available in other languages:**
- [Julia](julia.md#derive_odes)

---

### detect_conservation_violations

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/reactions.rs:477`

**Signature:**
```rust
pub fn detect_conservation_violations(system: &ReactionSystem) -> ConservationAnalysis {
```

**Description:**
Detect conservation law violations in a reaction system

Analyzes the reaction system for various types of conservation law violations
including mass balance within reactions and system-wide linear invariants.

# Arguments

* `system` - The reaction system to analyze

# Returns

* `ConservationAnalysis` - Detailed analysis of conservation laws and violations

# Examples

```rust
use esm_format::{ReactionSystem, detect_conservation_violations};

// Create a simple reaction system
let system = ReactionSystem {
name: Some("Test System".to_string()),
species: vec![],
parameters: std::collections::HashMap::new(),
reactions: vec![],
description: None,
};

let analysis = detect_conservation_violations(&system);
println!("Found {} violations", analysis.violations.len());
```

---

### dimensionless

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/units.rs:49`

**Signature:**
```rust
pub fn dimensionless() -> Self {
```

**Description:**
Create a dimensionless unit

---

### divide

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/units.rs:94`

**Signature:**
```rust
pub fn divide(&self, other: &Unit) -> Unit {
```

**Description:**
Divide two units

**Available in other languages:**
- [Python](python.md#divide)
- [Python](python.md#divide)

---

### dot_product_simd

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:214`

**Signature:**
```rust
pub fn dot_product_simd(a: &[f64], b: &[f64]) -> Result<f64, PerformanceError> {
```

**Description:**
SIMD-optimized dot product

---

### errors

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/validate.rs:30`

**Signature:**
```rust
pub fn errors(&self) -> Vec<StructuralError> {
```

**Description:**
Get all errors as a combined vector (for compatibility with old API)

**Available in other languages:**
- [Python](python.md#errors)

---

### evaluate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/expression.rs:69`

**Signature:**
```rust
pub fn evaluate(expr: &Expr, bindings: &HashMap<String, f64>) -> Result<f64, Vec<String>> {
```

**Description:**
Evaluate an expression with given variable values

# Arguments

* `expr` - The expression to evaluate
* `bindings` - Map from variable names to numeric values

# Returns

* `Ok(f64)` if evaluation succeeds
* `Err(Vec<String>)` with unbound variable names if evaluation fails

**Available in other languages:**
- [Julia](julia.md#evaluate)
- [Julia](julia.md#evaluate)
- [Python](python.md#evaluate)
- [Python](python.md#evaluate)
- [Python](python.md#evaluate)
- [Python](python.md#evaluate)
- [Python](python.md#evaluate)
- [Python](python.md#evaluate)
- [Python](python.md#evaluate)
- [Python](python.md#evaluate)
- [Python](python.md#evaluate)
- [Python](python.md#evaluate)
- [Python](python.md#evaluate)
- [Typescript](typescript.md#evaluate)

---

### evaluate_batch

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:79`

**Signature:**
```rust
pub fn evaluate_batch(
```

**Description:**
Evaluate multiple expressions in parallel

---

### evaluate_fast

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:340`

**Signature:**
```rust
pub fn evaluate_fast(&self, variables: &HashMap<String, f64>) -> Result<f64, PerformanceError> {
```

---

### expression_graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:335`

**Signature:**
```rust
pub fn expression_graph<T>(input: &T) -> ExpressionGraph
```

**Description:**
Build an expression graph from various ESM components

# Arguments

* `input` - Can be an ESM file, model, reaction system, equation, reaction, or expression

# Returns

* `ExpressionGraph` - Graph showing variable dependencies

**Available in other languages:**
- [Julia](julia.md#expression_graph)
- [Julia](julia.md#expression_graph)

---

### fast_parse

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:41`

**Signature:**
```rust
pub fn fast_parse(json_bytes: &mut [u8]) -> Result<EsmFile, PerformanceError> {
```

---

### fast_parse

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:49`

**Signature:**
```rust
pub fn fast_parse(json_str: &str) -> Result<EsmFile, PerformanceError> {
```

---

### free_parameters

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/expression.rs:33`

**Signature:**
```rust
pub fn free_parameters(expr: &Expr) -> HashSet<String> {
```

**Description:**
Extract all free parameters from an expression

This is currently the same as free_variables since we don't distinguish
parameters from variables at the expression level.

# Arguments

* `expr` - The expression to analyze

# Returns

* Set of parameter names referenced in the expression

---

### free_variables

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/expression.rs:15`

**Signature:**
```rust
pub fn free_variables(expr: &Expr) -> HashSet<String> {
```

**Description:**
Extract all free variables from an expression

# Arguments

* `expr` - The expression to analyze

# Returns

* Set of variable names referenced in the expression

**Available in other languages:**
- [Julia](julia.md#free_variables)
- [Julia](julia.md#free_variables)

---

### from_esm_file

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:248`

**Signature:**
```rust
pub fn from_esm_file(esm_file: &EsmFile) -> Self {
```

**Description:**
Create a new scoped context from an ESM file

---

### from_expr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:304`

**Signature:**
```rust
pub fn from_expr(expr: &Expr) -> Self {
```

**Description:**
Create a compact expression from a standard expression

**Available in other languages:**
- [Python](python.md#from_expr)
- [Python](python.md#from_expr)
- [Python](python.md#from_expr)
- [Python](python.md#from_expr)

---

### get_component_type

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:226`

**Signature:**
```rust
pub fn get_component_type(esm_file: &EsmFile, component_id: &str) -> Option<ComponentType> {
```

**Description:**
Get the type of a component

# Arguments

* `esm_file` - The ESM file to check
* `component_id` - The component ID to look for

# Returns

* `Some(ComponentType)` if the component exists
* `None` if the component doesn't exist

---

### get_performance_info

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:272`

**Signature:**
```rust
pub fn get_performance_info() -> JsValue {
```

---

### get_supported_migration_targets

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/migration.rs:224`

**Signature:**
```rust
pub fn get_supported_migration_targets(from_version: &str) -> Vec<String> {
```

**Description:**
Get supported migration paths from a given version

**Available in other languages:**
- [Julia](julia.md#get_supported_migration_targets)

---

### has_errors

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/validate.rs:25`

**Signature:**
```rust
pub fn has_errors(&self) -> bool {
```

**Description:**
Check if there are any errors (schema or structural)

---

### is_compatible

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/units.rs:66`

**Signature:**
```rust
pub fn is_compatible(&self, other: &Unit) -> bool {
```

**Description:**
Check if two units have compatible dimensions

**Available in other languages:**
- [Python](python.md#is_compatible)
- [Python](python.md#is_compatible)
- [Python](python.md#is_compatible)
- [Python](python.md#is_compatible)

---

### is_dimensionless

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/units.rs:71`

**Signature:**
```rust
pub fn is_dimensionless(&self) -> bool {
```

**Description:**
Check if this unit is dimensionless

**Available in other languages:**
- [Python](python.md#is_dimensionless)

---

### load

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:32`

**Signature:**
```rust
pub fn load(json_str: &str) -> Result<JsValue, JsValue> {
```

**Available in other languages:**
- [Julia](julia.md#load)
- [Julia](julia.md#load)
- [Julia](julia.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Typescript](typescript.md#load)

---

### load

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/parse.rs:82`

**Signature:**
```rust
pub fn load(json_str: &str) -> Result<EsmFile, EsmError> {
```

**Description:**
Load and parse an ESM file from JSON string

This function performs both JSON parsing and schema validation.
It will throw an error for malformed JSON or schema violations.

# Arguments

* `json_str` - The JSON string to parse

# Returns

* `Ok(EsmFile)` - Successfully parsed and validated ESM file
* `Err(EsmError)` - Parse error or schema validation error

# Examples

```rust
use esm_format::load;

let json = r#"
{
"esm": "0.1.0",
"metadata": {
"name": "test_model"
},
"models": {
"simple": {
"variables": {},
"equations": []
}
}
}
"#;

let esm_file = load(json).expect("Failed to load ESM file");
assert_eq!(esm_file.esm, "0.1.0");
```

**Available in other languages:**
- [Julia](julia.md#load)
- [Julia](julia.md#load)
- [Julia](julia.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Python](python.md#load)
- [Typescript](typescript.md#load)

---

### main

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:308`

**Signature:**
```rust
pub fn main() {
```

**Available in other languages:**
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)
- [Python](python.md#main)

---

### migrate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/migration.rs:154`

**Signature:**
```rust
pub fn migrate(file: &EsmFile, target_version: &str) -> Result<EsmFile, MigrationError> {
```

**Description:**
Migrate an ESM file to a target version

**Available in other languages:**
- [Julia](julia.md#migrate)

---

### multiply

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/units.rs:76`

**Signature:**
```rust
pub fn multiply(&self, other: &Unit) -> Unit {
```

**Description:**
Multiply two units

**Available in other languages:**
- [Python](python.md#multiply)
- [Python](python.md#multiply)
- [Python](python.md#multiply)
- [Python](python.md#multiply)
- [Python](python.md#multiply)
- [Python](python.md#multiply)
- [Python](python.md#multiply)
- [Python](python.md#multiply)
- [Python](python.md#multiply)
- [Python](python.md#multiply)

---

### multiply_vectors_simd

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:188`

**Signature:**
```rust
pub fn multiply_vectors_simd(a: &[f64], b: &[f64], result: &mut [f64]) -> Result<(), PerformanceError> {
```

**Description:**
SIMD-optimized element-wise multiplication

---

### new

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:63`

**Signature:**
```rust
pub fn new(num_threads: Option<usize>) -> Result<Self, PerformanceError> {
```

**Description:**
Create a new parallel evaluator with specified number of threads

**Available in other languages:**
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)

---

### new

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:250`

**Signature:**
```rust
pub fn new() -> Self {
```

**Description:**
Create a new model allocator with specified capacity

**Available in other languages:**
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)
- [Python](python.md#new)

---

### parse_unit

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/units.rs:141`

**Signature:**
```rust
pub fn parse_unit(unit_str: &str) -> Result<Unit, UnitError> {
```

**Description:**
Parse a unit string into a Unit struct

Supports common unit notations like:
- "m/s" (meters per second)
- "kg*m/s^2" (kilogram meters per second squared)
- "mol/L" (moles per liter)
- "1" or "" (dimensionless)

# Arguments

* `unit_str` - String representation of the unit

# Returns

* `Result<Unit, UnitError>` - Parsed unit or error

---

### power

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/units.rs:112`

**Signature:**
```rust
pub fn power(&self, exponent: i32) -> Unit {
```

**Description:**
Raise unit to a power

**Available in other languages:**
- [Python](python.md#power)
- [Python](python.md#power)
- [Python](python.md#power)
- [Python](python.md#power)
- [Python](python.md#power)
- [Python](python.md#power)
- [Python](python.md#power)

---

### remove_continuous_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:464`

**Signature:**
```rust
pub fn remove_continuous_event(model: &Model, index: usize) -> EditResult<Model> {
```

**Description:**
Remove a continuous event from a model by index

# Arguments

* `model` - The model to modify
* `index` - Index of the continuous event to remove

# Returns

* `EditResult<Model>` - New model without the continuous event

---

### remove_coupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:516`

**Signature:**
```rust
pub fn remove_coupling(esm_file: &EsmFile, index: usize) -> EditResult<EsmFile> {
```

**Description:**
Remove a coupling entry from an ESM file by index

# Arguments

* `esm_file` - The ESM file to modify
* `index` - Index of the coupling entry to remove

# Returns

* `EditResult<EsmFile>` - New ESM file without the coupling entry

**Available in other languages:**
- [Julia](julia.md#remove_coupling)
- [Julia](julia.md#remove_coupling)

---

### remove_discrete_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:412`

**Signature:**
```rust
pub fn remove_discrete_event(model: &Model, index: usize) -> EditResult<Model> {
```

**Description:**
Remove a discrete event from a model by index

# Arguments

* `model` - The model to modify
* `index` - Index of the discrete event to remove

# Returns

* `EditResult<Model>` - New model without the discrete event

---

### remove_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:171`

**Signature:**
```rust
pub fn remove_equation(model: &Model, index: usize) -> EditResult<Model> {
```

**Description:**
Remove an equation from a model by index

# Arguments

* `model` - The model to modify
* `index` - Index of the equation to remove

# Returns

* `EditResult<Model>` - New model without the equation

**Available in other languages:**
- [Julia](julia.md#remove_equation)
- [Julia](julia.md#remove_equation)

---

### remove_model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:89`

**Signature:**
```rust
pub fn remove_model(esm_file: &EsmFile, model_id: &str) -> EditResult<EsmFile> {
```

**Description:**
Remove a model from an ESM file

# Arguments

* `esm_file` - The ESM file to modify
* `model_id` - Identifier of the model to remove

# Returns

* `EditResult<EsmFile>` - New ESM file without the model

---

### remove_reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:307`

**Signature:**
```rust
pub fn remove_reaction(system: &ReactionSystem, index: usize) -> EditResult<ReactionSystem> {
```

**Description:**
Remove a reaction from a reaction system by index

# Arguments

* `system` - The reaction system to modify
* `index` - Index of the reaction to remove

# Returns

* `EditResult<ReactionSystem>` - New reaction system without the reaction

**Available in other languages:**
- [Julia](julia.md#remove_reaction)
- [Julia](julia.md#remove_reaction)

---

### remove_species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:268`

**Signature:**
```rust
pub fn remove_species(system: &ReactionSystem, species_name: &str) -> EditResult<ReactionSystem> {
```

**Description:**
Remove a species from a reaction system

# Arguments

* `system` - The reaction system to modify
* `species_name` - Name of the species to remove

# Returns

* `EditResult<ReactionSystem>` - New reaction system without the species

**Available in other languages:**
- [Julia](julia.md#remove_species)
- [Julia](julia.md#remove_species)

---

### remove_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:135`

**Signature:**
```rust
pub fn remove_variable(model: &Model, var_name: &str) -> EditResult<Model> {
```

**Description:**
Remove a variable from a model

# Arguments

* `model` - The model to modify
* `var_name` - Name of the variable to remove

# Returns

* `EditResult<Model>` - New model without the variable

**Available in other languages:**
- [Julia](julia.md#remove_variable)
- [Julia](julia.md#remove_variable)

---

### replace_coupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:547`

**Signature:**
```rust
pub fn replace_coupling(esm_file: &EsmFile, index: usize, coupling: CouplingEntry) -> EditResult<EsmFile> {
```

**Description:**
Replace a coupling entry in an ESM file

# Arguments

* `esm_file` - The ESM file to modify
* `index` - Index of the coupling entry to replace
* `coupling` - The new coupling entry

# Returns

* `EditResult<EsmFile>` - New ESM file with the replaced coupling entry

---

### replace_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:192`

**Signature:**
```rust
pub fn replace_equation(model: &Model, index: usize, equation: Equation) -> EditResult<Model> {
```

**Description:**
Replace an equation in a model

# Arguments

* `model` - The model to modify
* `index` - Index of the equation to replace
* `equation` - The new equation

# Returns

* `EditResult<Model>` - New model with the replaced equation

---

### reset

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:272`

**Signature:**
```rust
pub fn reset(&mut self) {
```

**Description:**
Reset the allocator for reuse

**Available in other languages:**
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)
- [Python](python.md#reset)

---

### resolve_scoped_reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:267`

**Signature:**
```rust
pub fn resolve_scoped_reference(&self, scoped_ref: &str) -> Option<String> {
```

**Description:**
Resolve a scoped reference to its full path
Handles hierarchical resolution according to ESM Spec Section 2.3.3

---

### save

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:47`

**Signature:**
```rust
pub fn save(esm_file_js: &JsValue) -> Result<String, JsValue> {
```

**Available in other languages:**
- [Julia](julia.md#save)
- [Julia](julia.md#save)
- [Julia](julia.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Typescript](typescript.md#save)

---

### save

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/serialize.rs:48`

**Signature:**
```rust
pub fn save(esm_file: &EsmFile) -> Result<String, EsmError> {
```

**Description:**
Serialize an ESM file to JSON string

This function converts an `EsmFile` struct back to a JSON string.
The output will be pretty-printed for human readability.

# Arguments

* `esm_file` - The ESM file to serialize

# Returns

* `Ok(String)` - Successfully serialized JSON string
* `Err(EsmError)` - Serialization error

# Examples

```rust
use esm_format::{EsmFile, Metadata, save};

let esm_file = EsmFile {
esm: "0.1.0".to_string(),
metadata: Metadata {
name: Some("test_model".to_string()),
description: None,
authors: None,
created: None,
modified: None,
license: None,
tags: None,
references: None,
},
models: None,
reaction_systems: None,
data_loaders: None,
operators: None,
coupling: None,
domain: None,
solver: None,
};

let json = save(&esm_file).expect("Failed to serialize ESM file");
assert!(json.contains("\"esm\": \"0.1.0\""));
```

**Available in other languages:**
- [Julia](julia.md#save)
- [Julia](julia.md#save)
- [Julia](julia.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Python](python.md#save)
- [Typescript](typescript.md#save)

---

### save_compact

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/serialize.rs:66`

**Signature:**
```rust
pub fn save_compact(esm_file: &EsmFile) -> Result<String, EsmError> {
```

**Description:**
Serialize an ESM file to compact JSON string (no pretty printing)

This function is similar to `save` but produces compact JSON without
extra whitespace, suitable for storage or transmission.

# Arguments

* `esm_file` - The ESM file to serialize

# Returns

* `Ok(String)` - Successfully serialized compact JSON string
* `Err(EsmError)` - Serialization error

---

### simplify

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/expression.rs:108`

**Signature:**
```rust
pub fn simplify(expr: &Expr) -> Expr {
```

**Description:**
Simplify an expression (basic symbolic simplification)

# Arguments

* `expr` - The expression to simplify

# Returns

* Simplified expression

**Available in other languages:**
- [Julia](julia.md#simplify)
- [Julia](julia.md#simplify)
- [Python](python.md#simplify)
- [Python](python.md#simplify)
- [Python](python.md#simplify)
- [Python](python.md#simplify)
- [Python](python.md#simplify)
- [Python](python.md#simplify)
- [Python](python.md#simplify)
- [Python](python.md#simplify)
- [Python](python.md#simplify)
- [Python](python.md#simplify)
- [Typescript](typescript.md#simplify)

---

### stoichiometric_matrix

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/reactions.rs:315`

**Signature:**
```rust
pub fn stoichiometric_matrix(system: &ReactionSystem) -> Vec<Vec<f64>> {
```

**Description:**
Generate stoichiometric matrix from a reaction system

Creates a matrix where rows represent species and columns represent reactions.
Matrix[i][j] = stoichiometric coefficient of species i in reaction j.
Negative values indicate reactants, positive values indicate products.

# Arguments

* `system` - The reaction system to analyze

# Returns

* `Vec<Vec<f64>>` - Matrix with species as rows and reactions as columns

**Available in other languages:**
- [Julia](julia.md#stoichiometric_matrix)

---

### stoichiometric_matrix_parallel

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/reactions.rs:388`

**Signature:**
```rust
pub fn stoichiometric_matrix_parallel(
```

---

### substitute

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:162`

**Signature:**
```rust
pub fn substitute(json_str: &str, bindings_str: &str) -> Result<String, JsValue> {
```

**Available in other languages:**
- [Julia](julia.md#substitute)
- [Julia](julia.md#substitute)
- [Python](python.md#substitute)
- [Python](python.md#substitute)
- [Typescript](typescript.md#substitute)

---

### substitute

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:17`

**Signature:**
```rust
pub fn substitute(expr: &Expr, substitutions: &std::collections::HashMap<String, Expr>) -> Expr {
```

**Description:**
Substitute variables in an expression

# Arguments

* `expr` - The expression to modify
* `substitutions` - Map from variable names to replacement expressions

# Returns

* New expression with substitutions applied

**Available in other languages:**
- [Julia](julia.md#substitute)
- [Julia](julia.md#substitute)
- [Python](python.md#substitute)
- [Python](python.md#substitute)
- [Typescript](typescript.md#substitute)

---

### substitute_in_affect_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:88`

**Signature:**
```rust
pub fn substitute_in_affect_equation(
```

**Description:**
Substitute variables in an affect equation

# Arguments

* `affect` - The affect equation to modify
* `substitutions` - Map from variable names to replacement expressions

# Returns

* New affect equation with substitutions applied

---

### substitute_in_affect_equation_with_context

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:524`

**Signature:**
```rust
pub fn substitute_in_affect_equation_with_context(
```

**Description:**
Substitute variables in an affect equation using scoped reference resolution

# Arguments

* `affect` - The affect equation to modify
* `substitutions` - Map from variable names to replacement expressions
* `context` - Scoped context for hierarchical resolution

# Returns

* New affect equation with substitutions applied using scoped resolution

---

### substitute_in_continuous_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:137`

**Signature:**
```rust
pub fn substitute_in_continuous_event(
```

**Description:**
Substitute variables in a continuous event

# Arguments

* `event` - The continuous event to modify
* `substitutions` - Map from variable names to replacement expressions

# Returns

* New continuous event with substitutions applied

---

### substitute_in_continuous_event_with_context

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:577`

**Signature:**
```rust
pub fn substitute_in_continuous_event_with_context(
```

**Description:**
Substitute variables in a continuous event using scoped reference resolution

# Arguments

* `event` - The continuous event to modify
* `substitutions` - Map from variable names to replacement expressions
* `context` - Scoped context for hierarchical resolution

# Returns

* New continuous event with substitutions applied using scoped resolution

---

### substitute_in_discrete_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:108`

**Signature:**
```rust
pub fn substitute_in_discrete_event(
```

**Description:**
Substitute variables in a discrete event

# Arguments

* `event` - The discrete event to modify
* `substitutions` - Map from variable names to replacement expressions

# Returns

* New discrete event with substitutions applied

---

### substitute_in_discrete_event_trigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:52`

**Signature:**
```rust
pub fn substitute_in_discrete_event_trigger(
```

**Description:**
Substitute variables in a discrete event trigger

# Arguments

* `trigger` - The discrete event trigger to modify
* `substitutions` - Map from variable names to replacement expressions

# Returns

* New discrete event trigger with substitutions applied

---

### substitute_in_discrete_event_trigger_with_context

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:486`

**Signature:**
```rust
pub fn substitute_in_discrete_event_trigger_with_context(
```

**Description:**
Substitute variables in a discrete event trigger using scoped reference resolution

# Arguments

* `trigger` - The discrete event trigger to modify
* `substitutions` - Map from variable names to replacement expressions
* `context` - Scoped context for hierarchical resolution

# Returns

* New discrete event trigger with substitutions applied using scoped resolution

---

### substitute_in_discrete_event_with_context

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:546`

**Signature:**
```rust
pub fn substitute_in_discrete_event_with_context(
```

**Description:**
Substitute variables in a discrete event using scoped reference resolution

# Arguments

* `event` - The discrete event to modify
* `substitutions` - Map from variable names to replacement expressions
* `context` - Scoped context for hierarchical resolution

# Returns

* New discrete event with substitutions applied using scoped resolution

---

### substitute_in_expression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:354`

**Signature:**
```rust
pub fn substitute_in_expression(expr: &Expr, substitutions: &HashMap<String, Expr>) -> Expr {
```

**Description:**
Create a copy of an expression with variable substitution

# Arguments

* `expr` - The expression to modify
* `substitutions` - Map of variable names to replacement expressions

# Returns

* `Expr` - New expression with substitutions applied

---

### substitute_in_model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:172`

**Signature:**
```rust
pub fn substitute_in_model(
```

**Description:**
Substitute variables in all expressions within a model

# Arguments

* `model` - The model to modify
* `substitutions` - Map from variable names to replacement expressions

# Returns

* New model with substitutions applied

---

### substitute_in_model_with_context

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:444`

**Signature:**
```rust
pub fn substitute_in_model_with_context(
```

**Description:**
Substitute variables in all expressions within a model using scoped reference resolution

# Arguments

* `model` - The model to modify
* `substitutions` - Map from variable names to replacement expressions
* `context` - Scoped context for hierarchical resolution

# Returns

* New model with substitutions applied using scoped resolution

---

### substitute_in_reaction_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:212`

**Signature:**
```rust
pub fn substitute_in_reaction_system(
```

**Description:**
Substitute variables in all expressions within a reaction system

# Arguments

* `reaction_system` - The reaction system to modify
* `substitutions` - Map from variable names to replacement expressions

# Returns

* New reaction system with substitutions applied

---

### substitute_in_reaction_system_with_context

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:614`

**Signature:**
```rust
pub fn substitute_in_reaction_system_with_context(
```

**Description:**
Substitute variables in all expressions within a reaction system using scoped reference resolution

# Arguments

* `reaction_system` - The reaction system to modify
* `substitutions` - Map from variable names to replacement expressions
* `context` - Scoped context for hierarchical resolution

# Returns

* New reaction system with substitutions applied using scoped resolution

---

### substitute_with_context

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:393`

**Signature:**
```rust
pub fn substitute_with_context(
```

**Description:**
Substitute variables in an expression with scoped reference resolution

# Arguments

* `expr` - The expression to modify
* `substitutions` - Map from variable names to replacement expressions
* `context` - Scoped context for hierarchical resolution

# Returns

* New expression with substitutions applied using scoped resolution

---

### to_ascii

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:133`

**Signature:**
```rust
pub fn to_ascii(json_str: &str) -> Result<String, JsValue> {
```

**Available in other languages:**
- [Julia](julia.md#to_ascii)
- [Julia](julia.md#to_ascii)

---

### to_ascii

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/display.rs:1131`

**Signature:**
```rust
pub fn to_ascii(expr: &Expr) -> String {
```

**Description:**
Convert an expression to ASCII representation

**Available in other languages:**
- [Julia](julia.md#to_ascii)
- [Julia](julia.md#to_ascii)

---

### to_dot

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:723`

**Signature:**
```rust
pub fn to_dot(&self) -> String {
```

**Description:**
Export graph to DOT format for Graphviz

# Returns

* `String` - DOT representation of the graph

**Available in other languages:**
- [Julia](julia.md#to_dot)
- [Julia](julia.md#to_dot)
- [Python](python.md#to_dot)

---

### to_dot

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:801`

**Signature:**
```rust
pub fn to_dot(&self) -> String {
```

**Description:**
Export graph to DOT format for Graphviz

# Returns

* `String` - DOT representation of the expression graph

**Available in other languages:**
- [Julia](julia.md#to_dot)
- [Julia](julia.md#to_dot)
- [Python](python.md#to_dot)

---

### to_json_graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:790`

**Signature:**
```rust
pub fn to_json_graph(&self) -> String {
```

**Description:**
Export graph to JSON format

# Returns

* `String` - JSON representation of the graph

---

### to_json_graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:870`

**Signature:**
```rust
pub fn to_json_graph(&self) -> String {
```

**Description:**
Export graph to JSON format

# Returns

* `String` - JSON representation of the graph

---

### to_latex

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:104`

**Signature:**
```rust
pub fn to_latex(json_str: &str) -> Result<String, JsValue> {
```

---

### to_latex

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/display.rs:688`

**Signature:**
```rust
pub fn to_latex(expr: &Expr) -> String {
```

**Description:**
Convert an expression to LaTeX notation

---

### to_mermaid

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:759`

**Signature:**
```rust
pub fn to_mermaid(&self) -> String {
```

**Description:**
Export graph to Mermaid format

# Returns

* `String` - Mermaid representation of the graph

**Available in other languages:**
- [Julia](julia.md#to_mermaid)
- [Julia](julia.md#to_mermaid)

---

### to_mermaid

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:842`

**Signature:**
```rust
pub fn to_mermaid(&self) -> String {
```

**Description:**
Export graph to Mermaid format

# Returns

* `String` - Mermaid representation of the expression graph

**Available in other languages:**
- [Julia](julia.md#to_mermaid)
- [Julia](julia.md#to_mermaid)

---

### to_unicode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:75`

**Signature:**
```rust
pub fn to_unicode(json_str: &str) -> Result<String, JsValue> {
```

---

### to_unicode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/display.rs:230`

**Signature:**
```rust
pub fn to_unicode(&self) -> String {
```

**Description:**
Convert expression to Unicode mathematical notation

---

### to_unicode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/display.rs:683`

**Signature:**
```rust
pub fn to_unicode(expr: &Expr) -> String {
```

**Description:**
Convert an expression to Unicode mathematical notation

---

### update_model_metadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/edit.rs:330`

**Signature:**
```rust
pub fn update_model_metadata(model: &Model, name: Option<String>, description: Option<String>) -> EditResult<Model> {
```

**Description:**
Update model metadata

# Arguments

* `model` - The model to modify
* `name` - New name (None to keep current)
* `description` - New description (None to keep current)

# Returns

* `EditResult<Model>` - New model with updated metadata

---

### validate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/wasm.rs:60`

**Signature:**
```rust
pub fn validate(json_str: &str) -> Result<JsValue, JsValue> {
```

**Available in other languages:**
- [Julia](julia.md#validate)
- [Julia](julia.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Typescript](typescript.md#validate)

---

### validate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/validate.rs:157`

**Signature:**
```rust
pub fn validate(esm_file: &EsmFile) -> ValidationResult {
```

**Description:**
Perform structural validation on an ESM file

**Note**: This function performs ONLY structural validation, not schema validation.
For comprehensive validation (both schema and structural), use `validate_complete()` instead.

This function checks:
- All variable references are defined
- Unit consistency in equations
- Mathematical validity of expressions
- Equation-unknown balance
- Reference integrity (scoped ref resolution via subsystem hierarchy)
- Reaction consistency
- Event consistency

# Arguments

* `esm_file` - The ESM file to validate (already parsed and schema-validated)

# Returns

* `ValidationResult` - Structural validation results (schema_errors will always be empty)

# Examples

```rust
use esm_format::{validate, load, EsmFile, Metadata};

let json_str = r#"
{
"esm": "0.1.0",
"metadata": {"name": "test"},
"models": {"simple": {"variables": {}, "equations": []}}
}
"#;

// First load and parse (includes schema validation)
let esm_file = load(json_str).unwrap();

// Then do structural validation
let result = validate(&esm_file);
assert!(result.is_valid);
assert!(result.schema_errors.is_empty()); // Always empty for this function
```

**Available in other languages:**
- [Julia](julia.md#validate)
- [Julia](julia.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Python](python.md#validate)
- [Typescript](typescript.md#validate)

---

### validate_complete

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/validate.rs:213`

**Signature:**
```rust
pub fn validate_complete(json_str: &str) -> ValidationResult {
```

**Description:**
Validate an ESM file completely (schema + structural validation)

This is the main validation function that performs both schema and structural validation.
Most users should use this function instead of the lower-level `validate()`.

# Arguments

* `json_str` - The original JSON string to validate

# Returns

* `ValidationResult` - Comprehensive validation results with both schema and structural errors

---

### validate_schema

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/parse.rs:109`

**Signature:**
```rust
pub fn validate_schema(json_value: &Value) -> Result<(), EsmError> {
```

**Description:**
Validate a JSON value against the ESM schema

This performs schema validation only. The JSON is assumed to be valid.

# Arguments

* `json_value` - The JSON value to validate

# Returns

* `Ok(())` - JSON passes schema validation
* `Err(EsmError::SchemaValidation)` - Schema validation errors

**Available in other languages:**
- [Julia](julia.md#validate_schema)
- [Julia](julia.md#validate_schema)

---

### validate_with_schema

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/validate.rs:240`

**Signature:**
```rust
pub fn validate_with_schema(json_str: &str, esm_file: &EsmFile) -> ValidationResult {
```

**Description:**
Validate an ESM file including schema validation

This function combines schema and structural validation.
Note: Consider using `validate_complete()` instead for a simpler API.

---

### with_capacity

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:257`

**Signature:**
```rust
pub fn with_capacity(capacity: usize) -> Self {
```

**Description:**
Create allocator with pre-allocated capacity

---

### with_scope

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:260`

**Signature:**
```rust
pub fn with_scope(mut self, scope: Vec<String>) -> Self {
```

**Description:**
Create a scoped context with specific current scope

---

## Types

### AffectEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:266`

**Definition:**
```rust
pub struct AffectEquation {
```

**Available in other languages:**
- [Julia](julia.md#affectequation)
- [Python](python.md#affectequation)
- [Typescript](typescript.md#affectequation)

---

### CompactExpr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:295`

**Definition:**
```rust
pub struct CompactExpr {
```

---

### ComponentGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:7`

**Definition:**
```rust
pub struct ComponentGraph {
```

**Available in other languages:**
- [Typescript](typescript.md#componentgraph)

---

### ComponentNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:16`

**Definition:**
```rust
pub struct ComponentNode {
```

**Available in other languages:**
- [Julia](julia.md#componentnode)
- [Python](python.md#componentnode)
- [Typescript](typescript.md#componentnode)

---

### ConservationAnalysis

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/reactions.rs:425`

**Definition:**
```rust
pub struct ConservationAnalysis {
```

---

### ConservationViolation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/reactions.rs:399`

**Definition:**
```rust
pub struct ConservationViolation {
```

---

### ContinuousEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:276`

**Definition:**
```rust
pub struct ContinuousEvent {
```

**Available in other languages:**
- [Julia](julia.md#continuousevent)
- [Python](python.md#continuousevent)
- [Typescript](typescript.md#continuousevent)

---

### CouplingEdge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:40`

**Definition:**
```rust
pub struct CouplingEdge {
```

**Available in other languages:**
- [Julia](julia.md#couplingedge)
- [Python](python.md#couplingedge)
- [Python](python.md#couplingedge)
- [Typescript](typescript.md#couplingedge)

---

### DataLoader

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:435`

**Definition:**
```rust
pub struct DataLoader {
```

**Available in other languages:**
- [Julia](julia.md#dataloader)
- [Python](python.md#dataloader)
- [Typescript](typescript.md#dataloader)

---

### DependencyEdge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:297`

**Definition:**
```rust
pub struct DependencyEdge {
```

**Available in other languages:**
- [Julia](julia.md#dependencyedge)
- [Python](python.md#dependencyedge)
- [Typescript](typescript.md#dependencyedge)

---

### DiscreteEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:212`

**Definition:**
```rust
pub struct DiscreteEvent {
```

**Available in other languages:**
- [Julia](julia.md#discreteevent)
- [Python](python.md#discreteevent)

---

### Domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:587`

**Definition:**
```rust
pub struct Domain {
```

**Available in other languages:**
- [Julia](julia.md#domain)
- [Python](python.md#domain)
- [Python](python.md#domain)
- [Python](python.md#domain)
- [Typescript](typescript.md#domain)

---

### Equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:202`

**Definition:**
```rust
pub struct Equation {
```

**Available in other languages:**
- [Julia](julia.md#equation)
- [Python](python.md#equation)
- [Python](python.md#equation)
- [Typescript](typescript.md#equation)

---

### EsmFile

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:10`

**Definition:**
```rust
pub struct EsmFile {
```

**Available in other languages:**
- [Julia](julia.md#esmfile)
- [Python](python.md#esmfile)

---

### ExpressionGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:260`

**Definition:**
```rust
pub struct ExpressionGraph {
```

---

### ExpressionNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:118`

**Definition:**
```rust
pub struct ExpressionNode {
```

**Available in other languages:**
- [Typescript](typescript.md#expressionnode)

---

### FunctionalAffect

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:314`

**Definition:**
```rust
pub struct FunctionalAffect {
```

**Available in other languages:**
- [Julia](julia.md#functionalaffect)
- [Python](python.md#functionalaffect)
- [Typescript](typescript.md#functionalaffect)

---

### LinearInvariant

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/reactions.rs:438`

**Definition:**
```rust
pub struct LinearInvariant {
```

---

### Metadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:68`

**Definition:**
```rust
pub struct Metadata {
```

**Available in other languages:**
- [Julia](julia.md#metadata)
- [Python](python.md#metadata)
- [Python](python.md#metadata)
- [Python](python.md#metadata)
- [Typescript](typescript.md#metadata)

---

### MigrationError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/migration.rs:12`

**Definition:**
```rust
pub struct MigrationError {
```

---

### Model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:136`

**Definition:**
```rust
pub struct Model {
```

**Available in other languages:**
- [Julia](julia.md#model)
- [Python](python.md#model)
- [Python](python.md#model)
- [Typescript](typescript.md#model)

---

### ModelAllocator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:243`

**Definition:**
```rust
pub struct ModelAllocator {
```

---

### ModelVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:166`

**Definition:**
```rust
pub struct ModelVariable {
```

**Available in other languages:**
- [Julia](julia.md#modelvariable)
- [Python](python.md#modelvariable)
- [Typescript](typescript.md#modelvariable)

---

### Operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:451`

**Definition:**
```rust
pub struct Operator {
```

**Available in other languages:**
- [Julia](julia.md#operator)
- [Python](python.md#operator)
- [Python](python.md#operator)
- [Python](python.md#operator)
- [Typescript](typescript.md#operator)

---

### ParallelEvaluator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/performance.rs:56`

**Definition:**
```rust
pub struct ParallelEvaluator {
```

---

### Parameter

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:387`

**Definition:**
```rust
pub struct Parameter {
```

**Available in other languages:**
- [Julia](julia.md#parameter)
- [Python](python.md#parameter)
- [Typescript](typescript.md#parameter)

---

### ParseError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/parse.rs:12`

**Definition:**
```rust
pub struct ParseError {
```

**Available in other languages:**
- [Julia](julia.md#parseerror)
- [Python](python.md#parseerror)
- [Python](python.md#parseerror)

---

### Reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:403`

**Definition:**
```rust
pub struct Reaction {
```

**Available in other languages:**
- [Julia](julia.md#reaction)
- [Python](python.md#reaction)
- [Typescript](typescript.md#reaction)

---

### ReactionSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:347`

**Definition:**
```rust
pub struct ReactionSystem {
```

**Available in other languages:**
- [Julia](julia.md#reactionsystem)
- [Python](python.md#reactionsystem)
- [Typescript](typescript.md#reactionsystem)

---

### Reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:48`

**Definition:**
```rust
pub struct Reference {
```

**Available in other languages:**
- [Julia](julia.md#reference)
- [Python](python.md#reference)
- [Python](python.md#reference)
- [Typescript](typescript.md#reference)

---

### SchemaError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/validate.rs:37`

**Definition:**
```rust
pub struct SchemaError {
```

**Available in other languages:**
- [Julia](julia.md#schemaerror)
- [Python](python.md#schemaerror)
- [Typescript](typescript.md#schemaerror)

---

### SchemaValidationError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/parse.rs:27`

**Definition:**
```rust
pub struct SchemaValidationError {
```

**Available in other languages:**
- [Julia](julia.md#schemavalidationerror)
- [Python](python.md#schemavalidationerror)

---

### ScopedContext

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/substitute.rs:237`

**Definition:**
```rust
pub struct ScopedContext {
```

---

### Solver

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:599`

**Definition:**
```rust
pub struct Solver {
```

**Available in other languages:**
- [Julia](julia.md#solver)
- [Python](python.md#solver)
- [Typescript](typescript.md#solver)

---

### Species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:368`

**Definition:**
```rust
pub struct Species {
```

**Available in other languages:**
- [Julia](julia.md#species)
- [Python](python.md#species)
- [Typescript](typescript.md#species)

---

### StoichiometricEntry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:424`

**Definition:**
```rust
pub struct StoichiometricEntry {
```

---

### StructuralError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/validate.rs:48`

**Definition:**
```rust
pub struct StructuralError {
```

**Available in other languages:**
- [Julia](julia.md#structuralerror)
- [Typescript](typescript.md#structuralerror)

---

### Unit

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/units.rs:8`

**Definition:**
```rust
pub struct Unit {
```

**Available in other languages:**
- [Python](python.md#unit)

---

### ValidationResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/validate.rs:12`

**Definition:**
```rust
pub struct ValidationResult {
```

**Available in other languages:**
- [Julia](julia.md#validationresult)
- [Python](python.md#validationresult)
- [Typescript](typescript.md#validationresult)

---

### VariableMapping

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/types.rs:575`

**Definition:**
```rust
pub struct VariableMapping {
```

---

### VariableNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/graph.rs:269`

**Definition:**
```rust
pub struct VariableNode {
```

**Available in other languages:**
- [Julia](julia.md#variablenode)
- [Python](python.md#variablenode)
- [Typescript](typescript.md#variablenode)

---

### VersionInfo

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format-rust/src/migration.rs:32`

**Definition:**
```rust
pub struct VersionInfo {
```

**Available in other languages:**
- [Python](python.md#versioninfo)

---

