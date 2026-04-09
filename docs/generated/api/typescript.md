# Typescript API Reference

Complete API reference for the ESM Format Typescript library.

## Functions

### addContinuousEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:387`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:464`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:404`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:193`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:262`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:306`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:61`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/complexity.ts:17`

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

### buildDependencyGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/dependency-graph.ts:19`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/migration.ts:22`

**Signature:**
```typescript
export function canMigrate(sourceVersion: string, targetVersion: string): boolean {
```

**Description:**
Check if migration is possible from the source version to target version.
/

---

### checkDimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/units.ts:210`

**Signature:**
```typescript
export function checkDimensions(expr: Expression, unitBindings: Map<string, DimensionalRep>): UnitResult {
```

**Description:**
Check dimensional consistency of an expression

Follows rules from ESM spec Section 3.3.1:
- Addition/subtraction: operands must have same dimensions
- Multiplication: dimensions add
- Division: dimensions subtract
- D(x,t): dimension of x divided by dimension of t
- Functions require dimensionless arguments; result is dimensionless

@param expr Expression to check
@param unitBindings Map of variable names to their dimensional representations
@returns Unit result with dimensions and any warnings
/

---

### classifyComplexity

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/complexity.ts:219`

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

### compareAnalysis

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/index.ts:261`

**Signature:**
```typescript
export function compareAnalysis(results1: any, results2: any) {
```

**Description:**
Compare analysis results between different expressions or models
/

---

### compareComplexity

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/complexity.ts:187`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/graph.ts:349`

**Signature:**
```typescript
export function componentExists(esmFile: EsmFile, componentId: string): boolean {
```

**Description:**
Utility to check if a component exists in the ESM file
/

---

### componentGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/graph.ts:290`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/graph.ts:104`

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
- [Rust](rust.md#component_graph)
- [Rust](rust.md#component_graph)

---

### compose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:506`

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
- [Python](python.md#compose)
- [Python](python.md#compose)
- [Python](python.md#compose)
- [Python](python.md#compose)
- [Python](python.md#compose)
- [Python](python.md#compose)
- [Python](python.md#compose)
- [Python](python.md#compose)
- [Python](python.md#compose)
- [Python](python.md#compose)
- [Python](python.md#compose)
- [Python](python.md#compose)
- [Python](python.md#compose)

---

### contains

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/expression.ts:65`

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
- [Rust](rust.md#contains)

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/demo/demo-pages.ts:333`

**Signature:**
```typescript
export function createDemoServer() {
```

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/reactions.ts:28`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/complexity.ts:324`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/differentiation.ts:19`

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
- [Python](python.md#differentiate)

---

### downloadExport

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/ModelExportUtils.ts:631`

**Signature:**
```typescript
export function downloadExport(content: string, filename: string, mimeType: string = 'text/plain'): void {
```

**Description:**
Download exported model as file
/

---

### estimateParallelPotential

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/complexity.ts:282`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/common-subexpressions.ts:288`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/expression.ts:85`

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
- [Rust](rust.md#evaluate)

---

### exportModel

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/ModelExportUtils.ts:33`

**Signature:**
```typescript
export function exportModel(model: Model, format: ExportFormat, options: ExportOptions = {}): string {
```

**Description:**
Export model to various formats
/

---

### exportResults

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/index.ts:246`

**Signature:**
```typescript
export function exportResults(results: any, format: 'json' | 'yaml' | 'markdown' | 'html') {
```

**Description:**
Export analysis results to various formats
/

---

### expressionGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/graph.ts:377`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:589`

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
- [Python](python.md#extract)
- [Python](python.md#extract)
- [Python](python.md#extract)
- [Python](python.md#extract)
- [Python](python.md#extract)
- [Python](python.md#extract)
- [Python](python.md#extract)
- [Python](python.md#extract)
- [Python](python.md#extract)
- [Python](python.md#extract)
- [Python](python.md#extract)

---

### findCommonSubexpressions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/common-subexpressions.ts:18`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/common-subexpressions.ts:87`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/common-subexpressions.ts:211`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/common-subexpressions.ts:159`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/differentiation.ts:544`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/dependency-graph.ts:463`

**Signature:**
```typescript
export function findDeadVariables(graph: DependencyGraph): DependencyNode[] {
```

**Description:**
Find dead variables (those that are defined but never used)
/

---

### findDependencyChains

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/dependency-graph.ts:480`

**Signature:**
```typescript
export function findDependencyChains(graph: DependencyGraph, startNode: string, maxDepth: number = 10): string[][] {
```

**Description:**
Find variable dependency chains (paths from parameters to state variables)
/

---

### findExpensiveSubexpressions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/complexity.ts:242`

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

### formatResults

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/index.ts:238`

**Signature:**
```typescript
export function formatResults(results: any): string {
```

**Description:**
Format analysis results for display
/

---

### formatUserFriendly

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/error-handling.ts:195`

**Signature:**
```typescript
export function formatUserFriendly(error: ESMError): string {
```

---

### freeParameters

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/expression.ts:45`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/expression.ts:20`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/common-subexpressions.ts:298`

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

### getAvailableFormats

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/ModelExportUtils.ts:609`

**Signature:**
```typescript
export function getAvailableFormats(): ExportFormat[] {
```

**Description:**
Get available export formats
/

---

### getComponentType

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/graph.ts:361`

**Signature:**
```typescript
export function getComponentType(esmFile: EsmFile, componentId: string): ComponentNode['type'] | null {
```

**Description:**
Get the type of a component by its ID
/

---

### getFileExtension

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/ModelExportUtils.ts:616`

**Signature:**
```typescript
export function getFileExtension(format: ExportFormat): string {
```

**Description:**
Get file extension for export format
/

---

### getProfiler

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/error-handling.ts:486`

**Signature:**
```typescript
export function getProfiler(): PerformanceProfiler {
```

---

### getSupportedMigrationTargets

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/migration.ts:30`

**Signature:**
```typescript
export function getSupportedMigrationTargets(sourceVersion: string): string[] {
```

**Description:**
Get the list of schema versions that a given source version can migrate to.
/

---

### gradient

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/differentiation.ts:52`

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

**Available in other languages:**
- [Python](python.md#gradient)
- [Python](python.md#gradient)
- [Python](python.md#gradient)
- [Python](python.md#gradient)
- [Python](python.md#gradient)
- [Python](python.md#gradient)
- [Python](python.md#gradient)
- [Python](python.md#gradient)

---

### groupSubexpressionsByType

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/common-subexpressions.ts:320`

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

### higherOrderDerivative

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/differentiation.ts:494`

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

### isDifferentiable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/differentiation.ts:527`

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

### load

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/parse.ts:1439`

**Signature:**
```typescript
export function load(input: string | object): EsmFile {
```

**Description:**
Load an ESM file from a JSON string or pre-parsed object

@param input - JSON string or pre-parsed JavaScript object
@returns Typed EsmFile object
@throws {ParseError} When JSON parsing fails or version is incompatible
@throws {SchemaValidationError} When schema validation fails
/

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
- [Rust](rust.md#load)
- [Rust](rust.md#load)

---

### mapVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:527`

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

### merge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:553`

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
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)
- [Python](python.md#merge)

---

### migrate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/migration.ts:40`

**Signature:**
```typescript
export function migrate(file: EsmFile, targetVersion: string): EsmFile {
```

**Description:**
Migrate an ESM file from its current schema version to the target version.
/

**Available in other languages:**
- [Julia](julia.md#migrate)
- [Python](python.md#migrate)
- [Rust](rust.md#migrate)

---

### parseUnit

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/units.ts:65`

**Signature:**
```typescript
export function parseUnit(unitStr: string): DimensionalRep {
```

**Description:**
Parse a unit string into canonical dimensional representation

Handles common patterns:
- "mol/mol" → {dimensionless: true} (cancels out)
- "cm^3/molec/s" → {cm: 3, molec: -1, s: -1}
- "K" → {K: 1}
- "m/s" → {m: 1, s: -1}
- "1/s" → {s: -1}
- "degrees" → {dimensionless: true}

@param unitStr Unit string to parse
@returns Dimensional representation
/

---

### partialDerivatives

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/differentiation.ts:36`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/reactions.ts:314`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/error-handling.ts:491`

**Signature:**
```typescript
export function profileOperation(operationName: string) {
```

---

### registerWebComponents

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/web-components.ts:565`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:482`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:211`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:422`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:279`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:328`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:83`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:155`

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

### save

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/serialize.ts:15`

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
- [Rust](rust.md#save)
- [Rust](rust.md#save)

---

### setupErrorLogging

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/error-handling.ts:628`

**Signature:**
```typescript
export function setupErrorLogging(config: ErrorLoggerConfig = { logLevel: 'info', logToConsole: true }) {
```

---

### simplify

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/expression.ts:210`

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
- [Rust](rust.md#simplify)

---

### stoichiometricMatrix

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/reactions.ts:225`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/substitute.ts:27`

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
- [Python](python.md#substitute)
- [Python](python.md#substitute)
- [Rust](rust.md#substitute)
- [Rust](rust.md#substitute)

---

### substituteInEquations

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/edit.ts:245`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/substitute.ts:148`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/substitute.ts:200`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/reactions.ts:280`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/pretty-print.ts:482`

**Signature:**
```typescript
export function toAscii(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
```

**Description:**
Format an expression as plain ASCII text
/

---

### toJuliaCode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/codegen.ts:18`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/pretty-print.ts:441`

**Signature:**
```typescript
export function toLatex(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
```

**Description:**
Format an expression as LaTeX mathematical notation
/

---

### toMathML

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/pretty-print.ts:522`

**Signature:**
```typescript
export function toMathML(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
```

**Description:**
Format an expression as MathML markup for web/academic publishing
/

---

### toPythonCode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/codegen.ts:108`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/pretty-print.ts:401`

**Signature:**
```typescript
export function toUnicode(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
```

**Description:**
Format an expression as Unicode mathematical notation
/

**Available in other languages:**
- [Python](python.md#tounicode)

---

### validate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/validate.ts:578`

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
- [Rust](rust.md#validate)
- [Rust](rust.md#validate)

---

### validateSchema

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/parse.ts:1127`

**Signature:**
```typescript
export function validateSchema(data: unknown): SchemaError[] {
```

**Description:**
Validate data against the ESM schema
/

---

### validateUnits

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/units.ts:408`

**Signature:**
```typescript
export function validateUnits(file: EsmFile): UnitWarning[] {
```

**Description:**
Validate dimensional consistency of all equations in an ESM file
@param file ESM file to validate
@returns Array of unit warnings
/

---

## Types

### AffectEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:366`

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
- [Rust](rust.md#affectequation)

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:786`

**Definition:**
```typescript
export interface BoundaryCondition {
```

**Description:**
Boundary condition for one or more dimensions.
/

**Available in other languages:**
- [Python](python.md#boundarycondition)

---

### Change

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/index.ts:73`

**Definition:**
```typescript
export interface Change {
```

---

### Command

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/index.ts:56`

**Definition:**
```typescript
export interface Command {
```

**Available in other languages:**
- [Python](python.md#command)
- [Python](python.md#command)
- [Python](python.md#command)

---

### CommandResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/index.ts:67`

**Definition:**
```typescript
export interface CommandResult {
```

---

### CommonSubexpression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:69`

**Definition:**
```typescript
export interface CommonSubexpression {
```

---

### ComplexityMetrics

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:51`

**Definition:**
```typescript
export interface ComplexityMetrics {
```

---

### ComponentGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/graph.ts:53`

**Definition:**
```typescript
export interface ComponentGraph {
```

**Available in other languages:**
- [Rust](rust.md#componentgraph)

---

### ComponentNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/graph.ts:12`

**Definition:**
```typescript
export interface ComponentNode {
```

**Available in other languages:**
- [Julia](julia.md#componentnode)
- [Python](python.md#componentnode)
- [Rust](rust.md#componentnode)

---

### ConnectorEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:641`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:406`

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
- [Rust](rust.md#continuousevent)

---

### CoordinateTransform

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:778`

**Definition:**
```typescript
export interface CoordinateTransform {
```

**Available in other languages:**
- [Python](python.md#coordinatetransform)
- [Python](python.md#coordinatetransform)

---

### CouplingCallback

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:696`

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

### CouplingCouple2

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:616`

**Definition:**
```typescript
export interface CouplingCouple2 {
```

**Description:**
Bi-directional coupling via coupletype dispatch.
/

**Available in other languages:**
- [Julia](julia.md#couplingcouple2)

---

### CouplingEdge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/graph.ts:35`

**Definition:**
```typescript
export interface CouplingEdge {
```

**Available in other languages:**
- [Julia](julia.md#couplingedge)
- [Python](python.md#couplingedge)
- [Python](python.md#couplingedge)
- [Rust](rust.md#couplingedge)

---

### CouplingOperatorApply

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:685`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:596`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:662`

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

### DataLoader

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:524`

**Definition:**
```typescript
export interface DataLoader {
```

**Description:**
An external data source registration. Runtime-specific; registered by type and loader_id.
/

**Available in other languages:**
- [Julia](julia.md#dataloader)
- [Python](python.md#dataloader)
- [Rust](rust.md#dataloader)

---

### DataLoaderProvides

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:564`

**Definition:**
```typescript
export interface DataLoaderProvides {
```

**Description:**
A variable provided by a data loader.
/

---

### DemoPageConfig

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/demo/demo-pages.ts:8`

**Definition:**
```typescript
export interface DemoPageConfig {
```

---

### DependencyEdge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/graph.ts:87`

**Definition:**
```typescript
export interface DependencyEdge {
```

**Available in other languages:**
- [Julia](julia.md#dependencyedge)
- [Python](python.md#dependencyedge)
- [Rust](rust.md#dependencyedge)

---

### DependencyGraph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:41`

**Definition:**
```typescript
export interface DependencyGraph extends Graph<DependencyNode, DependencyRelation> {
```

**Available in other languages:**
- [Python](python.md#dependencygraph)

---

### DependencyNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:11`

**Definition:**
```typescript
export interface DependencyNode {
```

---

### DependencyRelation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:27`

**Definition:**
```typescript
export interface DependencyRelation {
```

---

### DerivativeResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:125`

**Definition:**
```typescript
export interface DerivativeResult {
```

---

### DimensionalRep

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/units.ts:14`

**Definition:**
```typescript
export interface DimensionalRep {
```

**Description:**
Canonical dimensional representation
Maps base dimensions to their powers
/

---

### Domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:737`

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
- [Python](python.md#domain)
- [Python](python.md#domain)
- [Rust](rust.md#domain)

---

### DragState

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/index.ts:41`

**Definition:**
```typescript
export interface DragState {
```

---

### ESMError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/error-handling.ts:101`

**Definition:**
```typescript
export interface ESMError {
```

**Available in other languages:**
- [Julia](julia.md#esmerror)
- [Python](python.md#esmerror)

---

### EarthSciSerialization2

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:185`

**Definition:**
```typescript
export interface EarthSciSerialization2 {
```

---

### EditorState

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/index.ts:24`

**Definition:**
```typescript
export interface EditorState {
```

---

### Equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:358`

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
- [Rust](rust.md#equation)

---

### ErrorContext

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/error-handling.ts:80`

**Definition:**
```typescript
export interface ErrorContext {
```

**Available in other languages:**
- [Julia](julia.md#errorcontext)
- [Python](python.md#errorcontext)

---

### ErrorLoggerConfig

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/error-handling.ts:621`

**Definition:**
```typescript
export interface ErrorLoggerConfig {
```

---

### EsmCouplingGraphProps

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/web-components.ts:84`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/web-components.ts:36`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/web-components.ts:135`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/web-components.ts:59`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/web-components.ts:157`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/web-components.ts:108`

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

### ExportOptions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/ModelExportUtils.ts:19`

**Definition:**
```typescript
export interface ExportOptions {
```

**Description:**
Export options for different formats
/

---

### ExpressionLocation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:81`

**Definition:**
```typescript
export interface ExpressionLocation {
```

---

### ExpressionNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:300`

**Definition:**
```typescript
export interface ExpressionNode {
```

**Description:**
An operation in the expression AST.
/

**Available in other languages:**
- [Rust](rust.md#expressionnode)

---

### ExpressionPattern

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:91`

**Definition:**
```typescript
export interface ExpressionPattern {
```

---

### FixSuggestion

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/error-handling.ts:92`

**Definition:**
```typescript
export interface FixSuggestion {
```

**Available in other languages:**
- [Julia](julia.md#fixsuggestion)
- [Python](python.md#fixsuggestion)

---

### FunctionalAffect

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:379`

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
- [Rust](rust.md#functionalaffect)

---

### FunctionalAffect1

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:710`

**Definition:**
```typescript
export interface FunctionalAffect1 {
```

**Description:**
Registered functional affect handler (alternative to symbolic affects).
/

---

### Graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/graph.ts:61`

**Definition:**
```typescript
export interface Graph<N, E> {
```

**Available in other languages:**
- [Julia](julia.md#graph)
- [Python](python.md#graph)

---

### GraphExportOptions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:161`

**Definition:**
```typescript
export interface GraphExportOptions {
```

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/index.ts:79`

**Definition:**
```typescript
export interface HoverState {
```

---

### LayoutAlgorithm

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:140`

**Definition:**
```typescript
export interface LayoutAlgorithm {
```

---

### LayoutResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:148`

**Definition:**
```typescript
export interface LayoutResult<N> {
```

---

### MatchResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:101`

**Definition:**
```typescript
export interface MatchResult {
```

---

### Metadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:225`

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
- [Python](python.md#metadata)
- [Python](python.md#metadata)
- [Rust](rust.md#metadata)

---

### Model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:256`

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
- [Python](python.md#model)
- [Rust](rust.md#model)

---

### ModelVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:284`

**Definition:**
```typescript
export interface ModelVariable {
```

**Description:**
A variable in an ODE model.
/

**Available in other languages:**
- [Julia](julia.md#modelvariable)
- [Python](python.md#modelvariable)
- [Rust](rust.md#modelvariable)

---

### Operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:571`

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
- [Python](python.md#operator)
- [Python](python.md#operator)
- [Rust](rust.md#operator)

---

### Optimization

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/analysis/types.ts:111`

**Definition:**
```typescript
export interface Optimization {
```

**Available in other languages:**
- [Python](python.md#optimization)

---

### Parameter

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:486`

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
- [Rust](rust.md#parameter)

---

### Reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:494`

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
- [Rust](rust.md#reaction)

---

### ReactionSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:438`

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
- [Rust](rust.md#reactionsystem)

---

### Reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:247`

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
- [Python](python.md#reference)
- [Rust](rust.md#reference)

---

### SchemaError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/parse.ts:15`

**Definition:**
```typescript
export interface SchemaError {
```

**Description:**
Schema validation error with JSON Pointer path
/

**Available in other languages:**
- [Julia](julia.md#schemaerror)
- [Python](python.md#schemaerror)
- [Rust](rust.md#schemaerror)

---

### Solver

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:819`

**Definition:**
```typescript
export interface Solver {
```

**Description:**
Solver strategy for time integration.
/

**Available in other languages:**
- [Julia](julia.md#solver)
- [Python](python.md#solver)
- [Rust](rust.md#solver)

---

### SpatialDimension

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:772`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:478`

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
- [Rust](rust.md#species)

---

### StoichiometryEntry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/generated.ts:517`

**Definition:**
```typescript
export interface StoichiometryEntry {
```

**Description:**
A species with its stoichiometric coefficient in a reaction.
/

**Available in other languages:**
- [Julia](julia.md#stoichiometryentry)

---

### StructuralError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/validate.ts:51`

**Definition:**
```typescript
export interface StructuralError {
```

**Description:**
Structural error type matching the format specification
/

**Available in other languages:**
- [Julia](julia.md#structuralerror)
- [Rust](rust.md#structuralerror)

---

### SubstitutionContext

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/substitute.ts:13`

**Definition:**
```typescript
export interface SubstitutionContext {
```

**Description:**
Context for resolving scoped references during substitution
/

---

### TooltipData

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/index.ts:86`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/index.ts:48`

**Definition:**
```typescript
export interface UndoRedoState {
```

---

### UnitResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/units.ts:37`

**Definition:**
```typescript
export interface UnitResult {
```

**Description:**
Result of dimensional analysis
/

---

### UnitWarning

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/units.ts:45`

**Definition:**
```typescript
export interface UnitWarning {
```

**Description:**
Unit validation warning
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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/validate.ts:31`

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
- [Python](python.md#validationerror)
- [Python](python.md#validationerror)
- [Python](python.md#validationerror)
- [Python](python.md#validationerror)

---

### ValidationError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/interactive-editor/index.ts:32`

**Definition:**
```typescript
export interface ValidationError {
```

**Available in other languages:**
- [Python](python.md#validationerror)
- [Python](python.md#validationerror)
- [Python](python.md#validationerror)
- [Python](python.md#validationerror)
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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/validate.ts:41`

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
- [Rust](rust.md#validationresult)

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

### VariableNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/esm-format/src/graph.ts:75`

**Definition:**
```typescript
export interface VariableNode {
```

**Available in other languages:**
- [Julia](julia.md#variablenode)
- [Python](python.md#variablenode)
- [Rust](rust.md#variablenode)

---

