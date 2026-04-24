# Typescript API Reference

Complete API reference for the ESM Format Typescript library.

## Functions

### addContinuousEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:388`

**Signature:**
```typescript
export function addContinuousEvent(
```

**Description:**
Add a continuous event to a model
@param model Model to add event to
@param event Continuous event to add
@returns New model with event added
/

---

### addCoupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:465`

**Signature:**
```typescript
export function addCoupling(
```

**Description:**
Add a coupling entry to an ESM file
@param file ESM file to add coupling to
@param entry Coupling entry to add
@returns New ESM file with coupling added
/

---

### addDiscreteEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:405`

**Signature:**
```typescript
export function addDiscreteEvent(
```

**Description:**
Add a discrete event to a model
@param model Model to add event to
@param event Discrete event to add
@returns New model with event added
/

---

### addEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:194`

**Signature:**
```typescript
export function addEquation(
```

**Description:**
Add a new equation to a model
@param model Model to add equation to
@param equation Equation to add
@returns New model with equation added
/

---

### addReaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:263`

**Signature:**
```typescript
export function addReaction(
```

**Description:**
Add a new reaction to a reaction system
@param system ReactionSystem to add reaction to
@param reaction Reaction to add
@returns New reaction system with reaction added
/

---

### addSpecies

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:307`

**Signature:**
```typescript
export function addSpecies(
```

**Description:**
Add a new species to a reaction system
@param system ReactionSystem to add species to
@param name Species name
@param species Species definition
@returns New reaction system with species added
/

---

### addVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:62`

**Signature:**
```typescript
export function addVariable(
```

**Description:**
Add a new variable to a model
@param model Model to add variable to
@param name Variable name
@param variable Variable definition
@returns New model with variable added
/

---

### analyzeComplexity

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/complexity.ts:17`

**Signature:**
```typescript
export function analyzeComplexity(expr: Expr): ComplexityMetrics {
```

**Description:**
Analyze the complexity of an expression
@param expr Expression to analyze
@returns Complexity metrics
/

---

### applyBindings

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:212`

**Signature:**
```typescript
export function applyBindings(template: Expr, b: Bindings): Expr {
```

**Description:**
Substitute pattern variables in `template` with their bound values.
Throws `RuleEngineError(E_PATTERN_VAR_UNBOUND)` if the template
references a pattern variable not in `bindings`.
/

---

### buildDependencyGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/dependency-graph.ts:19`

**Signature:**
```typescript
export function buildDependencyGraph(
```

**Description:**
Build a dependency graph from an ESM file, model, or expression
@param target The target to analyze
@param options Analysis options
@returns Dependency graph with nodes and edges
/

---

### canMigrate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/migration.ts:22`

**Signature:**
```typescript
export function canMigrate(sourceVersion: string, targetVersion: string): boolean {
```

**Description:**
Check if migration is possible from the source version to target version.
/

---

### canonicalJson

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/canonicalize.ts:113`

**Signature:**
```typescript
export function canonicalJson(expr: Expr): string {
```

---

### canonicalize

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/canonicalize.ts:90`

**Signature:**
```typescript
export function canonicalize(expr: Expr): Expr {
```

**Available in other languages:**
- [Julia](julia.md#canonicalize)
- [Julia](julia.md#canonicalize)

---

### checkDimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/units.ts:82`

**Signature:**
```typescript
export function checkDimensions(
```

**Description:**
Check dimensional consistency of an expression.

Follows ESM spec Section 3.3.1:
- Addition/subtraction: operands must share canonical dimensions
- Multiplication: dimensions add (scales multiply)
- Division: dimensions subtract (scales divide)
- `D(x, wrt=t)`: dimension of x divided by dimension of t
- Transcendental functions require dimensionless arguments
/

---

### checkGuard

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:280`

**Signature:**
```typescript
export function checkGuard(g: Guard, b: Bindings, ctx: RuleContext): Bindings | null {
```

---

### checkGuards

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:266`

**Signature:**
```typescript
export function checkGuards(
```

**Description:**
Evaluate `guards` left-to-right, threading bindings. A guard whose
pvar-valued `grid` field is unbound at entry binds it to the
variable's actual grid (§9.2.1). Returns extended bindings on
success, `null` on miss. Throws on unknown guard names.
/

---

### checkUnrewrittenPdeOps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:595`

**Signature:**
```typescript
export function checkUnrewrittenPdeOps(expr: Expr): void {
```

**Description:**
Scan `expr` for leftover PDE ops after rewriting. Throws
`RuleEngineError(E_UNREWRITTEN_PDE_OP)` if any are found.
/

---

### classifyComplexity

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/complexity.ts:219`

**Signature:**
```typescript
export function classifyComplexity(expr: Expr): 'trivial' | 'simple' | 'moderate' | 'complex' | 'very_complex' {
```

**Description:**
Classify expression complexity level
@param expr Expression to classify
@returns Complexity level
/

---

### clearGridFamilies

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/grid-accessor.ts:185`

**Signature:**
```typescript
export function clearGridFamilies(): void {
```

**Description:**
Drop every registered family. Intended for test isolation; do not
call in production code.
/

---

### compareAnalysis

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/index.ts:260`

**Signature:**
```typescript
export function compareAnalysis(results1: any, results2: any) {
```

**Description:**
Compare analysis results between different expressions or models
/

---

### compareComplexity

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/complexity.ts:187`

**Signature:**
```typescript
export function compareComplexity(expr1: Expr, expr2: Expr): number {
```

**Description:**
Compare complexity of two expressions
@param expr1 First expression
@param expr2 Second expression
@returns Comparison result (-1: expr1 simpler, 0: equal, 1: expr1 more complex)
/

---

### componentExists

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/graph.ts:349`

**Signature:**
```typescript
export function componentExists(esmFile: EsmFile, componentId: string): boolean {
```

**Description:**
Utility to check if a component exists in the ESM file
/

---

### componentGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/graph.ts:290`

**Signature:**
```typescript
export function componentGraph(file: EsmFile): Graph<ComponentNode, CouplingEdge> {
```

**Description:**
Extract the system graph from an ESM file as specified in task.
Returns a directed graph where nodes are model components and edges are coupling rules.
Implements the Graph interface with adjacency methods.
/

---

### component_graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/graph.ts:104`

**Signature:**
```typescript
export function component_graph(esmFile: EsmFile): ComponentGraph {
```

**Description:**
Extract the system graph from an ESM file.
Returns a directed graph where nodes are model components and edges are coupling rules.
/

**Available in other languages:**
- [Julia](julia.md#component_graph)
- [Julia](julia.md#component_graph)

---

### compose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:507`

**Signature:**
```typescript
export function compose(
```

**Description:**
Compose two systems using a coupling entry
@param file ESM file
@param a First system name
@param b Second system name
@returns New ESM file with composition coupling added
/

**Available in other languages:**
- [Julia](julia.md#compose)
- [Julia](julia.md#compose)

---

### contains

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/expression.ts:67`

**Signature:**
```typescript
export function contains(expr: Expr, varName: string): boolean {
```

**Description:**
Check if an expression contains a specific variable
@param expr Expression to search
@param varName Variable name to look for
@returns True if the variable appears in the expression
/

**Available in other languages:**
- [Julia](julia.md#contains)
- [Julia](julia.md#contains)

---

### convertUnits

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/unit-conversion.ts:221`

**Signature:**
```typescript
export function convertUnits(value: number, from: string, to: string): number {
```

**Description:**
Convert a numeric value from one unit string to another.

@example
convertUnits(1, 'km', 'm')            // 1000
convertUnits(0, 'Celsius', 'K')       // 273.15
convertUnits(1, 'atm', 'Pa')          // 101325
convertUnits(1, 'Dobson', 'molec/m^2') // 2.6867e20

@throws {UnitConversionError} when the unit strings have incompatible dimensions
or cannot be parsed.
/

---

### createAstStore

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/ast-store.ts:129`

**Signature:**
```typescript
export function createAstStore(config: AstStoreConfig = {}): AstStore {
```

**Description:**
Create a centralized AST store for ESM file management

@param config - Configuration options
@returns AST store interface with reactive state and path-based updates
/

---

### createDebouncedValidation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/validation.ts:327`

**Signature:**
```typescript
export function createDebouncedValidation(
```

**Description:**
Debounced validation hook for use in components that trigger validation

@param validationFn - Function that performs validation
@param debounceMs - Debounce delay in milliseconds
@returns Debounced validation function
/

---

### createDemoServer

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/tests/demo/demo-pages.ts:333`

**Signature:**
```typescript
export function createDemoServer() {
```

---

### createGrid

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/grid-accessor.ts:170`

**Signature:**
```typescript
export function createGrid(family: string, opts: Record<string, unknown> = {}): GridAccessor {
```

**Description:**
Construct a grid via the registry. Raises
`GridAccessorError(E_GRID_FAMILY_UNKNOWN)` if the family has no
registered factory.
/

---

### createUndoHistory

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/history.ts:70`

**Signature:**
```typescript
export function createUndoHistory(
```

**Description:**
Create undo/redo history management for an ESM file

@param file - Reactive signal containing the current ESM file
@param setFile - Function to update the ESM file
@param config - Optional configuration
@returns History management interface with undo/redo functions
/

---

### createUndoKeyboardHandler

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/history.ts:281`

**Signature:**
```typescript
export function createUndoKeyboardHandler(
```

**Description:**
Default keyboard shortcut handler for undo/redo
Can be used independently of createUndoHistory if needed
/

---

### createValidationContext

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/validation.ts:306`

**Signature:**
```typescript
export function createValidationContext(
```

**Description:**
Create a simplified validation context for components that only need basic validation state

@param file - Reactive signal containing the current ESM file
@param config - Optional configuration
@returns Simplified validation interface
/

---

### createValidationSignals

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/validation.ts:93`

**Signature:**
```typescript
export function createValidationSignals(
```

**Description:**
Create reactive validation signals for an ESM file

@param file - Reactive signal containing the current ESM file
@param config - Optional configuration for validation behavior
@returns Validation signals interface with reactive validation state
/

---

### deriveODEs

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/reactions.ts:28`

**Signature:**
```typescript
export function deriveODEs(system: ReactionSystem): Model {
```

**Description:**
Derive ODEs from a reaction system using mass action kinetics

Generates an ODE model from reaction stoichiometry and rate laws. For each reaction
with rate k, substrates {Si} with stoichiometries {ni}, products {Pj} with
stoichiometries {mj}:
- rate law: v = k * prod(Si^ni)
- ODE contribution: dX/dt += net_stoich_X * v

Handles:
- Source reactions (null substrates): rate is the direct production term
- Sink reactions (null products): rate is the direct loss term
- Constraint equations are appended as additional equations

@param system ReactionSystem to derive ODEs from
@returns Model with species as state variables, derived ODEs plus constraints
/

---

### detectStabilityIssues

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/complexity.ts:324`

**Signature:**
```typescript
export function detectStabilityIssues(expr: Expr): Array<{
```

**Description:**
Detect numerical stability issues in expressions
@param expr Expression to analyze
@returns Array of potential stability issues
/

---

### differentiate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/differentiation.ts:19`

**Signature:**
```typescript
export function differentiate(expr: Expr, variable: string): DerivativeResult {
```

**Description:**
Compute the symbolic derivative of an expression with respect to a variable
@param expr Expression to differentiate
@param variable Variable with respect to which to differentiate
@returns Derivative result with simplified form
/

**Available in other languages:**
- [Python](python.md#differentiate)

---

### dimsEqual

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/units.ts:497`

**Signature:**
```typescript
export function dimsEqual(a: CanonicalDims, b: CanonicalDims): boolean {
```

---

### discretize

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/discretize.ts:87`

**Signature:**
```typescript
export function discretize(esm: JsonObject, options: DiscretizeOptions = {}): JsonObject {
```

**Description:**
Run the RFC §11 discretization pipeline and the RFC §12 DAE binding
contract on an ESM document. Returns a new object; the input is not
mutated.
/

**Available in other languages:**
- [Julia](julia.md#discretize)
- [Julia](julia.md#discretize)

---

### emptyContext

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:90`

**Signature:**
```typescript
export function emptyContext(): RuleContext {
```

---

### estimateParallelPotential

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/complexity.ts:282`

**Signature:**
```typescript
export function estimateParallelPotential(expr: Expr): number {
```

**Description:**
Estimate parallel execution potential
@param expr Expression to analyze
@returns Parallelization score (0-1, higher means more parallelizable)
/

---

### estimateSavings

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/common-subexpressions.ts:288`

**Signature:**
```typescript
export function estimateSavings(commonSubexpressions: CommonSubexpression[]): number {
```

**Description:**
Estimate the cost savings from factoring out common subexpressions
@param commonSubexpressions Array of common subexpressions
@returns Total estimated cost savings
/

---

### evaluate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/expression.ts:87`

**Signature:**
```typescript
export function evaluate(expr: Expr, bindings: Map<string, number>): number {
```

**Description:**
Evaluate an expression numerically with variable bindings
@param expr Expression to evaluate
@param bindings Map of variable names to their numeric values
@returns Numeric result
@throws Error if variables are unbound or evaluation fails
/

**Available in other languages:**
- [Julia](julia.md#evaluate)
- [Julia](julia.md#evaluate)

---

### exportResults

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/index.ts:245`

**Signature:**
```typescript
export function exportResults(results: any, format: 'json' | 'yaml' | 'markdown' | 'html') {
```

**Description:**
Export analysis results to various formats
/

---

### expressionGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/graph.ts:377`

**Signature:**
```typescript
export function expressionGraph(
```

**Description:**
Extract variable-level dependency graph from an ESM file, model, reaction system, equation, reaction, or expression.
Creates a directed graph where nodes are variables/parameters/species and edges represent dependencies.

@param target The target to analyze (EsmFile, Model, ReactionSystem, Equation, Reaction, or Expr)
@param options Optional settings for graph generation
@returns Graph with VariableNode nodes and DependencyEdge edges
/

---

### extract

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:590`

**Signature:**
```typescript
export function extract(
```

**Description:**
Extract a specific component from an ESM file into a new file
@param file ESM file to extract from
@param componentName Name of the component to extract
@returns New ESM file containing only the specified component
@throws EntityNotFoundError if component not found
/

**Available in other languages:**
- [Julia](julia.md#extract)
- [Julia](julia.md#extract)

---

### findCommonSubexpressions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/common-subexpressions.ts:18`

**Signature:**
```typescript
export function findCommonSubexpressions(expr: Expr, minComplexity: number = 5): CommonSubexpression[] {
```

**Description:**
Find common subexpressions in a single expression
@param expr Expression to analyze
@param minComplexity Minimum complexity threshold for considering subexpressions
@returns Array of common subexpressions found
/

---

### findCommonSubexpressionsAcrossExpressions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/common-subexpressions.ts:87`

**Signature:**
```typescript
export function findCommonSubexpressionsAcrossExpressions(
```

**Description:**
Find common subexpressions across multiple expressions
@param expressions Array of expressions to analyze
@param minComplexity Minimum complexity threshold
@returns Array of common subexpressions found across expressions
/

---

### findCommonSubexpressionsInEsmFile

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/common-subexpressions.ts:211`

**Signature:**
```typescript
export function findCommonSubexpressionsInEsmFile(esmFile: EsmFile, minComplexity: number = 5): CommonSubexpression[] {
```

**Description:**
Find common subexpressions across an entire ESM file
@param esmFile ESM file to analyze
@param minComplexity Minimum complexity threshold
@returns Array of common subexpressions found across the file
/

---

### findCommonSubexpressionsInModel

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/common-subexpressions.ts:159`

**Signature:**
```typescript
export function findCommonSubexpressionsInModel(model: Model, minComplexity: number = 5): CommonSubexpression[] {
```

**Description:**
Find common subexpressions in a model
@param model Model to analyze
@param minComplexity Minimum complexity threshold
@returns Array of common subexpressions found in the model
/

---

### findCriticalPoints

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/differentiation.ts:544`

**Signature:**
```typescript
export function findCriticalPoints(expr: Expr, variable: string): {
```

**Description:**
Find critical points (where derivative equals zero)
This is a symbolic analysis - actual solving would require numerical methods
@param expr Expression to analyze
@param variable Variable to find critical points for
@returns Information about potential critical points
/

---

### findDeadVariables

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/dependency-graph.ts:463`

**Signature:**
```typescript
export function findDeadVariables(graph: DependencyGraph): DependencyNode[] {
```

**Description:**
Find dead variables (those that are defined but never used)
/

---

### findDependencyChains

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/dependency-graph.ts:480`

**Signature:**
```typescript
export function findDependencyChains(graph: DependencyGraph, startNode: string, maxDepth: number = 10): string[][] {
```

**Description:**
Find variable dependency chains (paths from parameters to state variables)
/

---

### findExpensiveSubexpressions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/complexity.ts:242`

**Signature:**
```typescript
export function findExpensiveSubexpressions(expr: Expr, limit: number = 5): Array<{
```

**Description:**
Find the most expensive sub-expressions in an expression
@param expr Expression to analyze
@param limit Maximum number of results to return
@returns Array of expensive sub-expressions with their costs
/

---

### flatten

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/flatten.ts:73`

**Signature:**
```typescript
export function flatten(file: EsmFile): FlattenedSystem {
```

**Description:**
Flatten a multi-system ESM file into a single unified system.

The algorithm:
1. Iterates over all models and reaction_systems in the file
2. Namespaces all variables with their system name prefix (dot notation)
3. Processes coupling entries to produce variable mappings and connector equations
4. Returns a unified flattened system

@param file - The ESM file to flatten
@returns A FlattenedSystem with all variables namespaced and equations unified
/

**Available in other languages:**
- [Julia](julia.md#flatten)
- [Julia](julia.md#flatten)
- [Julia](julia.md#flatten)
- [Julia](julia.md#flatten)

---

### floatLit

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/numeric-literal.ts:50`

**Signature:**
```typescript
export function floatLit(value: number): NumericLiteral {
```

---

### formatCanonicalFloat

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/canonicalize.ts:375`

**Signature:**
```typescript
export function formatCanonicalFloat(f: number): string {
```

**Description:**
Format a finite `number` per RFC §5.4.6. Only handles float-typed
values: integer-typed `NumericLiteral` nodes are emitted as bare JSON
integers by {@link canonicalJson} directly.

Unlike the convenience helper re-exported from `./numeric-literal`, this
version strips the leading `+` on exponent notation (RFC §5.4.6:
"no leading + on the exponent") so `1e25` emits as `1e25`, not `1e+25`.
/

---

### formatCanonicalFloat

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/numeric-literal.ts:409`

**Signature:**
```typescript
export function formatCanonicalFloat(value: number): string {
```

**Description:**
Emit a float per RFC §5.4.6: ECMAScript `ToString(Number)` with a
trailing `.0` override when the result is an integer-valued
plain-decimal token.

Exported for use by canonicalize() and downstream consumers that
need to emit individual float tokens outside of a full JSON
document (e.g. debug logs, custom formatters).
/

---

### formatResults

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/index.ts:237`

**Signature:**
```typescript
export function formatResults(results: any): string {
```

**Description:**
Format analysis results for display
/

---

### formatUserFriendly

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/error-handling.ts:195`

**Signature:**
```typescript
export function formatUserFriendly(error: ESMError): string {
```

---

### freeParameters

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/expression.ts:47`

**Signature:**
```typescript
export function freeParameters(expr: Expr, model: Model): Set<string> {
```

**Description:**
Extract free parameters from an expression within a model context
@param expr Expression to analyze
@param model Model context to determine parameter vs state variables
@returns Set of parameter names referenced in the expression
/

---

### freeVariables

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/expression.ts:22`

**Signature:**
```typescript
export function freeVariables(expr: Expr): Set<string> {
```

**Description:**
Extract all variable references from an expression
@param expr Expression to analyze
@returns Set of variable names referenced in the expression
/

---

### generateFactoredVariableNames

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/common-subexpressions.ts:298`

**Signature:**
```typescript
export function generateFactoredVariableNames(
```

**Description:**
Generate variable names for factored subexpressions
@param commonSubexpressions Array of common subexpressions
@param prefix Prefix for generated variable names
@returns Map of expressions to generated variable names
/

---

### getComponentType

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/graph.ts:361`

**Signature:**
```typescript
export function getComponentType(esmFile: EsmFile, componentId: string): ComponentNode['type'] | null {
```

**Description:**
Get the type of a component by its ID
/

---

### getGridFamily

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/grid-accessor.ts:148`

**Signature:**
```typescript
export function getGridFamily(family: string): GridAccessorFactory | undefined {
```

---

### getProfiler

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/error-handling.ts:486`

**Signature:**
```typescript
export function getProfiler(): PerformanceProfiler {
```

---

### getSupportedMigrationTargets

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/migration.ts:30`

**Signature:**
```typescript
export function getSupportedMigrationTargets(sourceVersion: string): string[] {
```

**Description:**
Get the list of schema versions that a given source version can migrate to.
/

---

### gradient

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/differentiation.ts:52`

**Signature:**
```typescript
export function gradient(expr: Expr, variables?: string[]): DerivativeResult[] {
```

**Description:**
Compute the gradient (all first partial derivatives)
@param expr Expression to differentiate
@param variables Array of variables (if not provided, will extract from expression)
@returns Gradient as array of derivatives
/

---

### groupSubexpressionsByType

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/common-subexpressions.ts:320`

**Signature:**
```typescript
export function groupSubexpressionsByType(
```

**Description:**
Group common subexpressions by their structure type
@param commonSubexpressions Array of common subexpressions
@returns Grouped subexpressions by operation type
/

---

### hasGridFamily

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/grid-accessor.ts:153`

**Signature:**
```typescript
export function hasGridFamily(family: string): boolean {
```

---

### higherOrderDerivative

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/differentiation.ts:494`

**Signature:**
```typescript
export function higherOrderDerivative(expr: Expr, variable: string, order: number = 1): DerivativeResult {
```

**Description:**
Compute higher-order derivatives
@param expr Expression to differentiate
@param variable Variable with respect to which to differentiate
@param order Order of derivative (default: 1)
@returns Higher-order derivative result
/

---

### intLit

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/numeric-literal.ts:40`

**Signature:**
```typescript
export function intLit(value: number): NumericLiteral {
```

---

### isDifferentiable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/differentiation.ts:527`

**Signature:**
```typescript
export function isDifferentiable(expr: Expr, variable: string): boolean {
```

**Description:**
Check if an expression is differentiable with respect to a variable
@param expr Expression to check
@param variable Variable to check differentiability with respect to
@returns True if differentiable, false otherwise
/

---

### isDimensionless

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/units.ts:490`

**Signature:**
```typescript
export function isDimensionless(unit: ParsedUnit): boolean {
```

---

### isFloatLit

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/numeric-literal.ts:74`

**Signature:**
```typescript
export function isFloatLit(x: unknown): x is NumericLiteral & { kind: 'float' } {
```

---

### isIntLit

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/numeric-literal.ts:70`

**Signature:**
```typescript
export function isIntLit(x: unknown): x is NumericLiteral & { kind: 'int' } {
```

---

### isNumericLiteral

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/numeric-literal.ts:62`

**Signature:**
```typescript
export function isNumericLiteral(x: unknown): x is NumericLiteral {
```

---

### listGridFamilies

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/grid-accessor.ts:161`

**Signature:**
```typescript
export function listGridFamilies(): string[] {
```

**Description:**
All registered family names, sorted lexicographically so output is
deterministic across runs.
/

---

### load

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/parse.ts:2312`

**Signature:**
```typescript
export function load(input: string | object, options?: LoadOptions): EsmFile {
```

**Description:**
Load an ESM file from a JSON string or pre-parsed object

@param input - JSON string or pre-parsed JavaScript object
@param options - Optional load-time settings (see {@link LoadOptions})
@returns Typed EsmFile object
@throws {ParseError} When JSON parsing fails or version is incompatible
@throws {SchemaValidationError} When schema validation fails
/

**Available in other languages:**
- [Julia](julia.md#load)
- [Julia](julia.md#load)
- [Julia](julia.md#load)

---

### losslessJsonParse

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/numeric-literal.ts:111`

**Signature:**
```typescript
export function losslessJsonParse(text: string): unknown {
```

**Description:**
Parse a JSON document, preserving the integer-vs-float distinction
of every numeric token per RFC §5.4.6: a token containing `.`, `e`,
or `E` becomes `NumericLiteral{kind:'float'}`; otherwise it becomes
`NumericLiteral{kind:'int'}`. All other JSON values (strings, bools,
null, arrays, objects) decode to their native JS equivalents.

Integer-grammar tokens outside the safe-integer range fall back to
`float` kind to avoid silent precision loss, matching the Go
binding's `normalizeJSONNumber` behavior.
/

---

### losslessJsonStringify

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/numeric-literal.ts:345`

**Signature:**
```typescript
export function losslessJsonStringify(value: unknown): string {
```

**Description:**
Stringify a value to JSON, emitting `NumericLiteral` leaves per RFC
§5.4.6:

- `kind: 'int'`  → JSON-integer token (no `.`, no `e`).
- `kind: 'float'` with integer-valued magnitude in
`[−(1e21 − 1), 1e21 − 1]` → `ToString(Number)` with trailing
`.0` appended so the token cannot be confused with an integer
on parse-back (e.g. `1.0`, `-3.0`, `0.0`).
- `kind: 'float'` otherwise → native `ToString(Number)` (which is
already distinguishable via `.` or `e`).
- `-0.0` float → `-0.0`.
- NaN or ±Infinity → throws `CanonicalNonfiniteError`.

Plain JS `number` values are serialized with `JSON.stringify`'s
default rules (no trailing `.0` override); callers that want
canonical emission must tag literals via `intLit` / `floatLit`.
/

---

### mapVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:528`

**Signature:**
```typescript
export function mapVariable(
```

**Description:**
Map a variable from one system to another with optional transformation
@param file ESM file
@param from Source variable reference
@param to Target variable reference
@param transform Optional transformation type
@returns New ESM file with variable mapping coupling added
/

---

### matchPattern

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:136`

**Signature:**
```typescript
export function matchPattern(pattern: Expr, expr: Expr): Bindings | null {
```

**Description:**
Attempt to match `pattern` against `expr`. On success, returns a
substitution map from each pattern-variable name (including the
leading `$`) to the bound expression. Sibling-field (name-class)
pvars bind to bare-name strings.
/

---

### merge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:554`

**Signature:**
```typescript
export function merge(
```

**Description:**
Merge two ESM files
@param fileA First ESM file
@param fileB Second ESM file
@returns New ESM file with merged content
/

**Available in other languages:**
- [Julia](julia.md#merge)
- [Julia](julia.md#merge)

---

### migrate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/migration.ts:40`

**Signature:**
```typescript
export function migrate(file: EsmFile, targetVersion: string): EsmFile {
```

**Description:**
Migrate an ESM file from its current schema version to the target version.
/

**Available in other languages:**
- [Python](python.md#migrate)

---

### numericValue

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/numeric-literal.ts:83`

**Signature:**
```typescript
export function numericValue(x: unknown): number | undefined {
```

**Description:**
Return the underlying numeric value of a plain `number` or a
`NumericLiteral`. Returns `undefined` for anything else. Use this
at the boundary between kind-aware and kind-agnostic code.
/

---

### parseExpr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:559`

**Signature:**
```typescript
export function parseExpr(v: unknown): Expr {
```

**Description:**
Parse a JSON value (already parsed — produced by `losslessJsonParse`
or `JSON.parse`) into an [`Expr`], preserving int-vs-float per
RFC §5.4 when the caller used `losslessJsonParse`.
/

---

### parseRules

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:472`

**Signature:**
```typescript
export function parseRules(value: unknown): Rule[] {
```

**Description:**
Parse a `rules` section (already-parsed JSON value — produced by
`losslessJsonParse` or `JSON.parse`) into an ordered list. Accepts
either the JSON-object-keyed-by-name form or the array form
(RFC §5.2.5).
/

---

### parseUnit

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/units.ts:57`

**Signature:**
```typescript
export function parseUnit(unitStr: string): ParsedUnit {
```

**Description:**
Parse a unit string into canonical SI dimensions plus scale factor.

Delegates to `parseUnitForConversion` but swallows parse errors and returns
a dimensionless fallback, matching the lenient semantics of the earlier
unit validator (which silently ignored unknown tokens). This keeps the
`validateUnits` pipeline warning-driven rather than exception-driven.

The string `"degrees"` is accepted as dimensionless because ESM treats
angle labels as informational; the canonical unit table does not register
it to avoid committing to a radian conversion factor that ESM does not
promise.
/

---

### parseUnitForConversion

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/unit-conversion.ts:140`

**Signature:**
```typescript
export function parseUnitForConversion(unitStr: string): ParsedUnit {
```

**Description:**
Parse a unit string into canonical SI dimensions plus scale (and optional offset).

Accepts compound expressions like `"kg*m/s^2"`, `"molec/cm^3"`, `"cm^3/molec/s"`.
Offset-based units (`C`, `Celsius`) may only appear as the sole term at power +1.

@throws {UnitConversionError} on unknown unit names, malformed tokens, or misused offset units.
/

---

### partialDerivatives

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/differentiation.ts:36`

**Signature:**
```typescript
export function partialDerivatives(expr: Expr, variables: string[]): Map<string, DerivativeResult> {
```

**Description:**
Compute partial derivatives with respect to multiple variables
@param expr Expression to differentiate
@param variables Array of variables to differentiate with respect to
@returns Map of variable names to their derivative results
/

---

### productMatrix

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/reactions.ts:314`

**Signature:**
```typescript
export function productMatrix(system: ReactionSystem): number[][] {
```

**Description:**
Compute product stoichiometric matrix from a reaction system

Returns the product stoichiometric matrix (species × reactions) where:
- Rows are species (in declaration order)
- Columns are reactions (in array order)
- Entry [i][j] = product stoichiometry for species i in reaction j
- Null products contribute 0

@param system ReactionSystem to compute matrix from
@returns Product stoichiometric matrix
/

---

### profileOperation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/error-handling.ts:491`

**Signature:**
```typescript
export function profileOperation(operationName: string) {
```

---

### registerGridFamily

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/grid-accessor.ts:121`

**Signature:**
```typescript
export function registerGridFamily(family: string, factory: GridAccessorFactory): void {
```

**Description:**
Register a factory for `family`. Re-registering the same family is
an error so downstream code cannot silently pick the wrong
implementation when two packages ship the same name. Use
`unregisterGridFamily` first if you need to swap.
/

---

### registerWebComponents

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/web-components.ts:565`

**Signature:**
```typescript
export function registerWebComponents() {
```

---

### registerWebComponents

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/web-components.ts:420`

**Signature:**
```typescript
export function registerWebComponents() {
```

**Description:**
Register all ESM editor web components
/

---

### removeCoupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:483`

**Signature:**
```typescript
export function removeCoupling(
```

**Description:**
Remove a coupling entry from an ESM file by index
@param file ESM file to remove coupling from
@param index Index of coupling entry to remove
@returns New ESM file with coupling removed
@throws EntityNotFoundError if index is out of bounds
/

---

### removeEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:212`

**Signature:**
```typescript
export function removeEquation(
```

**Description:**
Remove an equation from a model
@param model Model to remove equation from
@param indexOrLhs Either the numeric index or the LHS expression of the equation
@returns New model with equation removed
@throws EntityNotFoundError if equation not found
/

---

### removeEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:423`

**Signature:**
```typescript
export function removeEvent(
```

**Description:**
Remove an event from a model by name
@param model Model to remove event from
@param name Event name to remove
@returns New model with event removed
@throws EntityNotFoundError if event not found
/

---

### removeReaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:280`

**Signature:**
```typescript
export function removeReaction(
```

**Description:**
Remove a reaction from a reaction system
@param system ReactionSystem to remove reaction from
@param id Reaction ID to remove
@returns New reaction system with reaction removed
@throws EntityNotFoundError if reaction not found
/

---

### removeSpecies

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:329`

**Signature:**
```typescript
export function removeSpecies(
```

**Description:**
Remove a species from a reaction system, with reference checking
@param system ReactionSystem to remove species from
@param name Species name to remove
@returns New reaction system with species removed
@throws VariableInUseError if species is still referenced in reactions
@throws EntityNotFoundError if species doesn't exist
/

---

### removeVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:84`

**Signature:**
```typescript
export function removeVariable(
```

**Description:**
Remove a variable from a model, with reference checking
@param model Model to remove variable from
@param name Variable name to remove
@returns New model with variable removed
@throws VariableInUseError if variable is still referenced
@throws EntityNotFoundError if variable doesn't exist
/

---

### renameVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:156`

**Signature:**
```typescript
export function renameVariable(
```

**Description:**
Rename a variable throughout a model
@param model Model to rename variable in
@param oldName Current variable name
@param newName New variable name
@returns New model with variable renamed
@throws EntityNotFoundError if variable doesn't exist
/

---

### rewrite

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:410`

**Signature:**
```typescript
export function rewrite(
```

**Description:**
Run the rule engine on `expr` per RFC §5.2.5. Top-down walker, per-
pass sealing of rewritten subtrees, fixed-point loop bounded by
`maxPasses`. Throws `RuleEngineError(E_RULES_NOT_CONVERGED)` on
non-convergence.
/

**Available in other languages:**
- [Julia](julia.md#rewrite)
- [Julia](julia.md#rewrite)

---

### save

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/serialize.ts:15`

**Signature:**
```typescript
export function save(file: EsmFile): string {
```

**Description:**
Serialize an EsmFile object to a formatted JSON string

@param file - The EsmFile object to serialize
@returns Formatted JSON string representation
/

**Available in other languages:**
- [Julia](julia.md#save)
- [Julia](julia.md#save)
- [Julia](julia.md#save)

---

### setupErrorLogging

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/error-handling.ts:628`

**Signature:**
```typescript
export function setupErrorLogging(config: ErrorLoggerConfig = { logLevel: 'info', logToConsole: true }) {
```

---

### simplify

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/expression.ts:215`

**Signature:**
```typescript
export function simplify(expr: Expr): Expr {
```

**Description:**
Simplify an expression using basic algebraic rules
@param expr Expression to simplify
@returns Simplified expression
/

**Available in other languages:**
- [Julia](julia.md#simplify)
- [Julia](julia.md#simplify)

---

### stoichiometricMatrix

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/reactions.ts:225`

**Signature:**
```typescript
export function stoichiometricMatrix(system: ReactionSystem): {
```

**Description:**
Compute stoichiometric matrix from a reaction system

Returns the net stoichiometric matrix (species × reactions) where:
- Rows are species (in declaration order)
- Columns are reactions (in array order)
- Entry [i][j] = (stoichiometry as product) - (stoichiometry as substrate) for species i in reaction j
- Null substrates contribute 0 to substrate stoichiometry
- Null products contribute 0 to product stoichiometry

@param system ReactionSystem to compute matrix from
@returns Object containing matrix, species list, and reactions list
/

---

### substitute

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/substitute.ts:28`

**Signature:**
```typescript
export function substitute(
```

**Description:**
Recursively substitute variable references in an expression with bound expressions.
Handles scoped references (Model.Subsystem.var) by splitting on '.' and matching
path through system hierarchy per format spec Section 4.3.

@param expr - Expression to substitute into
@param bindings - Variable name to expression mappings
@param context - Optional context for resolving scoped references
@returns New expression with substitutions applied (immutable)
/

**Available in other languages:**
- [Julia](julia.md#substitute)
- [Julia](julia.md#substitute)

---

### substituteInEquations

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/edit.ts:246`

**Signature:**
```typescript
export function substituteInEquations(
```

**Description:**
Apply substitutions to all equations in a model
@param model Model to apply substitutions to
@param bindings Variable name to expression mappings
@returns New model with substitutions applied
/

---

### substituteInModel

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/substitute.ts:150`

**Signature:**
```typescript
export function substituteInModel(
```

**Description:**
Apply substitution across all equations in a model.
Returns a new model with substitutions applied (immutable).

@param model - Model to substitute into
@param bindings - Variable name to expression mappings
@param context - Optional context for resolving scoped references
@returns New model with substitutions applied
/

---

### substituteInReactionSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/substitute.ts:202`

**Signature:**
```typescript
export function substituteInReactionSystem(
```

**Description:**
Apply substitution across all rate expressions in a reaction system.
Returns a new reaction system with substitutions applied (immutable).

@param system - ReactionSystem to substitute into
@param bindings - Variable name to expression mappings
@param context - Optional context for resolving scoped references
@returns New reaction system with substitutions applied
/

---

### substrateMatrix

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/reactions.ts:280`

**Signature:**
```typescript
export function substrateMatrix(system: ReactionSystem): number[][] {
```

**Description:**
Compute substrate stoichiometric matrix from a reaction system

Returns the substrate stoichiometric matrix (species × reactions) where:
- Rows are species (in declaration order)
- Columns are reactions (in array order)
- Entry [i][j] = substrate stoichiometry for species i in reaction j
- Null substrates contribute 0

@param system ReactionSystem to compute matrix from
@returns Substrate stoichiometric matrix
/

---

### toAscii

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/pretty-print.ts:578`

**Signature:**
```typescript
export function toAscii(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
```

**Description:**
Format an expression as plain ASCII text
/

---

### toJuliaCode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/codegen.ts:19`

**Signature:**
```typescript
export function toJuliaCode(file: EsmFile): string {
```

**Description:**
Generate a self-contained Julia script from an ESM file
@param file ESM file to generate Julia code for
@returns Julia script as a string
/

---

### toLatex

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/pretty-print.ts:537`

**Signature:**
```typescript
export function toLatex(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
```

**Description:**
Format an expression as LaTeX mathematical notation
/

---

### toMathML

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/pretty-print.ts:618`

**Signature:**
```typescript
export function toMathML(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
```

**Description:**
Format an expression as MathML markup for web/academic publishing
/

---

### toPythonCode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/codegen.ts:102`

**Signature:**
```typescript
export function toPythonCode(file: EsmFile): string {
```

**Description:**
Generate a self-contained Python script from an ESM file
@param file ESM file to generate Python code for
@returns Python script as a string
/

---

### toUnicode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/pretty-print.ts:497`

**Signature:**
```typescript
export function toUnicode(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
```

**Description:**
Format an expression as Unicode mathematical notation
/

---

### unitsCompatible

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/unit-conversion.ts:240`

**Signature:**
```typescript
export function unitsCompatible(a: string, b: string): boolean {
```

**Description:**
Report whether two unit strings represent compatible (same-dimension) quantities.
A non-throwing companion to `convertUnits`.
/

---

### unregisterGridFamily

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/grid-accessor.ts:142`

**Signature:**
```typescript
export function unregisterGridFamily(family: string): boolean {
```

**Description:**
Remove a registration. Returns `true` iff the family was present.
Intended for tests and ESD hot-reload; not a production path.
/

---

### validate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/validate.ts:1222`

**Signature:**
```typescript
export function validate(data: string | object): ValidationResult {
```

**Description:**
Validate ESM data and return structured validation result.

@param data - ESM data as JSON string or object
@returns ValidationResult with validation status and errors
/

**Available in other languages:**
- [Julia](julia.md#validate)
- [Julia](julia.md#validate)

---

### validateSchema

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/parse.ts:1848`

**Signature:**
```typescript
export function validateSchema(data: unknown): SchemaError[] {
```

**Description:**
Validate data against the ESM schema
/

---

### validateUnits

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/units.ts:301`

**Signature:**
```typescript
export function validateUnits(file: EsmFile): UnitWarning[] {
```

**Description:**
Validate dimensional consistency of all equations in an ESM file.
/

---

## Types

### AffectEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:860`

**Definition:**
```typescript
export interface AffectEquation {
```

**Description:**
An affect equation in an event: lhs is the target variable (string), rhs is an expression.
/

**Available in other languages:**
- [Julia](julia.md#affectequation)
- [Python](python.md#affectequation)

---

### AstStore

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/ast-store.ts:39`

**Definition:**
```typescript
export interface AstStore {
```

**Description:**
AST Store interface providing centralized ESM file management
/

---

### AstStoreConfig

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/ast-store.ts:27`

**Definition:**
```typescript
export interface AstStoreConfig {
```

**Description:**
Configuration for the AST store
/

---

### BoundaryCondition

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1135`

**Definition:**
```typescript
export interface BoundaryCondition {
```

**Description:**
Model-level boundary condition entry (v0.2.0). Constrains one model variable on one boundary side. See docs/rfcs/discretization.md §9.2 for full semantics. This object lives under models.<M>.boundary_conditions keyed by user-supplied id; it replaces the v0.1.0 domains.<d>.boundary_conditions list.
/

**Available in other languages:**
- [Python](python.md#boundarycondition)

---

### CanonicalDims

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/unit-conversion.ts:16`

**Definition:**
```typescript
export interface CanonicalDims {
```

---

### CellCenter

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/grid-accessor.ts:30`

**Definition:**
```typescript
export interface CellCenter {
```

**Description:**
Geographic / cartesian center of a cell. Spherical families populate
`lon`/`lat`; cartesian families populate `x`/`y`/`z`. The accessor
may populate both for families that carry both coordinate systems.
/

---

### Change

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/interactive-editor/index.ts:73`

**Definition:**
```typescript
export interface Change {
```

---

### Command

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/interactive-editor/index.ts:56`

**Definition:**
```typescript
export interface Command {
```

---

### CommandResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/interactive-editor/index.ts:67`

**Definition:**
```typescript
export interface CommandResult {
```

---

### CommonSubexpression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:70`

**Definition:**
```typescript
export interface CommonSubexpression {
```

---

### ComplexityMetrics

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:52`

**Definition:**
```typescript
export interface ComplexityMetrics {
```

---

### ComponentGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/graph.ts:53`

**Definition:**
```typescript
export interface ComponentGraph {
```

---

### ComponentNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/graph.ts:12`

**Definition:**
```typescript
export interface ComponentNode {
```

**Available in other languages:**
- [Julia](julia.md#componentnode)
- [Python](python.md#componentnode)

---

### ConnectorEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1588`

**Definition:**
```typescript
export interface ConnectorEquation {
```

**Description:**
A single equation in a ConnectorSystem linking two coupled systems.
/

**Available in other languages:**
- [Python](python.md#connectorequation)

---

### ContinuousEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:900`

**Definition:**
```typescript
export interface ContinuousEvent {
```

**Description:**
Fires when a condition expression crosses zero (root-finding). Maps to MTK SymbolicContinuousCallback.
/

**Available in other languages:**
- [Julia](julia.md#continuousevent)
- [Python](python.md#continuousevent)

---

### CoordinateTransform

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1737`

**Definition:**
```typescript
export interface CoordinateTransform {
```

**Available in other languages:**
- [Python](python.md#coordinatetransform)

---

### CouplingCallback

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1651`

**Definition:**
```typescript
export interface CouplingCallback {
```

**Description:**
Register a callback for simulation events.
/

**Available in other languages:**
- [Julia](julia.md#couplingcallback)

---

### CouplingCouple

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1562`

**Definition:**
```typescript
export interface CouplingCouple {
```

**Description:**
Bi-directional coupling via explicit ConnectorSystem equations.
/

**Available in other languages:**
- [Julia](julia.md#couplingcouple)
- [Python](python.md#couplingcouple)

---

### CouplingEdge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/graph.ts:35`

**Definition:**
```typescript
export interface CouplingEdge {
```

**Available in other languages:**
- [Julia](julia.md#couplingedge)
- [Python](python.md#couplingedge)
- [Python](python.md#couplingedge)

---

### CouplingOperatorApply

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1640`

**Definition:**
```typescript
export interface CouplingOperatorApply {
```

**Description:**
Register an Operator to run during simulation.
/

**Available in other languages:**
- [Julia](julia.md#couplingoperatorapply)

---

### CouplingOperatorCompose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1534`

**Definition:**
```typescript
export interface CouplingOperatorCompose {
```

**Description:**
Match LHS time derivatives and add RHS terms together.
/

**Available in other languages:**
- [Julia](julia.md#couplingoperatorcompose)

---

### CouplingVariableMap

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1609`

**Definition:**
```typescript
export interface CouplingVariableMap {
```

**Description:**
Replace a parameter in one system with a variable from another.
/

**Available in other languages:**
- [Julia](julia.md#couplingvariablemap)

---

### DataLoaderDeterminism

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1418`

**Definition:**
```typescript
export interface DataLoaderDeterminism {
```

**Description:**
Reproducibility contract a mesh (or grid) loader advertises to bindings (discretization RFC §8.A and §14 item 4). A binding that cannot honor the declared endian / float_format / integer_width MUST reject the file at load rather than silently reinterpreting bytes.
/

**Available in other languages:**
- [Julia](julia.md#dataloaderdeterminism)
- [Python](python.md#dataloaderdeterminism)

---

### DataLoaderMesh

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1391`

**Definition:**
```typescript
export interface DataLoaderMesh {
```

**Description:**
Mesh-loader descriptor (discretization RFC §8.A). Declares which loader fields are integer-typed connectivity tables vs float-typed metric arrays and the topological family the loader serves. Only meaningful when the enclosing DataLoader has kind='mesh'.
/

**Available in other languages:**
- [Julia](julia.md#dataloadermesh)
- [Python](python.md#dataloadermesh)

---

### DataLoaderRegridding

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1454`

**Definition:**
```typescript
export interface DataLoaderRegridding {
```

**Description:**
Structural regridding configuration. Algorithm-specific tuning parameters are runtime-side and not in the schema.
/

**Available in other languages:**
- [Julia](julia.md#dataloaderregridding)
- [Python](python.md#dataloaderregridding)

---

### DataLoaderSource

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1313`

**Definition:**
```typescript
export interface DataLoaderSource {
```

**Description:**
File discovery configuration. Describes how to locate data files at runtime via URL templates with date/variable substitutions.
/

**Available in other languages:**
- [Julia](julia.md#dataloadersource)
- [Python](python.md#dataloadersource)

---

### DataLoaderSpatial

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1355`

**Definition:**
```typescript
export interface DataLoaderSpatial {
```

**Description:**
Spatial grid description for a data source.
/

**Available in other languages:**
- [Julia](julia.md#dataloaderspatial)
- [Python](python.md#dataloaderspatial)

---

### DataLoaderStaggering

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1385`

**Definition:**
```typescript
export interface DataLoaderStaggering {
```

**Description:**
Per-dimension grid staggering (centered or edge-aligned).
/

---

### DataLoaderTemporal

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1326`

**Definition:**
```typescript
export interface DataLoaderTemporal {
```

**Description:**
Temporal coverage and record layout for a data source.
/

**Available in other languages:**
- [Julia](julia.md#dataloadertemporal)
- [Python](python.md#dataloadertemporal)

---

### DataLoaderVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1435`

**Definition:**
```typescript
export interface DataLoaderVariable {
```

**Description:**
A variable exposed by a data loader, mapped from a source-file variable.
/

**Available in other languages:**
- [Julia](julia.md#dataloadervariable)
- [Python](python.md#dataloadervariable)

---

### DemoPageConfig

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/tests/demo/demo-pages.ts:8`

**Definition:**
```typescript
export interface DemoPageConfig {
```

---

### DependencyEdge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/graph.ts:87`

**Definition:**
```typescript
export interface DependencyEdge {
```

**Available in other languages:**
- [Julia](julia.md#dependencyedge)
- [Python](python.md#dependencyedge)

---

### DependencyGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:42`

**Definition:**
```typescript
export interface DependencyGraph extends Graph<DependencyNode, DependencyRelation> {
```

---

### DependencyNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:12`

**Definition:**
```typescript
export interface DependencyNode {
```

---

### DependencyRelation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:28`

**Definition:**
```typescript
export interface DependencyRelation {
```

---

### DeprecatedDomainBoundaryCondition

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1746`

**Definition:**
```typescript
export interface DeprecatedDomainBoundaryCondition {
```

**Description:**
@deprecated
DEPRECATED v0.1.0 domain-level boundary condition entry. Retained for the v0.2.0 transitional window only (RFC §10.1). Loaders emit E_DEPRECATED_DOMAIN_BC when encountering it; use Model.boundary_conditions (keyed map of BoundaryCondition entries) instead.
/

---

### DerivativeResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:126`

**Definition:**
```typescript
export interface DerivativeResult {
```

---

### Discretization

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1811`

**Definition:**
```typescript
export interface Discretization {
```

**Description:**
A named stencil template. Each entry maps a PDE operator class (via an applies_to pattern) to a combination (combine) over neighbors with symbolic coefficients. See RFC §7.1.
/

---

### DiscretizeOptions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/discretize.ts:46`

**Definition:**
```typescript
export interface DiscretizeOptions {
```

---

### Domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1692`

**Definition:**
```typescript
export interface Domain {
```

**Description:**
Spatiotemporal domain specification (DomainInfo).
/

**Available in other languages:**
- [Julia](julia.md#domain)
- [Python](python.md#domain)

---

### DragState

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/interactive-editor/index.ts:41`

**Definition:**
```typescript
export interface DragState {
```

---

### ESMError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/error-handling.ts:101`

**Definition:**
```typescript
export interface ESMError {
```

**Available in other languages:**
- [Julia](julia.md#esmerror)
- [Python](python.md#esmerror)

---

### ESMFormat2

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:692`

**Definition:**
```typescript
export interface ESMFormat2 {
```

---

### EditorState

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/interactive-editor/index.ts:24`

**Definition:**
```typescript
export interface EditorState {
```

---

### Equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:852`

**Definition:**
```typescript
export interface Equation {
```

**Description:**
An equation: lhs = rhs (or lhs ~ rhs in MTK notation).
/

**Available in other languages:**
- [Julia](julia.md#equation)
- [Python](python.md#equation)
- [Python](python.md#equation)

---

### ErrorContext

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/error-handling.ts:80`

**Definition:**
```typescript
export interface ErrorContext {
```

**Available in other languages:**
- [Julia](julia.md#errorcontext)
- [Python](python.md#errorcontext)

---

### ErrorLoggerConfig

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/error-handling.ts:621`

**Definition:**
```typescript
export interface ErrorLoggerConfig {
```

---

### EsmCouplingGraphProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/web-components.ts:84`

**Definition:**
```typescript
export interface EsmCouplingGraphProps {
```

**Description:**
Web component wrapper for CouplingGraph

Usage:
<esm-coupling-graph
esm-file='{"components": [...], "coupling": [...]}'
width="800"
height="600"
interactive="true">
</esm-coupling-graph>
/

---

### EsmCouplingGraphProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/web-components.ts:143`

**Definition:**
```typescript
export interface EsmCouplingGraphProps {
```

**Description:**
Web component wrapper for CouplingGraph

Usage:
<esm-coupling-graph
esm-file='{"components": [...], "coupling": [...]}'
width="800"
height="600"
interactive="true"
allow-editing="true">
</esm-coupling-graph>
/

---

### EsmExpressionEditorProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/web-components.ts:55`

**Definition:**
```typescript
export interface EsmExpressionEditorProps {
```

**Description:**
Web component wrapper for EquationEditor (expression editing)

Usage:
<esm-expression-editor
expression='{"op": "+", "args": [1, 2]}'
allow-editing="true"
show-palette="true">
</esm-expression-editor>
/

---

### EsmExpressionNodeProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/web-components.ts:36`

**Definition:**
```typescript
export interface EsmExpressionNodeProps {
```

**Description:**
Web component wrapper for ExpressionNode

Usage:
<esm-expression-node
expression='{"op": "+", "args": [1, 2]}'
path='["root"]'
allow-editing="true">
</esm-expression-node>
/

---

### EsmFileEditorProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/web-components.ts:97`

**Definition:**
```typescript
export interface EsmFileEditorProps {
```

**Description:**
Web component wrapper for complete ESM file editing

Usage:
<esm-file-editor
esm-file='{"components": {...}, "coupling": [...]}'
allow-editing="true"
enable-undo="true">
</esm-file-editor>
/

---

### EsmFileSummaryProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/web-components.ts:135`

**Definition:**
```typescript
export interface EsmFileSummaryProps {
```

**Description:**
Web component wrapper for FileSummary

Usage:
<esm-file-summary
esm-file='{"components": [...], "coupling": [...]}'
show-details="true"
show-export-options="true">
</esm-file-summary>
/

---

### EsmModelEditorProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/web-components.ts:59`

**Definition:**
```typescript
export interface EsmModelEditorProps {
```

**Description:**
Web component wrapper for ModelEditor

Usage:
<esm-model-editor
model='{"variables": {...}, "equations": [...]}'
allow-editing="true">
</esm-model-editor>
/

---

### EsmModelEditorProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/web-components.ts:76`

**Definition:**
```typescript
export interface EsmModelEditorProps {
```

**Description:**
Web component wrapper for ModelEditor

Usage:
<esm-model-editor
model='{"variables": {...}, "equations": [...]}'
allow-editing="true"
show-validation="true">
</esm-model-editor>
/

---

### EsmReactionEditorProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/web-components.ts:120`

**Definition:**
```typescript
export interface EsmReactionEditorProps {
```

**Description:**
Web component wrapper for ReactionEditor

Usage:
<esm-reaction-editor
reaction-system='{"species": {...}, "reactions": [...]}'
allow-editing="true"
show-validation="true">
</esm-reaction-editor>
/

---

### EsmSimulationControlsProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/web-components.ts:157`

**Definition:**
```typescript
export interface EsmSimulationControlsProps {
```

**Description:**
Web component wrapper for SimulationControls

Usage:
<esm-simulation-controls
esm-file='{"components": [...], "coupling": [...]}'
is-running="false"
progress="50"
available-backends='["julia", "python"]'>
</esm-simulation-controls>
/

---

### EsmValidationPanelProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/web-components.ts:108`

**Definition:**
```typescript
export interface EsmValidationPanelProps {
```

**Description:**
Web component wrapper for ValidationPanel

Usage:
<esm-validation-panel
model='{"variables": {...}, "equations": [...]}'
validation-errors='[{"message": "Error", "path": "..."}]'
show-details="true">
</esm-validation-panel>
/

---

### Example

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1020`

**Definition:**
```typescript
export interface Example {
```

**Description:**
An inline illustrative example of how to run the enclosing component. Defines the run configuration and one or more plots derived from the result.
/

**Available in other languages:**
- [Python](python.md#example)

---

### ExpressionLocation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:82`

**Definition:**
```typescript
export interface ExpressionLocation {
```

---

### ExpressionPattern

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:92`

**Definition:**
```typescript
export interface ExpressionPattern {
```

---

### FixSuggestion

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/error-handling.ts:92`

**Definition:**
```typescript
export interface FixSuggestion {
```

**Available in other languages:**
- [Julia](julia.md#fixsuggestion)
- [Python](python.md#fixsuggestion)

---

### FlattenMetadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/flatten.ts:36`

**Definition:**
```typescript
export interface FlattenMetadata {
```

**Description:**
Metadata describing the origin of the flattened system.
/

**Available in other languages:**
- [Julia](julia.md#flattenmetadata)
- [Python](python.md#flattenmetadata)

---

### FlattenedEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/flatten.ts:24`

**Definition:**
```typescript
export interface FlattenedEquation {
```

**Description:**
A single equation in the flattened system, with dot-namespaced variable names.
/

**Available in other languages:**
- [Python](python.md#flattenedequation)

---

### FlattenedSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/flatten.ts:46`

**Definition:**
```typescript
export interface FlattenedSystem {
```

**Description:**
A fully flattened representation of a coupled ESM system.
/

**Available in other languages:**
- [Julia](julia.md#flattenedsystem)
- [Python](python.md#flattenedsystem)

---

### FunctionalAffect

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:873`

**Definition:**
```typescript
export interface FunctionalAffect {
```

**Description:**
Registered functional affect handler (alternative to symbolic affects).
/

**Available in other languages:**
- [Julia](julia.md#functionalaffect)
- [Python](python.md#functionalaffect)

---

### FunctionalAffect1

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1665`

**Definition:**
```typescript
export interface FunctionalAffect1 {
```

**Description:**
Registered functional affect handler (alternative to symbolic affects).
/

---

### GhostVarDecl

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1890`

**Definition:**
```typescript
export interface GhostVarDecl {
```

**Description:**
Optional ghost-cell variable declaration used by a discretization scheme (e.g. a periodic-BC halo). See RFC §9 for boundary-condition interaction.
/

---

### Graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/graph.ts:61`

**Definition:**
```typescript
export interface Graph<N, E> {
```

**Available in other languages:**
- [Julia](julia.md#graph)
- [Python](python.md#graph)

---

### GraphExportOptions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:162`

**Definition:**
```typescript
export interface GraphExportOptions {
```

---

### GridAccessor

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/grid-accessor.ts:43`

**Definition:**
```typescript
export interface GridAccessor {
```

**Description:**
Accessor contract every ESD-provided concrete grid implements.
Subsumes the GRIDS_API §3.4 `Grid` interface (family/dtype/toESM)
and adds the three accessor methods called out in gt-j2b8.
/

**Available in other languages:**
- [Python](python.md#gridaccessor)

---

### GridConnectivity

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1933`

**Definition:**
```typescript
export interface GridConnectivity {
```

**Description:**
Unstructured-grid connectivity table (e.g., cellsOnEdge, edgesOnCell). Integer-indexed lookup produced by a mesh loader. See §6.3.
/

**Available in other languages:**
- [Python](python.md#gridconnectivity)

---

### GridExtent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1926`

**Definition:**
```typescript
export interface GridExtent {
```

**Description:**
Per-dimension extent for cartesian or cubed_sphere grids. `n` is either an integer literal or a parameter reference naming the dimension count; `spacing` is 'uniform' or 'nonuniform' for cartesian (determines whether metric arrays are scalar or rank-1).
/

**Available in other languages:**
- [Python](python.md#gridextent)

---

### GridMeta

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:73`

**Definition:**
```typescript
export interface GridMeta {
```

---

### GridMetricArray

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1904`

**Definition:**
```typescript
export interface GridMetricArray {
```

**Description:**
A named metric array declared on a grid (e.g., dx, dcEdge, areaCell). See §6.5.
/

**Available in other languages:**
- [Python](python.md#gridmetricarray)

---

### Guard

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:60`

**Definition:**
```typescript
export interface Guard {
```

**Available in other languages:**
- [Julia](julia.md#guard)
- [Python](python.md#guard)

---

### HistoryEntry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/history.ts:26`

**Definition:**
```typescript
export interface HistoryEntry {
```

**Description:**
History entry representing a state snapshot
/

---

### HoverState

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/interactive-editor/index.ts:79`

**Definition:**
```typescript
export interface HoverState {
```

---

### Interface

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1761`

**Definition:**
```typescript
export interface Interface {
```

**Description:**
Geometric connection between two domains of potentially different dimensionality.
/

**Available in other languages:**
- [Julia](julia.md#interface)

---

### InterfaceConstraint

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1801`

**Definition:**
```typescript
export interface InterfaceConstraint {
```

**Description:**
Constraint on a non-shared dimension at the interface.
/

---

### LayoutAlgorithm

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:141`

**Definition:**
```typescript
export interface LayoutAlgorithm {
```

---

### LayoutResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:149`

**Definition:**
```typescript
export interface LayoutResult<N> {
```

---

### LoadOptions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/parse.ts:2286`

**Definition:**
```typescript
export interface LoadOptions {
```

**Description:**
Options controlling how `load()` parses and represents an ESM file.
/

---

### MatchResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:102`

**Definition:**
```typescript
export interface MatchResult {
```

---

### Metadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:760`

**Definition:**
```typescript
export interface Metadata {
```

**Description:**
Authorship, provenance, and description.
/

**Available in other languages:**
- [Julia](julia.md#metadata)
- [Python](python.md#metadata)

---

### Model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:791`

**Definition:**
```typescript
export interface Model {
```

**Description:**
An ODE system — a fully specified set of time-dependent equations.
/

**Available in other languages:**
- [Julia](julia.md#model)
- [Python](python.md#model)

---

### NumericLiteral

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/numeric-literal.ts:29`

**Definition:**
```typescript
export interface NumericLiteral {
```

---

### Operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1467`

**Definition:**
```typescript
export interface Operator {
```

**Description:**
A registered runtime operator (e.g., dry deposition, wet scavenging).
/

**Available in other languages:**
- [Julia](julia.md#operator)
- [Python](python.md#operator)

---

### Optimization

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/analysis/types.ts:112`

**Definition:**
```typescript
export interface Optimization {
```

---

### Parameter

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1258`

**Definition:**
```typescript
export interface Parameter {
```

**Description:**
A parameter in a reaction system.
/

**Available in other languages:**
- [Julia](julia.md#parameter)
- [Python](python.md#parameter)

---

### ParameterSweep

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1073`

**Definition:**
```typescript
export interface ParameterSweep {
```

**Description:**
Optional parameter sweep. When present, the example represents a family of runs (one per Cartesian combination) rather than a single trajectory.
/

**Available in other languages:**
- [Python](python.md#parametersweep)

---

### ParsedUnit

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/unit-conversion.ts:27`

**Definition:**
```typescript
export interface ParsedUnit {
```

---

### PlotAxis

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1098`

**Definition:**
```typescript
export interface PlotAxis {
```

**Description:**
Axis specification: any state variable, observed variable, parameter name, or swept parameter may be used.
/

**Available in other languages:**
- [Python](python.md#plotaxis)

---

### PlotSeries

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1128`

**Definition:**
```typescript
export interface PlotSeries {
```

**Description:**
A single named series for multi-series line or scatter plots.
/

**Available in other languages:**
- [Python](python.md#plotseries)

---

### PlotValue

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1111`

**Definition:**
```typescript
export interface PlotValue {
```

**Description:**
Required for heatmap; defines the color channel. Ignored for line/scatter. For field_snapshot, the variable plotted as the color channel (use `value.variable`); `at_time` and `reduce` are ignored — the field is sampled at `at_time` declared on the plot.
/

**Available in other languages:**
- [Python](python.md#plotvalue)

---

### Reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1270`

**Definition:**
```typescript
export interface Reaction {
```

**Description:**
A single reaction in a reaction system.
/

**Available in other languages:**
- [Julia](julia.md#reaction)
- [Python](python.md#reaction)

---

### ReactionSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1189`

**Definition:**
```typescript
export interface ReactionSystem {
```

**Description:**
A reaction network — declarative representation of chemical or biological reactions.
/

**Available in other languages:**
- [Julia](julia.md#reactionsystem)
- [Python](python.md#reactionsystem)

---

### Reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:782`

**Definition:**
```typescript
export interface Reference {
```

**Description:**
Academic citation or data source reference.
/

**Available in other languages:**
- [Julia](julia.md#reference)
- [Python](python.md#reference)

---

### RegisteredFunction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1492`

**Definition:**
```typescript
export interface RegisteredFunction {
```

**Description:**
A named pure function that may be invoked inside an expression via the 'call' op. Analogous to Operator, but intended for side-effect-free callables embedded directly in expression trees (e.g. interpolation handlers, Julia @register_symbolic stubs, table lookups).
/

**Available in other languages:**
- [Julia](julia.md#registeredfunction)
- [Python](python.md#registeredfunction)

---

### Rule

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:65`

**Definition:**
```typescript
export interface Rule {
```

**Available in other languages:**
- [Julia](julia.md#rule)
- [Python](python.md#rule)

---

### RuleContext

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:85`

**Definition:**
```typescript
export interface RuleContext {
```

**Available in other languages:**
- [Julia](julia.md#rulecontext)
- [Python](python.md#rulecontext)

---

### SchemaError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/parse.ts:17`

**Definition:**
```typescript
export interface SchemaError {
```

**Description:**
Schema validation error with JSON Pointer path
/

**Available in other languages:**
- [Julia](julia.md#schemaerror)

---

### SpatialDimension

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1731`

**Definition:**
```typescript
export interface SpatialDimension {
```

**Description:**
Specification of a single spatial dimension.
/

**Available in other languages:**
- [Python](python.md#spatialdimension)

---

### Species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1242`

**Definition:**
```typescript
export interface Species {
```

**Description:**
A reactive species in a reaction system.
/

**Available in other languages:**
- [Julia](julia.md#species)
- [Python](python.md#species)

---

### StencilEntry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1872`

**Definition:**
```typescript
export interface StencilEntry {
```

**Description:**
One neighbor contribution to a discretization stencil: a selector picking out the neighbor(s) and a coefficient expression.
/

---

### StoichiometryEntry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1293`

**Definition:**
```typescript
export interface StoichiometryEntry {
```

**Description:**
A species with its stoichiometric coefficient in a reaction. Coefficients MUST be positive and finite (NaN / ±Infinity are rejected at parse time). Fractional values are supported to preserve fidelity with atmospheric-chemistry mechanisms whose products include non-integer yields (e.g. `0.87 CH2O`, `1.86 CH3O2`). Integer values remain valid — they are a subset of the permitted number range.
/

**Available in other languages:**
- [Julia](julia.md#stoichiometryentry)

---

### StructuralError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/validate.ts:60`

**Definition:**
```typescript
export interface StructuralError {
```

**Description:**
Structural error type matching the format specification
/

**Available in other languages:**
- [Julia](julia.md#structuralerror)

---

### SubstitutionContext

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/substitute.ts:14`

**Definition:**
```typescript
export interface SubstitutionContext {
```

**Description:**
Context for resolving scoped references during substitution
/

---

### SubsystemRef

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:932`

**Definition:**
```typescript
export interface SubsystemRef {
```

**Description:**
A reference to an external ESM file containing a model or reaction system definition. The ref field can be a relative or absolute local file path, or an HTTP/HTTPS URL. Relative paths are resolved relative to the directory of the referencing file.
/

---

### SweepRange

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1086`

**Definition:**
```typescript
export interface SweepRange {
```

**Description:**
Generated range; mutually exclusive with values.
/

**Available in other languages:**
- [Python](python.md#sweeprange)

---

### Test

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:954`

**Definition:**
```typescript
export interface Test {
```

**Description:**
An inline validation test for the enclosing model or reaction system. Defines the run configuration (initial conditions, parameter overrides, time span) and the scalar assertions that must hold.
/

**Available in other languages:**
- [Julia](julia.md#test)
- [Python](python.md#test)

---

### TimeSpan

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:987`

**Definition:**
```typescript
export interface TimeSpan {
```

**Description:**
Simulation time interval expressed in the component's time units.
/

**Available in other languages:**
- [Julia](julia.md#timespan)
- [Python](python.md#timespan)

---

### Tolerance

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:941`

**Definition:**
```typescript
export interface Tolerance {
```

**Description:**
Model-level default numerical tolerance for tests, used when a test or assertion does not provide its own.
/

**Available in other languages:**
- [Julia](julia.md#tolerance)
- [Python](python.md#tolerance)

---

### Tolerance1

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:994`

**Definition:**
```typescript
export interface Tolerance1 {
```

**Description:**
Test-level default tolerance applied to all assertions in this test that do not override it.
/

---

### Tolerance2

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1007`

**Definition:**
```typescript
export interface Tolerance2 {
```

**Description:**
Per-assertion tolerance override. If present, this takes precedence over the test-level and model-level defaults.
/

---

### Tolerance3

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/generated.ts:1300`

**Definition:**
```typescript
export interface Tolerance3 {
```

**Description:**
System-level default numerical tolerance for tests, used when a test or assertion does not provide its own.
/

---

### TooltipData

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/interactive-editor/index.ts:86`

**Definition:**
```typescript
export interface TooltipData {
```

---

### UndoHistory

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/history.ts:38`

**Definition:**
```typescript
export interface UndoHistory {
```

**Description:**
Undo/redo history management interface
/

---

### UndoHistoryConfig

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/history.ts:14`

**Definition:**
```typescript
export interface UndoHistoryConfig {
```

**Description:**
Configuration for undo history behavior
/

---

### UndoRedoState

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/interactive-editor/index.ts:48`

**Definition:**
```typescript
export interface UndoRedoState {
```

---

### UnitResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/units.ts:26`

**Definition:**
```typescript
export interface UnitResult {
```

**Description:**
Result of dimensional analysis for a single expression.
/

---

### UnitWarning

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/units.ts:34`

**Definition:**
```typescript
export interface UnitWarning {
```

**Description:**
Dimensional-consistency warning emitted during file-level validation.
/

**Available in other languages:**
- [Python](python.md#unitwarning)

---

### ValidationConfig

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/validation.ts:16`

**Definition:**
```typescript
export interface ValidationConfig {
```

**Description:**
Configuration for validation behavior
/

---

### ValidationError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/validate.ts:40`

**Definition:**
```typescript
export interface ValidationError {
```

**Description:**
Validation error with structured details
/

**Available in other languages:**
- [Python](python.md#validationerror)
- [Python](python.md#validationerror)

---

### ValidationError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/interactive-editor/index.ts:32`

**Definition:**
```typescript
export interface ValidationError {
```

**Available in other languages:**
- [Python](python.md#validationerror)
- [Python](python.md#validationerror)

---

### ValidationErrorWithMetadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/validation.ts:28`

**Definition:**
```typescript
export interface ValidationErrorWithMetadata extends ValidationError {
```

**Description:**
Extended validation error with UI-specific metadata
/

---

### ValidationResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/validate.ts:50`

**Definition:**
```typescript
export interface ValidationResult {
```

**Description:**
Structured validation result
/

**Available in other languages:**
- [Julia](julia.md#validationresult)
- [Python](python.md#validationresult)

---

### ValidationSignals

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-editor/src/primitives/validation.ts:40`

**Definition:**
```typescript
export interface ValidationSignals {
```

**Description:**
Validation signals interface providing reactive validation state
/

---

### VariableMeta

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/rule-engine.ts:79`

**Definition:**
```typescript
export interface VariableMeta {
```

---

### VariableNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/earthsci-toolkit/src/graph.ts:75`

**Definition:**
```typescript
export interface VariableNode {
```

**Available in other languages:**
- [Julia](julia.md#variablenode)
- [Python](python.md#variablenode)

---

