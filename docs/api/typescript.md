# Typescript API Reference

Complete API reference for the ESM Format Typescript library.

## Functions

### addContinuousEvent

**File:** `packages/esm-format/src/edit.ts:387`

```typescript
export function addContinuousEvent(
```

Add a continuous event to a model
@param model Model to add event to
@param event Continuous event to add
@returns New model with event added
/

---

### addCoupling

**File:** `packages/esm-format/src/edit.ts:464`

```typescript
export function addCoupling(
```

Add a coupling entry to an ESM file
@param file ESM file to add coupling to
@param entry Coupling entry to add
@returns New ESM file with coupling added
/

---

### addDiscreteEvent

**File:** `packages/esm-format/src/edit.ts:404`

```typescript
export function addDiscreteEvent(
```

Add a discrete event to a model
@param model Model to add event to
@param event Discrete event to add
@returns New model with event added
/

---

### addEquation

**File:** `packages/esm-format/src/edit.ts:193`

```typescript
export function addEquation(
```

Add a new equation to a model
@param model Model to add equation to
@param equation Equation to add
@returns New model with equation added
/

---

### addReaction

**File:** `packages/esm-format/src/edit.ts:262`

```typescript
export function addReaction(
```

Add a new reaction to a reaction system
@param system ReactionSystem to add reaction to
@param reaction Reaction to add
@returns New reaction system with reaction added
/

---

### addSpecies

**File:** `packages/esm-format/src/edit.ts:306`

```typescript
export function addSpecies(
```

Add a new species to a reaction system
@param system ReactionSystem to add species to
@param name Species name
@param species Species definition
@returns New reaction system with species added
/

---

### addVariable

**File:** `packages/esm-format/src/edit.ts:61`

```typescript
export function addVariable(
```

Add a new variable to a model
@param model Model to add variable to
@param name Variable name
@param variable Variable definition
@returns New model with variable added
/

---

### analyzeComplexity

**File:** `packages/esm-format/src/analysis/complexity.ts:17`

```typescript
export function analyzeComplexity(expr: Expr): ComplexityMetrics {
```

Analyze the complexity of an expression
@param expr Expression to analyze
@returns Complexity metrics
/

---

### buildDependencyGraph

**File:** `packages/esm-format/src/analysis/dependency-graph.ts:19`

```typescript
export function buildDependencyGraph(
```

Build a dependency graph from an ESM file, model, or expression
@param target The target to analyze
@param options Analysis options
@returns Dependency graph with nodes and edges
/

---

### checkDimensions

**File:** `packages/esm-format/src/units.ts:210`

```typescript
export function checkDimensions(expr: Expression, unitBindings: Map<string, DimensionalRep>): UnitResult {
```

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

**File:** `packages/esm-format/src/analysis/complexity.ts:219`

```typescript
export function classifyComplexity(expr: Expr): 'trivial' | 'simple' | 'moderate' | 'complex' | 'very_complex' {
```

Classify expression complexity level
@param expr Expression to classify
@returns Complexity level
/

---

### compareAnalysis

**File:** `packages/esm-format/src/analysis/index.ts:218`

```typescript
export function compareAnalysis(results1: any, results2: any) {
```

Compare analysis results between different expressions or models
/

---

### compareComplexity

**File:** `packages/esm-format/src/analysis/complexity.ts:187`

```typescript
export function compareComplexity(expr1: Expr, expr2: Expr): number {
```

Compare complexity of two expressions
@param expr1 First expression
@param expr2 Second expression
@returns Comparison result (-1: expr1 simpler, 0: equal, 1: expr1 more complex)
/

---

### componentExists

**File:** `packages/esm-format/src/graph.ts:349`

```typescript
export function componentExists(esmFile: EsmFile, componentId: string): boolean {
```

Utility to check if a component exists in the ESM file
/

---

### componentGraph

**File:** `packages/esm-format/src/graph.ts:290`

```typescript
export function componentGraph(file: EsmFile): Graph<ComponentNode, CouplingEdge> {
```

Extract the system graph from an ESM file as specified in task.
Returns a directed graph where nodes are model components and edges are coupling rules.
Implements the Graph interface with adjacency methods.
/

---

### component_graph

**File:** `packages/esm-format/src/graph.ts:104`

```typescript
export function component_graph(esmFile: EsmFile): ComponentGraph {
```

Extract the system graph from an ESM file.
Returns a directed graph where nodes are model components and edges are coupling rules.
/

---

### compose

**File:** `packages/esm-format/src/edit.ts:506`

```typescript
export function compose(
```

Compose two systems using a coupling entry
@param file ESM file
@param a First system name
@param b Second system name
@returns New ESM file with composition coupling added
/

---

### contains

**File:** `packages/esm-format/src/expression.ts:65`

```typescript
export function contains(expr: Expr, varName: string): boolean {
```

Check if an expression contains a specific variable
@param expr Expression to search
@param varName Variable name to look for
@returns True if the variable appears in the expression
/

---

### createAstStore

**File:** `packages/esm-editor/src/primitives/ast-store.ts:129`

```typescript
export function createAstStore(config: AstStoreConfig = {}): AstStore {
```

Create a centralized AST store for ESM file management

@param config - Configuration options
@returns AST store interface with reactive state and path-based updates
/

---

### createDemoServer

**File:** `packages/esm-format/src/demo/demo-pages.ts:333`

```typescript
export function createDemoServer() {
```

---

### createUndoHistory

**File:** `packages/esm-editor/src/primitives/history.ts:70`

```typescript
export function createUndoHistory(
```

Create undo/redo history management for an ESM file

@param file - Reactive signal containing the current ESM file
@param setFile - Function to update the ESM file
@param config - Optional configuration
@returns History management interface with undo/redo functions
/

---

### createUndoKeyboardHandler

**File:** `packages/esm-editor/src/primitives/history.ts:281`

```typescript
export function createUndoKeyboardHandler(
```

Default keyboard shortcut handler for undo/redo
Can be used independently of createUndoHistory if needed
/

---

### deriveODEs

**File:** `packages/esm-format/src/reactions.ts:28`

```typescript
export function deriveODEs(system: ReactionSystem): Model {
```

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

**File:** `packages/esm-format/src/analysis/complexity.ts:324`

```typescript
export function detectStabilityIssues(expr: Expr): Array<{
```

Detect numerical stability issues in expressions
@param expr Expression to analyze
@returns Array of potential stability issues
/

---

### differentiate

**File:** `packages/esm-format/src/analysis/differentiation.ts:19`

```typescript
export function differentiate(expr: Expr, variable: string): DerivativeResult {
```

Compute the symbolic derivative of an expression with respect to a variable
@param expr Expression to differentiate
@param variable Variable with respect to which to differentiate
@returns Derivative result with simplified form
/

---

### downloadExport

**File:** `packages/esm-format/src/interactive-editor/ModelExportUtils.ts:631`

```typescript
export function downloadExport(content: string, filename: string, mimeType: string = 'text/plain'): void {
```

Download exported model as file
/

---

### estimateParallelPotential

**File:** `packages/esm-format/src/analysis/complexity.ts:282`

```typescript
export function estimateParallelPotential(expr: Expr): number {
```

Estimate parallel execution potential
@param expr Expression to analyze
@returns Parallelization score (0-1, higher means more parallelizable)
/

---

### estimateSavings

**File:** `packages/esm-format/src/analysis/common-subexpressions.ts:288`

```typescript
export function estimateSavings(commonSubexpressions: CommonSubexpression[]): number {
```

Estimate the cost savings from factoring out common subexpressions
@param commonSubexpressions Array of common subexpressions
@returns Total estimated cost savings
/

---

### evaluate

**File:** `packages/esm-format/src/expression.ts:85`

```typescript
export function evaluate(expr: Expr, bindings: Map<string, number>): number {
```

Evaluate an expression numerically with variable bindings
@param expr Expression to evaluate
@param bindings Map of variable names to their numeric values
@returns Numeric result
@throws Error if variables are unbound or evaluation fails
/

---

### exportModel

**File:** `packages/esm-format/src/interactive-editor/ModelExportUtils.ts:33`

```typescript
export function exportModel(model: Model, format: ExportFormat, options: ExportOptions = {}): string {
```

Export model to various formats
/

---

### exportResults

**File:** `packages/esm-format/src/analysis/index.ts:203`

```typescript
export function exportResults(results: any, format: 'json' | 'yaml' | 'markdown' | 'html') {
```

Export analysis results to various formats
/

---

### expressionGraph

**File:** `packages/esm-format/src/graph.ts:377`

```typescript
export function expressionGraph(
```

Extract variable-level dependency graph from an ESM file, model, reaction system, equation, reaction, or expression.
Creates a directed graph where nodes are variables/parameters/species and edges represent dependencies.

@param target The target to analyze (EsmFile, Model, ReactionSystem, Equation, Reaction, or Expr)
@param options Optional settings for graph generation
@returns Graph with VariableNode nodes and DependencyEdge edges
/

---

### extract

**File:** `packages/esm-format/src/edit.ts:588`

```typescript
export function extract(
```

Extract a specific component from an ESM file into a new file
@param file ESM file to extract from
@param componentName Name of the component to extract
@returns New ESM file containing only the specified component
@throws EntityNotFoundError if component not found
/

---

### findCommonSubexpressions

**File:** `packages/esm-format/src/analysis/common-subexpressions.ts:18`

```typescript
export function findCommonSubexpressions(expr: Expr, minComplexity: number = 5): CommonSubexpression[] {
```

Find common subexpressions in a single expression
@param expr Expression to analyze
@param minComplexity Minimum complexity threshold for considering subexpressions
@returns Array of common subexpressions found
/

---

### findCommonSubexpressionsAcrossExpressions

**File:** `packages/esm-format/src/analysis/common-subexpressions.ts:87`

```typescript
export function findCommonSubexpressionsAcrossExpressions(
```

Find common subexpressions across multiple expressions
@param expressions Array of expressions to analyze
@param minComplexity Minimum complexity threshold
@returns Array of common subexpressions found across expressions
/

---

### findCommonSubexpressionsInEsmFile

**File:** `packages/esm-format/src/analysis/common-subexpressions.ts:211`

```typescript
export function findCommonSubexpressionsInEsmFile(esmFile: EsmFile, minComplexity: number = 5): CommonSubexpression[] {
```

Find common subexpressions across an entire ESM file
@param esmFile ESM file to analyze
@param minComplexity Minimum complexity threshold
@returns Array of common subexpressions found across the file
/

---

### findCommonSubexpressionsInModel

**File:** `packages/esm-format/src/analysis/common-subexpressions.ts:159`

```typescript
export function findCommonSubexpressionsInModel(model: Model, minComplexity: number = 5): CommonSubexpression[] {
```

Find common subexpressions in a model
@param model Model to analyze
@param minComplexity Minimum complexity threshold
@returns Array of common subexpressions found in the model
/

---

### findCriticalPoints

**File:** `packages/esm-format/src/analysis/differentiation.ts:544`

```typescript
export function findCriticalPoints(expr: Expr, variable: string): {
```

Find critical points (where derivative equals zero)
This is a symbolic analysis - actual solving would require numerical methods
@param expr Expression to analyze
@param variable Variable to find critical points for
@returns Information about potential critical points
/

---

### findDeadVariables

**File:** `packages/esm-format/src/analysis/dependency-graph.ts:463`

```typescript
export function findDeadVariables(graph: DependencyGraph): DependencyNode[] {
```

Find dead variables (those that are defined but never used)
/

---

### findDependencyChains

**File:** `packages/esm-format/src/analysis/dependency-graph.ts:480`

```typescript
export function findDependencyChains(graph: DependencyGraph, startNode: string, maxDepth: number = 10): string[][] {
```

Find variable dependency chains (paths from parameters to state variables)
/

---

### findExpensiveSubexpressions

**File:** `packages/esm-format/src/analysis/complexity.ts:242`

```typescript
export function findExpensiveSubexpressions(expr: Expr, limit: number = 5): Array<{
```

Find the most expensive sub-expressions in an expression
@param expr Expression to analyze
@param limit Maximum number of results to return
@returns Array of expensive sub-expressions with their costs
/

---

### formatResults

**File:** `packages/esm-format/src/analysis/index.ts:195`

```typescript
export function formatResults(results: any): string {
```

Format analysis results for display
/

---

### formatUserFriendly

**File:** `packages/esm-format/src/error-handling.ts:195`

```typescript
export function formatUserFriendly(error: ESMError): string {
```

---

### freeParameters

**File:** `packages/esm-format/src/expression.ts:45`

```typescript
export function freeParameters(expr: Expr, model: Model): Set<string> {
```

Extract free parameters from an expression within a model context
@param expr Expression to analyze
@param model Model context to determine parameter vs state variables
@returns Set of parameter names referenced in the expression
/

---

### freeVariables

**File:** `packages/esm-format/src/expression.ts:20`

```typescript
export function freeVariables(expr: Expr): Set<string> {
```

Extract all variable references from an expression
@param expr Expression to analyze
@returns Set of variable names referenced in the expression
/

---

### generateFactoredVariableNames

**File:** `packages/esm-format/src/analysis/common-subexpressions.ts:298`

```typescript
export function generateFactoredVariableNames(
```

Generate variable names for factored subexpressions
@param commonSubexpressions Array of common subexpressions
@param prefix Prefix for generated variable names
@returns Map of expressions to generated variable names
/

---

### getAvailableFormats

**File:** `packages/esm-format/src/interactive-editor/ModelExportUtils.ts:609`

```typescript
export function getAvailableFormats(): ExportFormat[] {
```

Get available export formats
/

---

### getComponentType

**File:** `packages/esm-format/src/graph.ts:361`

```typescript
export function getComponentType(esmFile: EsmFile, componentId: string): ComponentNode['type'] | null {
```

Get the type of a component by its ID
/

---

### getFileExtension

**File:** `packages/esm-format/src/interactive-editor/ModelExportUtils.ts:616`

```typescript
export function getFileExtension(format: ExportFormat): string {
```

Get file extension for export format
/

---

### getProfiler

**File:** `packages/esm-format/src/error-handling.ts:486`

```typescript
export function getProfiler(): PerformanceProfiler {
```

---

### gradient

**File:** `packages/esm-format/src/analysis/differentiation.ts:52`

```typescript
export function gradient(expr: Expr, variables?: string[]): DerivativeResult[] {
```

Compute the gradient (all first partial derivatives)
@param expr Expression to differentiate
@param variables Array of variables (if not provided, will extract from expression)
@returns Gradient as array of derivatives
/

---

### groupSubexpressionsByType

**File:** `packages/esm-format/src/analysis/common-subexpressions.ts:320`

```typescript
export function groupSubexpressionsByType(
```

Group common subexpressions by their structure type
@param commonSubexpressions Array of common subexpressions
@returns Grouped subexpressions by operation type
/

---

### higherOrderDerivative

**File:** `packages/esm-format/src/analysis/differentiation.ts:494`

```typescript
export function higherOrderDerivative(expr: Expr, variable: string, order: number = 1): DerivativeResult {
```

Compute higher-order derivatives
@param expr Expression to differentiate
@param variable Variable with respect to which to differentiate
@param order Order of derivative (default: 1)
@returns Higher-order derivative result
/

---

### isDifferentiable

**File:** `packages/esm-format/src/analysis/differentiation.ts:527`

```typescript
export function isDifferentiable(expr: Expr, variable: string): boolean {
```

Check if an expression is differentiable with respect to a variable
@param expr Expression to check
@param variable Variable to check differentiability with respect to
@returns True if differentiable, false otherwise
/

---

### load

**File:** `packages/esm-format/src/parse.ts:376`

```typescript
export function load(input: string | object): EsmFile {
```

Load an ESM file from a JSON string or pre-parsed object

@param input - JSON string or pre-parsed JavaScript object
@returns Typed EsmFile object
@throws {ParseError} When JSON parsing fails or version is incompatible
@throws {SchemaValidationError} When schema validation fails
/

---

### mapVariable

**File:** `packages/esm-format/src/edit.ts:527`

```typescript
export function mapVariable(
```

Map a variable from one system to another with optional transformation
@param file ESM file
@param from Source variable reference
@param to Target variable reference
@param transform Optional transformation expression
@returns New ESM file with variable mapping coupling added
/

---

### merge

**File:** `packages/esm-format/src/edit.ts:552`

```typescript
export function merge(
```

Merge two ESM files
@param fileA First ESM file
@param fileB Second ESM file
@returns New ESM file with merged content
/

---

### parseUnit

**File:** `packages/esm-format/src/units.ts:65`

```typescript
export function parseUnit(unitStr: string): DimensionalRep {
```

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

**File:** `packages/esm-format/src/analysis/differentiation.ts:36`

```typescript
export function partialDerivatives(expr: Expr, variables: string[]): Map<string, DerivativeResult> {
```

Compute partial derivatives with respect to multiple variables
@param expr Expression to differentiate
@param variables Array of variables to differentiate with respect to
@returns Map of variable names to their derivative results
/

---

### productMatrix

**File:** `packages/esm-format/src/reactions.ts:314`

```typescript
export function productMatrix(system: ReactionSystem): number[][] {
```

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

**File:** `packages/esm-format/src/error-handling.ts:491`

```typescript
export function profileOperation(operationName: string) {
```

---

### registerWebComponents

**File:** `packages/esm-format/src/web-components.ts:579`

```typescript
export function registerWebComponents() {
```

---

### registerWebComponents

**File:** `packages/esm-editor/src/web-components.ts:411`

```typescript
export function registerWebComponents() {
```

Register all ESM editor web components
/

---

### removeCoupling

**File:** `packages/esm-format/src/edit.ts:482`

```typescript
export function removeCoupling(
```

Remove a coupling entry from an ESM file by index
@param file ESM file to remove coupling from
@param index Index of coupling entry to remove
@returns New ESM file with coupling removed
@throws EntityNotFoundError if index is out of bounds
/

---

### removeEquation

**File:** `packages/esm-format/src/edit.ts:211`

```typescript
export function removeEquation(
```

Remove an equation from a model
@param model Model to remove equation from
@param indexOrLhs Either the numeric index or the LHS expression of the equation
@returns New model with equation removed
@throws EntityNotFoundError if equation not found
/

---

### removeEvent

**File:** `packages/esm-format/src/edit.ts:422`

```typescript
export function removeEvent(
```

Remove an event from a model by name
@param model Model to remove event from
@param name Event name to remove
@returns New model with event removed
@throws EntityNotFoundError if event not found
/

---

### removeReaction

**File:** `packages/esm-format/src/edit.ts:279`

```typescript
export function removeReaction(
```

Remove a reaction from a reaction system
@param system ReactionSystem to remove reaction from
@param id Reaction ID to remove
@returns New reaction system with reaction removed
@throws EntityNotFoundError if reaction not found
/

---

### removeSpecies

**File:** `packages/esm-format/src/edit.ts:328`

```typescript
export function removeSpecies(
```

Remove a species from a reaction system, with reference checking
@param system ReactionSystem to remove species from
@param name Species name to remove
@returns New reaction system with species removed
@throws VariableInUseError if species is still referenced in reactions
@throws EntityNotFoundError if species doesn't exist
/

---

### removeVariable

**File:** `packages/esm-format/src/edit.ts:83`

```typescript
export function removeVariable(
```

Remove a variable from a model, with reference checking
@param model Model to remove variable from
@param name Variable name to remove
@returns New model with variable removed
@throws VariableInUseError if variable is still referenced
@throws EntityNotFoundError if variable doesn't exist
/

---

### renameVariable

**File:** `packages/esm-format/src/edit.ts:155`

```typescript
export function renameVariable(
```

Rename a variable throughout a model
@param model Model to rename variable in
@param oldName Current variable name
@param newName New variable name
@returns New model with variable renamed
@throws EntityNotFoundError if variable doesn't exist
/

---

### save

**File:** `packages/esm-format/src/serialize.ts:15`

```typescript
export function save(file: EsmFile): string {
```

Serialize an EsmFile object to a formatted JSON string

@param file - The EsmFile object to serialize
@returns Formatted JSON string representation
/

---

### setupErrorLogging

**File:** `packages/esm-format/src/error-handling.ts:628`

```typescript
export function setupErrorLogging(config: ErrorLoggerConfig = { logLevel: 'info', logToConsole: true }) {
```

---

### simplify

**File:** `packages/esm-format/src/expression.ts:210`

```typescript
export function simplify(expr: Expr): Expr {
```

Simplify an expression using basic algebraic rules
@param expr Expression to simplify
@returns Simplified expression
/

---

### stoichiometricMatrix

**File:** `packages/esm-format/src/reactions.ts:225`

```typescript
export function stoichiometricMatrix(system: ReactionSystem): {
```

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

**File:** `packages/esm-format/src/substitute.ts:19`

```typescript
export function substitute(expr: Expr, bindings: Record<string, Expr>): Expr {
```

Recursively substitute variable references in an expression with bound expressions.
Handles scoped references (Model.Subsystem.var) by splitting on '.' and matching
path through system hierarchy per format spec Section 4.3.

@param expr - Expression to substitute into
@param bindings - Variable name to expression mappings
@returns New expression with substitutions applied (immutable)
/

---

### substituteInEquations

**File:** `packages/esm-format/src/edit.ts:245`

```typescript
export function substituteInEquations(
```

Apply substitutions to all equations in a model
@param model Model to apply substitutions to
@param bindings Variable name to expression mappings
@returns New model with substitutions applied
/

---

### substituteInModel

**File:** `packages/esm-format/src/substitute.ts:57`

```typescript
export function substituteInModel(model: Model, bindings: Record<string, Expr>): Model {
```

Apply substitution across all equations in a model.
Returns a new model with substitutions applied (immutable).

@param model - Model to substitute into
@param bindings - Variable name to expression mappings
@returns New model with substitutions applied
/

---

### substituteInReactionSystem

**File:** `packages/esm-format/src/substitute.ts:104`

```typescript
export function substituteInReactionSystem(
```

Apply substitution across all rate expressions in a reaction system.
Returns a new reaction system with substitutions applied (immutable).

@param system - ReactionSystem to substitute into
@param bindings - Variable name to expression mappings
@returns New reaction system with substitutions applied
/

---

### substrateMatrix

**File:** `packages/esm-format/src/reactions.ts:280`

```typescript
export function substrateMatrix(system: ReactionSystem): number[][] {
```

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

**File:** `packages/esm-format/src/pretty-print.ts:321`

```typescript
export function toAscii(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
```

Format an expression as plain ASCII text
/

---

### toJuliaCode

**File:** `packages/esm-format/src/codegen.ts:18`

```typescript
export function toJuliaCode(file: EsmFile): string {
```

Generate a self-contained Julia script from an ESM file
@param file ESM file to generate Julia code for
@returns Julia script as a string
/

---

### toLatex

**File:** `packages/esm-format/src/pretty-print.ts:281`

```typescript
export function toLatex(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
```

Format an expression as LaTeX mathematical notation
/

---

### toPythonCode

**File:** `packages/esm-format/src/codegen.ts:108`

```typescript
export function toPythonCode(file: EsmFile): string {
```

Generate a self-contained Python script from an ESM file
@param file ESM file to generate Python code for
@returns Python script as a string
/

---

### toUnicode

**File:** `packages/esm-format/src/pretty-print.ts:241`

```typescript
export function toUnicode(expr: Expr | Equation | Model | ReactionSystem | EsmFile): string {
```

Format an expression as Unicode mathematical notation
/

---

### validate

**File:** `packages/esm-format/src/validate.ts:576`

```typescript
export function validate(data: string | object): ValidationResult {
```

Validate ESM data and return structured validation result.

@param data - ESM data as JSON string or object
@returns ValidationResult with validation status and errors
/

---

### validateSchema

**File:** `packages/esm-format/src/parse.ts:77`

```typescript
export function validateSchema(data: unknown): SchemaError[] {
```

Validate data against the ESM schema
/

---

### validateUnits

**File:** `packages/esm-format/src/units.ts:408`

```typescript
export function validateUnits(file: EsmFile): UnitWarning[] {
```

Validate dimensional consistency of all equations in an ESM file
@param file ESM file to validate
@returns Array of unit warnings
/

---

## Types

### AffectEquation

**File:** `packages/esm-format/src/generated.ts:351`

```typescript
export interface AffectEquation {
```

An affect equation in an event: lhs is the target variable (string), rhs is an expression.
/

---

### AstStore

**File:** `packages/esm-editor/src/primitives/ast-store.ts:39`

```typescript
export interface AstStore {
```

AST Store interface providing centralized ESM file management
/

---

### AstStoreConfig

**File:** `packages/esm-editor/src/primitives/ast-store.ts:27`

```typescript
export interface AstStoreConfig {
```

Configuration for the AST store
/

---

### BoundaryCondition

**File:** `packages/esm-format/src/generated.ts:744`

```typescript
export interface BoundaryCondition {
```

Boundary condition for one or more dimensions.
/

---

### Change

**File:** `packages/esm-format/src/interactive-editor/index.ts:73`

```typescript
export interface Change {
```

---

### Command

**File:** `packages/esm-format/src/interactive-editor/index.ts:56`

```typescript
export interface Command {
```

---

### CommandResult

**File:** `packages/esm-format/src/interactive-editor/index.ts:67`

```typescript
export interface CommandResult {
```

---

### CommonSubexpression

**File:** `packages/esm-format/src/analysis/types.ts:69`

```typescript
export interface CommonSubexpression {
```

---

### ComplexityMetrics

**File:** `packages/esm-format/src/analysis/types.ts:51`

```typescript
export interface ComplexityMetrics {
```

---

### ComponentGraph

**File:** `packages/esm-format/src/graph.ts:53`

```typescript
export interface ComponentGraph {
```

---

### ComponentNode

**File:** `packages/esm-format/src/graph.ts:12`

```typescript
export interface ComponentNode {
```

---

### ConnectorEquation

**File:** `packages/esm-format/src/generated.ts:626`

```typescript
export interface ConnectorEquation {
```

A single equation in a ConnectorSystem linking two coupled systems.
/

---

### ContinuousEvent

**File:** `packages/esm-format/src/generated.ts:391`

```typescript
export interface ContinuousEvent {
```

Fires when a condition expression crosses zero (root-finding). Maps to MTK SymbolicContinuousCallback.
/

---

### CoordinateTransform

**File:** `packages/esm-format/src/generated.ts:736`

```typescript
export interface CoordinateTransform {
```

---

### CouplingCallback

**File:** `packages/esm-format/src/generated.ts:681`

```typescript
export interface CouplingCallback {
```

Register a callback for simulation events.
/

---

### CouplingCouple2

**File:** `packages/esm-format/src/generated.ts:601`

```typescript
export interface CouplingCouple2 {
```

Bi-directional coupling via coupletype dispatch.
/

---

### CouplingEdge

**File:** `packages/esm-format/src/graph.ts:35`

```typescript
export interface CouplingEdge {
```

---

### CouplingOperatorApply

**File:** `packages/esm-format/src/generated.ts:670`

```typescript
export interface CouplingOperatorApply {
```

Register an Operator to run during simulation.
/

---

### CouplingOperatorCompose

**File:** `packages/esm-format/src/generated.ts:581`

```typescript
export interface CouplingOperatorCompose {
```

Match LHS time derivatives and add RHS terms together.
/

---

### CouplingVariableMap

**File:** `packages/esm-format/src/generated.ts:647`

```typescript
export interface CouplingVariableMap {
```

Replace a parameter in one system with a variable from another.
/

---

### DataLoader

**File:** `packages/esm-format/src/generated.ts:509`

```typescript
export interface DataLoader {
```

An external data source registration. Runtime-specific; registered by type and loader_id.
/

---

### DataLoaderProvides

**File:** `packages/esm-format/src/generated.ts:549`

```typescript
export interface DataLoaderProvides {
```

A variable provided by a data loader.
/

---

### DemoPageConfig

**File:** `packages/esm-format/src/demo/demo-pages.ts:8`

```typescript
export interface DemoPageConfig {
```

---

### DependencyEdge

**File:** `packages/esm-format/src/graph.ts:87`

```typescript
export interface DependencyEdge {
```

---

### DependencyGraph

**File:** `packages/esm-format/src/analysis/types.ts:41`

```typescript
export interface DependencyGraph extends Graph<DependencyNode, DependencyRelation> {
```

---

### DependencyNode

**File:** `packages/esm-format/src/analysis/types.ts:11`

```typescript
export interface DependencyNode {
```

---

### DependencyRelation

**File:** `packages/esm-format/src/analysis/types.ts:27`

```typescript
export interface DependencyRelation {
```

---

### DerivativeResult

**File:** `packages/esm-format/src/analysis/types.ts:125`

```typescript
export interface DerivativeResult {
```

---

### DimensionalRep

**File:** `packages/esm-format/src/units.ts:14`

```typescript
export interface DimensionalRep {
```

Canonical dimensional representation
Maps base dimensions to their powers
/

---

### Domain

**File:** `packages/esm-format/src/generated.ts:695`

```typescript
export interface Domain {
```

Spatiotemporal domain specification (DomainInfo).
/

---

### DragState

**File:** `packages/esm-format/src/interactive-editor/index.ts:41`

```typescript
export interface DragState {
```

---

### ESMError

**File:** `packages/esm-format/src/error-handling.ts:101`

```typescript
export interface ESMError {
```

---

### ESMFormat2

**File:** `packages/esm-format/src/generated.ts:170`

```typescript
export interface ESMFormat2 {
```

---

### EditorState

**File:** `packages/esm-format/src/interactive-editor/index.ts:24`

```typescript
export interface EditorState {
```

---

### Equation

**File:** `packages/esm-format/src/generated.ts:343`

```typescript
export interface Equation {
```

An equation: lhs = rhs (or lhs ~ rhs in MTK notation).
/

---

### ErrorContext

**File:** `packages/esm-format/src/error-handling.ts:80`

```typescript
export interface ErrorContext {
```

---

### ErrorLoggerConfig

**File:** `packages/esm-format/src/error-handling.ts:621`

```typescript
export interface ErrorLoggerConfig {
```

---

### EsmCouplingGraphProps

**File:** `packages/esm-format/src/web-components.ts:84`

```typescript
export interface EsmCouplingGraphProps {
```

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

**File:** `packages/esm-editor/src/web-components.ts:128`

```typescript
export interface EsmCouplingGraphProps {
```

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

**File:** `packages/esm-editor/src/web-components.ts:40`

```typescript
export interface EsmExpressionEditorProps {
```

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

**File:** `packages/esm-format/src/web-components.ts:36`

```typescript
export interface EsmExpressionNodeProps {
```

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

**File:** `packages/esm-editor/src/web-components.ts:82`

```typescript
export interface EsmFileEditorProps {
```

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

**File:** `packages/esm-format/src/web-components.ts:135`

```typescript
export interface EsmFileSummaryProps {
```

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

**File:** `packages/esm-format/src/web-components.ts:59`

```typescript
export interface EsmModelEditorProps {
```

Web component wrapper for ModelEditor

Usage:
<esm-model-editor
model='{"variables": {...}, "equations": [...]}'
allow-editing="true">
</esm-model-editor>
/

---

### EsmModelEditorProps

**File:** `packages/esm-editor/src/web-components.ts:61`

```typescript
export interface EsmModelEditorProps {
```

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

**File:** `packages/esm-editor/src/web-components.ts:105`

```typescript
export interface EsmReactionEditorProps {
```

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

**File:** `packages/esm-format/src/web-components.ts:157`

```typescript
export interface EsmSimulationControlsProps {
```

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

**File:** `packages/esm-format/src/web-components.ts:108`

```typescript
export interface EsmValidationPanelProps {
```

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

**File:** `packages/esm-format/src/interactive-editor/ModelExportUtils.ts:19`

```typescript
export interface ExportOptions {
```

Export options for different formats
/

---

### ExpressionLocation

**File:** `packages/esm-format/src/analysis/types.ts:81`

```typescript
export interface ExpressionLocation {
```

---

### ExpressionNode

**File:** `packages/esm-format/src/generated.ts:285`

```typescript
export interface ExpressionNode {
```

An operation in the expression AST.
/

---

### ExpressionPattern

**File:** `packages/esm-format/src/analysis/types.ts:91`

```typescript
export interface ExpressionPattern {
```

---

### FixSuggestion

**File:** `packages/esm-format/src/error-handling.ts:92`

```typescript
export interface FixSuggestion {
```

---

### FunctionalAffect

**File:** `packages/esm-format/src/generated.ts:364`

```typescript
export interface FunctionalAffect {
```

Registered functional affect handler (alternative to symbolic affects).
/

---

### Graph

**File:** `packages/esm-format/src/graph.ts:61`

```typescript
export interface Graph<N, E> {
```

---

### GraphExportOptions

**File:** `packages/esm-format/src/analysis/types.ts:161`

```typescript
export interface GraphExportOptions {
```

---

### HistoryEntry

**File:** `packages/esm-editor/src/primitives/history.ts:26`

```typescript
export interface HistoryEntry {
```

History entry representing a state snapshot
/

---

### HoverState

**File:** `packages/esm-format/src/interactive-editor/index.ts:79`

```typescript
export interface HoverState {
```

---

### LayoutAlgorithm

**File:** `packages/esm-format/src/analysis/types.ts:140`

```typescript
export interface LayoutAlgorithm {
```

---

### LayoutResult

**File:** `packages/esm-format/src/analysis/types.ts:148`

```typescript
export interface LayoutResult<N> {
```

---

### MatchResult

**File:** `packages/esm-format/src/analysis/types.ts:101`

```typescript
export interface MatchResult {
```

---

### Metadata

**File:** `packages/esm-format/src/generated.ts:210`

```typescript
export interface Metadata {
```

Authorship, provenance, and description.
/

---

### Model

**File:** `packages/esm-format/src/generated.ts:241`

```typescript
export interface Model {
```

An ODE system — a fully specified set of time-dependent equations.
/

---

### ModelVariable

**File:** `packages/esm-format/src/generated.ts:269`

```typescript
export interface ModelVariable {
```

A variable in an ODE model.
/

---

### Operator

**File:** `packages/esm-format/src/generated.ts:556`

```typescript
export interface Operator {
```

A registered runtime operator (e.g., dry deposition, wet scavenging).
/

---

### Optimization

**File:** `packages/esm-format/src/analysis/types.ts:111`

```typescript
export interface Optimization {
```

---

### Parameter

**File:** `packages/esm-format/src/generated.ts:471`

```typescript
export interface Parameter {
```

A parameter in a reaction system.
/

---

### Reaction

**File:** `packages/esm-format/src/generated.ts:479`

```typescript
export interface Reaction {
```

A single reaction in a reaction system.
/

---

### ReactionSystem

**File:** `packages/esm-format/src/generated.ts:423`

```typescript
export interface ReactionSystem {
```

A reaction network — declarative representation of chemical or biological reactions.
/

---

### Reference

**File:** `packages/esm-format/src/generated.ts:232`

```typescript
export interface Reference {
```

Academic citation or data source reference.
/

---

### SchemaError

**File:** `packages/esm-format/src/parse.ts:22`

```typescript
export interface SchemaError {
```

Schema validation error with JSON Pointer path
/

---

### Solver

**File:** `packages/esm-format/src/generated.ts:777`

```typescript
export interface Solver {
```

Solver strategy for time integration.
/

---

### SpatialDimension

**File:** `packages/esm-format/src/generated.ts:730`

```typescript
export interface SpatialDimension {
```

Specification of a single spatial dimension.
/

---

### Species

**File:** `packages/esm-format/src/generated.ts:463`

```typescript
export interface Species {
```

A reactive species in a reaction system.
/

---

### StoichiometryEntry

**File:** `packages/esm-format/src/generated.ts:502`

```typescript
export interface StoichiometryEntry {
```

A species with its stoichiometric coefficient in a reaction.
/

---

### StructuralError

**File:** `packages/esm-format/src/validate.ts:49`

```typescript
export interface StructuralError {
```

Structural error type matching the format specification
/

---

### TooltipData

**File:** `packages/esm-format/src/interactive-editor/index.ts:86`

```typescript
export interface TooltipData {
```

---

### UndoHistory

**File:** `packages/esm-editor/src/primitives/history.ts:38`

```typescript
export interface UndoHistory {
```

Undo/redo history management interface
/

---

### UndoHistoryConfig

**File:** `packages/esm-editor/src/primitives/history.ts:14`

```typescript
export interface UndoHistoryConfig {
```

Configuration for undo history behavior
/

---

### UndoRedoState

**File:** `packages/esm-format/src/interactive-editor/index.ts:48`

```typescript
export interface UndoRedoState {
```

---

### UnitResult

**File:** `packages/esm-format/src/units.ts:37`

```typescript
export interface UnitResult {
```

Result of dimensional analysis
/

---

### UnitWarning

**File:** `packages/esm-format/src/units.ts:45`

```typescript
export interface UnitWarning {
```

Unit validation warning
/

---

### ValidationError

**File:** `packages/esm-format/src/validate.ts:30`

```typescript
export interface ValidationError {
```

Validation error with structured details
/

---

### ValidationError

**File:** `packages/esm-format/src/interactive-editor/index.ts:32`

```typescript
export interface ValidationError {
```

---

### ValidationResult

**File:** `packages/esm-format/src/validate.ts:40`

```typescript
export interface ValidationResult {
```

Structured validation result
/

---

### VariableNode

**File:** `packages/esm-format/src/graph.ts:75`

```typescript
export interface VariableNode {
```

---

