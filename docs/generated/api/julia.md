# Julia API Reference

Complete API reference for the ESM Format Julia library.

## Functions

### ASCII

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ASCII(...)
```

---

### AffectEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
AffectEquation(...)
```

**Available in other languages:**
- [Python](python.md#affectequation)
- [Typescript](typescript.md#affectequation)

---

### Availability

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Availability(...)
```

---

### Base

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:310`

**Signature:**
```julia
function Base.show(io::IO, ::MIME"text/plain", expr::Expr)
```

**Description:**
Base.show(io::IO, ::MIME"text/plain", expr::Expr)

Unicode display: chemical subscripts via element-aware tokenizer, ∂x/∂t derivatives,
· for multiplication, − for unary minus, scientific notation with Unicode superscripts.

---

### Base

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:319`

**Signature:**
```julia
function Base.show(io::IO, ::MIME"text/latex", expr::Expr)
```

**Description:**
Base.show(io::IO, ::MIME"text/latex", expr::Expr)

LaTeX display: \\frac{}{}, \\partial, \\mathrm{} for species.

---

### Base

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:328`

**Signature:**
```julia
function Base.show(io::IO, ::MIME"text/ascii", expr::Expr)
```

**Description:**
Base.show(io::IO, ::MIME"text/ascii", expr::Expr)

ASCII display: plain ASCII mathematical notation with standard operators (*, /, ^).

---

### Base

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:636`

**Signature:**
```julia
function Base.show(io::IO, equation::Equation)
```

**Description:**
Base.show(io::IO, equation::Equation)

Display equation in Unicode format.

---

### Base

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:647`

**Signature:**
```julia
function Base.show(io::IO, model::Model)
```

**Description:**
Base.show(io::IO, model::Model)

Model display: show(Model) prints equation list per spec Section 6.3.

---

### Base

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:717`

**Signature:**
```julia
function Base.show(io::IO, esm_file::EsmFile)
```

**Description:**
Base.show(io::IO, esm_file::EsmFile)

EsmFile display: show(EsmFile) prints structured summary per spec Section 6.3.

---

### Base

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:766`

**Signature:**
```julia
function Base.show(io::IO, reaction_system::ReactionSystem)
```

**Description:**
Base.show(io::IO, reaction_system::ReactionSystem)

ReactionSystem display: reactions in chemical notation.

---

### Catalyst

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Catalyst(...)
```

---

### Chemical

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Chemical(...)
```

---

### Code

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Code(...)
```

---

### ComponentNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ComponentNode(...)
```

**Available in other languages:**
- [Python](python.md#componentnode)
- [Typescript](typescript.md#componentnode)

---

### Concrete

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Concrete(...)
```

---

### ConditionTrigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ConditionTrigger(...)
```

---

### ContinuousEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ContinuousEvent(...)
```

**Available in other languages:**
- [Python](python.md#continuousevent)
- [Typescript](typescript.md#continuousevent)

---

### Coupled

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Coupled(...)
```

---

### Coupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Coupling(...)
```

---

### CouplingCallback

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
CouplingCallback(...)
```

**Available in other languages:**
- [Typescript](typescript.md#couplingcallback)

---

### CouplingCouple

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
CouplingCouple(...)
```

**Available in other languages:**
- [Python](python.md#couplingcouple)
- [Typescript](typescript.md#couplingcouple)

---

### CouplingEdge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
CouplingEdge(...)
```

**Available in other languages:**
- [Python](python.md#couplingedge)
- [Python](python.md#couplingedge)
- [Typescript](typescript.md#couplingedge)

---

### CouplingEntry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
CouplingEntry(...)
```

---

### CouplingEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
CouplingEvent(...)
```

---

### CouplingOperatorApply

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
CouplingOperatorApply(...)
```

**Available in other languages:**
- [Typescript](typescript.md#couplingoperatorapply)

---

### CouplingOperatorCompose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
CouplingOperatorCompose(...)
```

**Available in other languages:**
- [Typescript](typescript.md#couplingoperatorcompose)

---

### CouplingVariableMap

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
CouplingVariableMap(...)
```

**Available in other languages:**
- [Typescript](typescript.md#couplingvariablemap)

---

### Data

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Data(...)
```

---

### DataLoader

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DataLoader(...)
```

**Available in other languages:**
- [Python](python.md#dataloader)
- [Typescript](typescript.md#dataloader)

---

### DependencyEdge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DependencyEdge(...)
```

**Available in other languages:**
- [Python](python.md#dependencyedge)
- [Typescript](typescript.md#dependencyedge)

---

### DiscreteEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DiscreteEvent(...)
```

**Available in other languages:**
- [Python](python.md#discreteevent)

---

### DiscreteEventTrigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DiscreteEventTrigger(...)
```

---

### Domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Domain(...)
```

**Available in other languages:**
- [Python](python.md#domain)
- [Typescript](typescript.md#domain)

---

### Editing

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Editing(...)
```

---

### Equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Equation(...)
```

**Available in other languages:**
- [Python](python.md#equation)
- [Python](python.md#equation)
- [Typescript](typescript.md#equation)

---

### Equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Equation(...)
```

**Available in other languages:**
- [Python](python.md#equation)
- [Python](python.md#equation)
- [Typescript](typescript.md#equation)

---

### EsmFile

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
EsmFile(...)
```

**Available in other languages:**
- [Python](python.md#esmfile)

---

### Event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Event(...)
```

---

### EventType

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
EventType(...)
```

---

### Expr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Expr(...)
```

---

### Expression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Expression(...)
```

---

### Expression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Expression(...)
```

---

### Expression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Expression(...)
```

---

### FlattenMetadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
FlattenMetadata(...)
```

**Available in other languages:**
- [Python](python.md#flattenmetadata)
- [Typescript](typescript.md#flattenmetadata)

---

### Flattened

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Flattened(...)
```

---

### FlattenedEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
FlattenedEquation(...)
```

**Available in other languages:**
- [Python](python.md#flattenedequation)
- [Typescript](typescript.md#flattenedequation)

---

### FlattenedSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
FlattenedSystem(...)
```

**Available in other languages:**
- [Python](python.md#flattenedsystem)
- [Typescript](typescript.md#flattenedsystem)

---

### FunctionalAffect

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
FunctionalAffect(...)
```

**Available in other languages:**
- [Python](python.md#functionalaffect)
- [Typescript](typescript.md#functionalaffect)

---

### Graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Graph(...)
```

**Available in other languages:**
- [Python](python.md#graph)
- [Typescript](typescript.md#graph)

---

### Graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Graph(...)
```

**Available in other languages:**
- [Python](python.md#graph)
- [Typescript](typescript.md#graph)

---

### Interface

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Interface(...)
```

---

### JSON

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
JSON(...)
```

---

### Legacy

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Legacy(...)
```

---

### MTK

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
MTK(...)
```

---

### Metadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Metadata(...)
```

**Available in other languages:**
- [Python](python.md#metadata)
- [Typescript](typescript.md#metadata)

---

### MockCatalystSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
MockCatalystSystem(...)
```

---

### MockCoupledSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
MockCoupledSystem(...)
```

---

### MockMTKSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
MockMTKSystem(...)
```

---

### Model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Model(...)
```

**Available in other languages:**
- [Python](python.md#model)
- [Typescript](typescript.md#model)

---

### Model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Model(...)
```

**Available in other languages:**
- [Python](python.md#model)
- [Typescript](typescript.md#model)

---

### ModelVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ModelVariable(...)
```

**Available in other languages:**
- [Python](python.md#modelvariable)
- [Typescript](typescript.md#modelvariable)

---

### ModelVariableType

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ModelVariableType(...)
```

---

### NumExpr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
NumExpr(...)
```

---

### ODE

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ODE(...)
```

---

### ObservedVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ObservedVariable(...)
```

---

### OpExpr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
OpExpr(...)
```

---

### Operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Operator(...)
```

**Available in other languages:**
- [Python](python.md#operator)
- [Typescript](typescript.md#operator)

---

### Parameter

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Parameter(...)
```

**Available in other languages:**
- [Python](python.md#parameter)
- [Typescript](typescript.md#parameter)

---

### ParameterVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ParameterVariable(...)
```

---

### ParseError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ParseError(...)
```

---

### PeriodicTrigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
PeriodicTrigger(...)
```

---

### PresetTimesTrigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
PresetTimesTrigger(...)
```

---

### Qualified

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Qualified(...)
```

---

### QualifiedReferenceError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
QualifiedReferenceError(...)
```

---

### Reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Reaction(...)
```

**Available in other languages:**
- [Python](python.md#reaction)
- [Typescript](typescript.md#reaction)

---

### Reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Reaction(...)
```

**Available in other languages:**
- [Python](python.md#reaction)
- [Typescript](typescript.md#reaction)

---

### Reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:898`

**Signature:**
```julia
function Reaction(reactants::Dict{String,Int}, products::Dict{String,Int}, rate::Expr; reversible=false)
```

**Description:**
Reaction(reactants::Dict{String,Int}, products::Dict{String,Int}, rate::Expr; reversible=false) -> Reaction

Legacy constructor for backward compatibility. Creates a reaction with auto-generated ID.

**Available in other languages:**
- [Python](python.md#reaction)
- [Typescript](typescript.md#reaction)

---

### ReactionSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ReactionSystem(...)
```

**Available in other languages:**
- [Python](python.md#reactionsystem)
- [Typescript](typescript.md#reactionsystem)

---

### Reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Reference(...)
```

**Available in other languages:**
- [Python](python.md#reference)
- [Typescript](typescript.md#reference)

---

### ReferenceResolution

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ReferenceResolution(...)
```

---

### SchemaError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
SchemaError(...)
```

**Available in other languages:**
- [Typescript](typescript.md#schemaerror)

---

### SchemaValidationError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
SchemaValidationError(...)
```

**Available in other languages:**
- [Python](python.md#schemavalidationerror)

---

### Section

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Section(...)
```

---

### Section

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Section(...)
```

---

### Species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Species(...)
```

**Available in other languages:**
- [Python](python.md#species)
- [Typescript](typescript.md#species)

---

### StateVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
StateVariable(...)
```

---

### Structural

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Structural(...)
```

---

### StructuralError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
StructuralError(...)
```

**Available in other languages:**
- [Typescript](typescript.md#structuralerror)

---

### Subsystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Subsystem(...)
```

---

### SubsystemRefError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
SubsystemRefError(...)
```

**Available in other languages:**
- [Python](python.md#subsystemreferror)

---

### System

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
System(...)
```

---

### UnboundVariableError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
UnboundVariableError(...)
```

---

### Unit

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Unit(...)
```

---

### ValidationResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ValidationResult(...)
```

**Available in other languages:**
- [Python](python.md#validationresult)
- [Typescript](typescript.md#validationresult)

---

### VarExpr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
VarExpr(...)
```

---

### VariableNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
VariableNode(...)
```

**Available in other languages:**
- [Python](python.md#variablenode)
- [Typescript](typescript.md#variablenode)

---

### _canonical_ref

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:870`

**Signature:**
```julia
function _canonical_ref(ref::String, base_path::String)::String
```

**Description:**
_canonical_ref(ref::String, base_path::String) -> String

Produce a canonical key for a reference, used for cycle detection.
URLs are returned as-is; local paths are resolved to absolute paths.

---

### _load_local_ref

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:883`

**Signature:**
```julia
function _load_local_ref(ref::String, base_path::String, visited::Set{String})::EsmFile
```

**Description:**
_load_local_ref(ref::String, base_path::String, visited::Set{String}) -> EsmFile

Load a locally referenced ESM file.

---

### _load_ref

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:840`

**Signature:**
```julia
function _load_ref(ref::String, base_path::String, visited::Set{String})::EsmFile
```

**Description:**
_load_ref(ref::String, base_path::String, visited::Set{String}) -> EsmFile

Load a referenced ESM file from a local path or URL, with circular reference detection.

# Arguments
- `ref::String`: the reference string (local path or URL)
- `base_path::String`: directory for resolving relative paths
- `visited::Set{String}`: set of already-visited references for cycle detection

---

### _load_remote_ref

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:908`

**Signature:**
```julia
function _load_remote_ref(ref::String)::EsmFile
```

**Description:**
_load_remote_ref(ref::String) -> EsmFile

Load a remotely referenced ESM file from a URL.
Uses the Downloads stdlib to fetch the content.

---

### _resolve_model_refs!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:809`

**Signature:**
```julia
function _resolve_model_refs!(models_dict::Dict{String,Model}, name::String,
```

**Description:**
_resolve_model_refs!(models_dict, name, model, base_path, visited)

Recursively resolve subsystem references within a Model's subsystems.

---

### _resolve_reaction_system_refs!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:822`

**Signature:**
```julia
function _resolve_reaction_system_refs!(rsys_dict::Dict{String,ReactionSystem}, name::String,
```

**Description:**
_resolve_reaction_system_refs!(rsys_dict, name, rsys, base_path, visited)

Recursively resolve subsystem references within a ReactionSystem's subsystems.

---

### _resolve_refs_in_file!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:788`

**Signature:**
```julia
function _resolve_refs_in_file!(file::EsmFile, base_path::String, visited::Set{String})
```

**Description:**
_resolve_refs_in_file!(file::EsmFile, base_path::String, visited::Set{String})

Internal recursive resolver for subsystem references in an EsmFile.

---

### add_continuous_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
add_continuous_event(...)
```

---

### add_continuous_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:322`

**Signature:**
```julia
function add_continuous_event(model::Model, event::ContinuousEvent)::Model
```

**Description:**
add_continuous_event(model::Model, event::ContinuousEvent) -> Model

Add a continuous event to a model.

---

### add_coupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
add_coupling(...)
```

---

### add_coupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:390`

**Signature:**
```julia
function add_coupling(file::EsmFile, entry::CouplingEntry)::EsmFile
```

**Description:**
add_coupling(file::EsmFile, entry::CouplingEntry) -> EsmFile

Add a coupling entry to an ESM file.

---

### add_discrete_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
add_discrete_event(...)
```

---

### add_discrete_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:340`

**Signature:**
```julia
function add_discrete_event(model::Model, event::DiscreteEvent)::Model
```

**Description:**
add_discrete_event(model::Model, event::DiscreteEvent) -> Model

Add a discrete event to a model.

---

### add_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
add_equation(...)
```

---

### add_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:128`

**Signature:**
```julia
function add_equation(model::Model, equation::Equation)::Model
```

**Description:**
add_equation(model::Model, equation::Equation) -> Model

Add a new equation to a model.

Appends the equation to the end of the equations list.

---

### add_error!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:167`

**Signature:**
```julia
function add_error!(collector::ErrorCollector, error::ESMError)
```

**Description:**
add_error!(collector, error)

Add an error to the collection.

---

### add_reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
add_reaction(...)
```

---

### add_reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:211`

**Signature:**
```julia
function add_reaction(system::ReactionSystem, reaction::Reaction)::ReactionSystem
```

**Description:**
add_reaction(system::ReactionSystem, reaction::Reaction) -> ReactionSystem

Add a new reaction to a reaction system.

---

### add_species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
add_species(...)
```

---

### add_species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:257`

**Signature:**
```julia
function add_species(system::ReactionSystem, name::String, species::Species)::ReactionSystem
```

**Description:**
add_species(system::ReactionSystem, name::String, species::Species) -> ReactionSystem

Add a new species to a reaction system.

---

### add_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
add_variable(...)
```

---

### add_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:18`

**Signature:**
```julia
function add_variable(model::Model, name::String, variable::ModelVariable)::Model
```

**Description:**
add_variable(model::Model, name::String, variable::ModelVariable) -> Model

Add a new variable to a model.

Creates a new model with the additional variable. Warns if variable already exists.

---

### adjacency

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
adjacency(...)
```

---

### adjacency

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:69`

**Signature:**
```julia
function adjacency(graph::Graph{N, E}, node::N) where {N, E}
```

**Description:**
Get all adjacent nodes (both predecessors and successors).

---

### aliases

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
aliases(...)
```

---

### analysis

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
analysis(...)
```

---

### analyze_coupling_issues

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:571`

**Signature:**
```julia
function analyze_coupling_issues(esm_file, error_collector)
```

**Description:**
analyze_coupling_issues(esm_file, error_collector)

Analyze coupling-related issues and provide debugging info.

---

### and

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
and(...)
```

---

### apply_additive_transform

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:621`

**Signature:**
```julia
function apply_additive_transform(coupled_system, from_resolution, to_resolution, constraint)
```

**Description:**
apply_additive_transform(coupled_system, from_resolution, to_resolution, constraint)

Create an additive coupling between two variables.

---

### apply_advanced_mtk_features

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:1133`

**Signature:**
```julia
function apply_advanced_mtk_features(sys, metadata::Dict)
```

**Description:**
apply_advanced_mtk_features(sys, metadata::Dict) -> ODESystem

Apply advanced MTK features like algebraic reduction and optimization hints.

---

### apply_connector_transform

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:413`

**Signature:**
```julia
function apply_connector_transform(system::MockMTKSystem, constraint)
```

**Description:**
apply_connector_transform(system, constraint)

Apply a connector transform to modify equations in the target system.

---

### apply_conversion_factor_transform

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:669`

**Signature:**
```julia
function apply_conversion_factor_transform(coupled_system, from_resolution, to_resolution, constraint)
```

**Description:**
apply_conversion_factor_transform(coupled_system, from_resolution, to_resolution, constraint)

Create a conversion factor coupling with scaling between two variables.

---

### apply_identity_transform

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:601`

**Signature:**
```julia
function apply_identity_transform(coupled_system, from_resolution, to_resolution, constraint)
```

**Description:**
apply_identity_transform(coupled_system, from_resolution, to_resolution, constraint)

Create an identity mapping constraint between two variables.

---

### apply_multiplicative_transform

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:645`

**Signature:**
```julia
function apply_multiplicative_transform(coupled_system, from_resolution, to_resolution, constraint)
```

**Description:**
apply_multiplicative_transform(coupled_system, from_resolution, to_resolution, constraint)

Create a multiplicative coupling between two variables.

---

### apply_param_to_var_transform

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:574`

**Signature:**
```julia
function apply_param_to_var_transform(coupled_system, from_resolution, to_resolution, constraint)
```

**Description:**
apply_param_to_var_transform(coupled_system, from_resolution, to_resolution, constraint)

Promote a parameter to a shared state variable between systems.

---

### apply_translations

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:190`

**Signature:**
```julia
function apply_translations(vars::Vector{String}, translate)
```

**Description:**
apply_translations(vars::Vector{String}, translate)

Apply translation mappings to variable names.

---

### apply_variable_transform

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:518`

**Signature:**
```julia
function apply_variable_transform(coupled_system, from_resolution, to_resolution, coupling)
```

**Description:**
apply_variable_transform(coupled_system, from_resolution, to_resolution, coupling)

Apply the specified transform operation between variables.

---

### check_catalyst_availability

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
check_catalyst_availability(...)
```

---

### check_catalyst_availability

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/availability.jl:52`

**Signature:**
```julia
function check_catalyst_availability()
```

**Description:**
check_catalyst_availability() -> Bool

Check if Catalyst and Symbolics are available.
Uses lazy loading to avoid precompilation issues.

---

### check_mtk_availability

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
check_mtk_availability(...)
```

---

### check_mtk_availability

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/availability.jl:25`

**Signature:**
```julia
function check_mtk_availability()
```

**Description:**
check_mtk_availability() -> Bool

Check if ModelingToolkit and Symbolics are available.
Uses lazy loading to avoid precompilation issues.

---

### check_mtk_catalyst_availability

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
check_mtk_catalyst_availability(...)
```

---

### check_mtk_catalyst_availability

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/availability.jl:79`

**Signature:**
```julia
function check_mtk_catalyst_availability()
```

**Description:**
check_mtk_catalyst_availability() -> Bool

Check if both ModelingToolkit and Catalyst are available.
Uses lazy loading to avoid precompilation issues.

---

### checking

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
checking(...)
```

---

### coerce_affect_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:322`

**Signature:**
```julia
function coerce_affect_equation(data::Any)::AffectEquation
```

**Description:**
coerce_affect_equation(data::Any) -> AffectEquation

Coerce JSON data into AffectEquation type.

---

### coerce_callback

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:598`

**Signature:**
```julia
function coerce_callback(data::AbstractDict)::CouplingCallback
```

**Description:**
coerce_callback(data::AbstractDict) -> CouplingCallback

Parse callback coupling entry.

---

### coerce_continuous_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:306`

**Signature:**
```julia
function coerce_continuous_event(data::Any)::ContinuousEvent
```

**Description:**
coerce_continuous_event(data::Any) -> ContinuousEvent

Coerce JSON data specifically into ContinuousEvent.

---

### coerce_couple

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:521`

**Signature:**
```julia
function coerce_couple(data::AbstractDict)::CouplingCouple
```

**Description:**
coerce_couple(data::AbstractDict) -> CouplingCouple

Parse couple coupling entry.

---

### coerce_coupling_entry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
coerce_coupling_entry(...)
```

---

### coerce_coupling_entry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:467`

**Signature:**
```julia
function coerce_coupling_entry(data::Any)::CouplingEntry
```

**Description:**
coerce_coupling_entry(data::Any) -> CouplingEntry

Coerce JSON data into concrete CouplingEntry subtype based on the 'type' field.

---

### coerce_data_loader

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:422`

**Signature:**
```julia
function coerce_data_loader(data::Any)::DataLoader
```

**Description:**
coerce_data_loader(data::Any) -> DataLoader

Coerce JSON data into DataLoader type.

---

### coerce_discrete_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:290`

**Signature:**
```julia
function coerce_discrete_event(data::Any)::DiscreteEvent
```

**Description:**
coerce_discrete_event(data::Any) -> DiscreteEvent

Coerce JSON data specifically into DiscreteEvent.

---

### coerce_domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:677`

**Signature:**
```julia
function coerce_domain(data::Any)::Domain
```

**Description:**
coerce_domain(data::Any) -> Domain

Coerce JSON data into Domain type.

---

### coerce_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:255`

**Signature:**
```julia
function coerce_equation(data::Any)::Equation
```

**Description:**
coerce_equation(data::Any) -> Equation

Coerce JSON data into Equation type.

---

### coerce_esm_file

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:99`

**Signature:**
```julia
function coerce_esm_file(data::Any)::EsmFile
```

**Description:**
coerce_esm_file(data::Any) -> EsmFile

Coerce raw JSON data into properly typed EsmFile with custom union type handling.

---

### coerce_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:267`

**Signature:**
```julia
function coerce_event(data::Any)::EventType
```

**Description:**
coerce_event(data::Any) -> EventType

Coerce JSON data into EventType (ContinuousEvent or DiscreteEvent).

---

### coerce_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:618`

**Signature:**
```julia
function coerce_event(data::AbstractDict)::CouplingEvent
```

**Description:**
coerce_event(data::AbstractDict) -> CouplingEvent

Parse event coupling entry.

---

### coerce_functional_affect

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:333`

**Signature:**
```julia
function coerce_functional_affect(data::Any)::FunctionalAffect
```

**Description:**
coerce_functional_affect(data::Any) -> FunctionalAffect

Coerce JSON data into FunctionalAffect type.

---

### coerce_interface

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:689`

**Signature:**
```julia
function coerce_interface(data::Any)::Interface
```

**Description:**
coerce_interface(data::Any) -> Interface

Coerce JSON data into Interface type.

---

### coerce_metadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:162`

**Signature:**
```julia
function coerce_metadata(data::Any)::Metadata
```

**Description:**
coerce_metadata(data::Any) -> Metadata

Coerce JSON data into Metadata type.

---

### coerce_model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:201`

**Signature:**
```julia
function coerce_model(data::Any)::Model
```

**Description:**
coerce_model(data::Any) -> Model

Coerce JSON data into Model type.

---

### coerce_model_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:238`

**Signature:**
```julia
function coerce_model_variable(data::Any)::ModelVariable
```

**Description:**
coerce_model_variable(data::Any) -> ModelVariable

Coerce JSON data into ModelVariable type.

---

### coerce_operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:446`

**Signature:**
```julia
function coerce_operator(data::Any)::Operator
```

**Description:**
coerce_operator(data::Any) -> Operator

Coerce JSON data into Operator type.

---

### coerce_operator_apply

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:582`

**Signature:**
```julia
function coerce_operator_apply(data::AbstractDict)::CouplingOperatorApply
```

**Description:**
coerce_operator_apply(data::AbstractDict) -> CouplingOperatorApply

Parse operator_apply coupling entry.

---

### coerce_operator_compose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:496`

**Signature:**
```julia
function coerce_operator_compose(data::AbstractDict)::CouplingOperatorCompose
```

**Description:**
coerce_operator_compose(data::AbstractDict) -> CouplingOperatorCompose

Parse operator_compose coupling entry.

---

### coerce_parameter

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:409`

**Signature:**
```julia
function coerce_parameter(name::String, data::Any)::Parameter
```

**Description:**
coerce_parameter(name::String, data::Any) -> Parameter

Coerce JSON data into Parameter type with explicit name.

---

### coerce_reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:375`

**Signature:**
```julia
function coerce_reaction(data::Any)::Reaction
```

**Description:**
coerce_reaction(data::Any) -> Reaction

Coerce JSON data into Reaction type.

---

### coerce_reaction_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:345`

**Signature:**
```julia
function coerce_reaction_system(data::Any)::ReactionSystem
```

**Description:**
coerce_reaction_system(data::Any) -> ReactionSystem

Coerce JSON data into ReactionSystem type.

---

### coerce_reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:187`

**Signature:**
```julia
function coerce_reference(data::Any)::Reference
```

**Description:**
coerce_reference(data::Any) -> Reference

Coerce JSON data into Reference type.

---

### coerce_species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:362`

**Signature:**
```julia
function coerce_species(name::String, data::Any)::Species
```

**Description:**
coerce_species(name::String, data::Any) -> Species

Coerce JSON data into Species type with explicit name.

---

### coerce_variable_map

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:549`

**Signature:**
```julia
function coerce_variable_map(data::AbstractDict)::CouplingVariableMap
```

**Description:**
coerce_variable_map(data::AbstractDict) -> CouplingVariableMap

Parse variable_map coupling entry.

---

### compatibility

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
compatibility(...)
```

---

### component

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
component(...)
```

---

### component_graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
component_graph(...)
```

**Available in other languages:**
- [Typescript](typescript.md#component_graph)

---

### component_graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:133`

**Signature:**
```julia
function component_graph(file::EsmFile)::Graph{ComponentNode, CouplingEdge}
```

**Description:**
component_graph(file::EsmFile) -> Graph{ComponentNode, CouplingEdge}

Generate component-level graph showing systems and their couplings.

Creates nodes for each model, reaction system, data loader, and operator.
Creates edges based on coupling entries with appropriate types and labels.

# Arguments
- `file::EsmFile`: Input ESM file

# Returns
- `Graph{ComponentNode, CouplingEdge}`: Component graph with coupling relationships

# Example
```julia
graph = component_graph(file)
# Access nodes and edges
for node in graph.nodes
    println("Component: \$(node.name) (\$(node.type))")
end
for edge in graph.edges
    println("Coupling: \$(edge.from) --[\$(edge.label)]--> \$(edge.to)")
end
```

**Available in other languages:**
- [Typescript](typescript.md#component_graph)

---

### compose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
compose(...)
```

**Available in other languages:**
- [Typescript](typescript.md#compose)

---

### compose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:437`

**Signature:**
```julia
function compose(file::EsmFile, system_a::String, system_b::String)::EsmFile
```

**Description:**
compose(file::EsmFile, system_a::String, system_b::String) -> EsmFile

Convenience function to create an operator_compose coupling entry.

**Available in other languages:**
- [Typescript](typescript.md#compose)

---

### compose_systems

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:224`

**Signature:**
```julia
function compose_systems(system1, system2, matched_vars, translate, composed_name)
```

**Description:**
compose_systems(system1, system2, matched_vars, translate, composed_name)

Actually compose two systems by combining equations for matched variables.
This implements the core operator_compose algorithm:
1. For each matched variable, combine RHS terms by addition
2. Preserve unmatched equations from both systems
3. Create a unified system with merged variables, parameters, and equations

---

### contains

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
contains(...)
```

**Available in other languages:**
- [Typescript](typescript.md#contains)

---

### contains

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/expression.jl:119`

**Signature:**
```julia
function contains(expr::NumExpr, var::String)::Bool
```

**Description:**
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

**Available in other languages:**
- [Typescript](typescript.md#contains)

---

### conversion

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
conversion(...)
```

---

### conversion

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
conversion(...)
```

---

### conversion

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
conversion(...)
```

---

### convert_operator_enhanced

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:951`

**Signature:**
```julia
function convert_operator_enhanced(op::String, args::Vector, wrt::Union{String,Nothing}, advanced_features::Bool)
```

**Description:**
convert_operator_enhanced(op::String, args::Vector, wrt::Union{String,Nothing}, advanced_features::Bool) -> Any

Enhanced operator conversion supporting more functions and advanced features.

---

### couple

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:334`

**Signature:**
```julia
function couple(coupled_system::MockCoupledSystem, coupling::CouplingCouple)
```

**Description:**
couple(coupled_system::MockCoupledSystem, coupling::CouplingCouple)

Implement bi-directional coupling via connector equations:
1. Read connector equations from the coupling specification
2. Resolve scoped references in connector equations
3. Apply transform operations (additive/multiplicative/replacement)

---

### coupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
coupling(...)
```

---

### create_connector_constraint

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:364`

**Signature:**
```julia
function create_connector_constraint(coupled_system, from_ref, to_ref, transform, systems)
```

**Description:**
create_connector_constraint(coupled_system, from_ref, to_ref, transform, systems)

Create an actual coupling constraint from connector equation specification.
This processes scoped references and applies the specified transform.

---

### create_equation_imbalance_error

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:397`

**Signature:**
```julia
function create_equation_imbalance_error(model_name::String, num_equations::Int, num_unknowns::Int,
```

**Description:**
create_equation_imbalance_error(model_name, num_equations, num_unknowns, state_variables)

Create equation-unknown imbalance error with detailed suggestions.

---

### create_json_parse_error

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:362`

**Signature:**
```julia
function create_json_parse_error(message::String, file_path::String="", line_number::Union{Int, Nothing}=nothing)
```

**Description:**
create_json_parse_error(message, file_path="", line_number=nothing)

Create a JSON parse error with fix suggestions.

---

### create_mock_catalyst_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:448`

**Signature:**
```julia
function create_mock_catalyst_system(rsys::ReactionSystem, name::String, advanced_features::Bool)
```

**Description:**
create_mock_catalyst_system(rsys::ReactionSystem, name::String, advanced_features::Bool) -> MockCatalystSystem

Create a mock Catalyst system for testing when Catalyst is not available.

---

### create_mock_catalyst_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/catalyst.jl:218`

**Signature:**
```julia
function create_mock_catalyst_system(rs::ReactionSystem)
```

**Description:**
create_mock_catalyst_system(rs::ReactionSystem) -> MockCatalystSystem

Create a mock Catalyst system for testing when Catalyst.jl is not available.
Preserves all the structural information in a testable format.

---

### create_mock_mtk_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:249`

**Signature:**
```julia
function create_mock_mtk_system(model::Model, name::String, advanced_features::Bool)
```

**Description:**
create_mock_mtk_system(model::Model, name::String, advanced_features::Bool) -> MockMTKSystem

Create a mock MTK system for testing when ModelingToolkit is not available.

---

### create_mock_mtk_system_basic

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk.jl:79`

**Signature:**
```julia
function create_mock_mtk_system_basic(model::Model, name::String)
```

**Description:**
create_mock_mtk_system_basic(model::Model, name::String) -> MockMTKSystem

Create a mock MTK system for testing when ModelingToolkit is not available.

---

### create_model_with_mixed_events

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:261`

**Signature:**
```julia
function create_model_with_mixed_events(variables::Dict{String,ModelVariable},
```

**Description:**
create_model_with_mixed_events(variables, equations, events, subsystems) -> Model

Helper function to create Model from mixed events vector for backwards compatibility.

---

### create_performance_warning

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:501`

**Signature:**
```julia
function create_performance_warning(operation::String, duration::Float64, threshold::Float64=1.0)
```

**Description:**
create_performance_warning(operation, duration, threshold=1.0)

Create performance warning with optimization suggestions.

---

### create_real_catalyst_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:324`

**Signature:**
```julia
function create_real_catalyst_system(rsys::ReactionSystem, name::String, advanced_features::Bool)
```

**Description:**
create_real_catalyst_system(rsys::ReactionSystem, name::String, advanced_features::Bool) -> ReactionSystem

Create a real Catalyst ReactionSystem from an ESM reaction system.

---

### create_real_catalyst_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/catalyst.jl:79`

**Signature:**
```julia
function create_real_catalyst_system(rs::ReactionSystem)
```

**Description:**
create_real_catalyst_system(rs::ReactionSystem) -> ReactionSystem

Create a real Catalyst.jl ReactionSystem from an ESM ReactionSystem.
Handles the full conversion pipeline with proper symbolic mathematics.

---

### create_real_mtk_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:80`

**Signature:**
```julia
function create_real_mtk_system(model::Model, name::String, advanced_features::Bool)
```

**Description:**
create_real_mtk_system(model::Model, name::String, advanced_features::Bool) -> ODESystem

Create a real ModelingToolkit ODESystem from an ESM model.

---

### create_undefined_reference_error

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:443`

**Signature:**
```julia
function create_undefined_reference_error(reference::String, available_variables::Vector{String}=String[],
```

**Description:**
create_undefined_reference_error(reference, available_variables=String[], scope_path="")

Create undefined reference error with smart suggestions.

---

### create_variable_mapping_constraint

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:531`

**Signature:**
```julia
function create_variable_mapping_constraint(coupled_system, from_resolution, to_resolution, coupling)
```

**Description:**
create_variable_mapping_constraint(coupled_system, from_resolution, to_resolution, coupling)

Create an actual variable mapping constraint that modifies the coupled system.

---

### derivation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
derivation(...)
```

---

### derive_odes

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
derive_odes(...)
```

---

### describe_coupling_entry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:305`

**Signature:**
```julia
function describe_coupling_entry(entry::CouplingEntry)::String
```

**Description:**
describe_coupling_entry(entry::CouplingEntry) -> String

Produce a human-readable description of a coupling entry.

---

### dict_to_stoichiometry_entries

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:880`

**Signature:**
```julia
function dict_to_stoichiometry_entries(dict::Dict{String,Int})::Vector{StoichiometryEntry}
```

**Description:**
dict_to_stoichiometry_entries(dict::Dict{String,Int}) -> Vector{StoichiometryEntry}

Convert old-style Dict{String,Int} format to new StoichiometryEntry vector format.

---

### display

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
display(...)
```

---

### end_timer!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:311`

**Signature:**
```julia
function end_timer!(profiler::PerformanceProfiler, operation::String)
```

**Description:**
end_timer!(profiler, operation)

End timing an operation and return duration.

---

### esm_to_mock_symbolic

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
esm_to_mock_symbolic(...)
```

---

### esm_to_symbolic

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
esm_to_symbolic(...)
```

---

### esm_to_symbolic

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/catalyst.jl:309`

**Signature:**
```julia
function esm_to_symbolic(expr::Expr, var_dict::Dict)
```

**Description:**
esm_to_symbolic(expr::Expr, var_dict::Dict) -> Any

Convert ESM expression to symbolic form for Catalyst.jl.
Handles the expression mapping required for rate expressions.

---

### esm_to_symbolic_enhanced

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:919`

**Signature:**
```julia
function esm_to_symbolic_enhanced(expr::Expr, var_dict::Dict, advanced_features::Bool)
```

**Description:**
esm_to_symbolic_enhanced(expr::Expr, var_dict::Dict, advanced_features::Bool) -> Any

Enhanced ESM to symbolic conversion with support for advanced features and better error handling.

---

### evaluate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
evaluate(...)
```

**Available in other languages:**
- [Typescript](typescript.md#evaluate)

---

### evaluate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/expression.jl:183`

**Signature:**
```julia
function evaluate(expr::NumExpr, bindings::Dict{String,Float64})::Float64
```

**Description:**
evaluate(expr::Expr, bindings::Dict{String,Float64})::Float64

Numerically evaluate an expression using provided variable bindings.
Throws UnboundVariableError if any variable is not found in bindings.

# Arguments
- `expr`: The expression to evaluate
- `bindings`: Dictionary mapping variable names to numeric values

# Examples
```julia
x = VarExpr("x")
y = VarExpr("y")
sum_expr = OpExpr("+", [x, y])
bindings = Dict("x" => 2.0, "y" => 3.0)
result = evaluate(sum_expr, bindings)  # 5.0
```

# Supported Operations
- Arithmetic: "+", "-", "*", "/", "^"
- Mathematical functions: "sin", "cos", "tan", "exp", "log", "sqrt", "abs"
- Constants: "π", "e"

**Available in other languages:**
- [Typescript](typescript.md#evaluate)

---

### expr_to_string

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/catalyst.jl:455`

**Signature:**
```julia
function expr_to_string(expr::Expr)
```

**Description:**
expr_to_string(expr::Expr) -> String

Convert ESM expression to string representation for mock systems.

---

### expression_graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
expression_graph(...)
```

---

### expression_graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:326`

**Signature:**
```julia
function expression_graph(file::EsmFile)::Graph{VariableNode, DependencyEdge}
```

**Description:**
expression_graph(file::EsmFile) -> Graph{VariableNode, DependencyEdge}
    expression_graph(model::Model) -> Graph{VariableNode, DependencyEdge}
    expression_graph(system::ReactionSystem) -> Graph{VariableNode, DependencyEdge}
    expression_graph(equation::Equation) -> Graph{VariableNode, DependencyEdge}
    expression_graph(reaction::Reaction) -> Graph{VariableNode, DependencyEdge}
    expression_graph(expr::Expr) -> Graph{VariableNode, DependencyEdge}

Generate expression-level dependency graph showing variable relationships.

Creates nodes for variables and edges for dependencies based on expressions.
Supports different scoping levels from individual expressions to full files.

# Arguments
- Input can be EsmFile, Model, ReactionSystem, Equation, Reaction, or Expr

# Returns
- `Graph{VariableNode, DependencyEdge}`: Variable dependency graph

# Examples
```julia
# File-level analysis
graph = expression_graph(file)

# Model-level analysis
graph = expression_graph(model)

# Single equation analysis
graph = expression_graph(equation)
```

---

### extract

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
extract(...)
```

**Available in other languages:**
- [Typescript](typescript.md#extract)

---

### extract

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:507`

**Signature:**
```julia
function extract(file::EsmFile, component_name::String)::EsmFile
```

**Description:**
extract(file::EsmFile, component_name::String) -> EsmFile

Extract a single component into a standalone ESM file.

Creates a new file containing only the specified component and any
coupling entries that reference it.

**Available in other languages:**
- [Typescript](typescript.md#extract)

---

### extract_dependent_variables

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:164`

**Signature:**
```julia
function extract_dependent_variables(system)
```

**Description:**
extract_dependent_variables(system)

Extract dependent variables (LHS of differential equations) from a system.

---

### extract_variable_name

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:1249`

**Signature:**
```julia
function extract_variable_name(symbolic_var)
```

**Description:**
extract_variable_name(symbolic_var) -> String

Extract variable name from a symbolic variable, handling various formats.

---

### find_subsystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:770`

**Signature:**
```julia
function find_subsystem(system::Model, name::String)::Union{Model,Nothing}
```

**Description:**
find_subsystem(system::Union{Model,ReactionSystem}, name::String) -> Union{Model,ReactionSystem,Nothing}

Find a subsystem by name within a Model or ReactionSystem.
Returns the subsystem or nothing if not found.

---

### find_top_level_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:740`

**Signature:**
```julia
function find_top_level_system(esm_file::EsmFile, name::String)
```

**Description:**
find_top_level_system(esm_file::EsmFile, name::String) -> (Union{Model,ReactionSystem,DataLoader,Operator,Nothing}, Symbol)

Find a top-level system by name in models, reaction_systems, data_loaders, or operators.
Returns the system and its type, or (nothing, :none) if not found.

---

### flatten

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
flatten(...)
```

**Available in other languages:**
- [Typescript](typescript.md#flatten)

---

### flatten

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:96`

**Signature:**
```julia
function flatten(file::EsmFile)::FlattenedSystem
```

**Description:**
flatten(file::EsmFile) -> FlattenedSystem

Flatten coupled systems into a single system with dot-namespaced variables.

The algorithm:
1. Iterates over all models and reaction_systems in the EsmFile
2. Namespaces all variables by prefixing with "SystemName."
3. Recursively flattens subsystems using nested dot notation (e.g., "System.Sub.var")
4. Processes coupling entries to produce human-readable rule descriptions
5. Returns a unified FlattenedSystem

# Examples
```julia
file = load("coupled_model.esm")
flat = flatten(file)
println(flat.state_variables)  # ["Atmosphere.T", "Ocean.SST", ...]
println(flat.equations[1].lhs) # "Atmosphere.T"
```

**Available in other languages:**
- [Typescript](typescript.md#flatten)

---

### flatten_model!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:140`

**Signature:**
```julia
function flatten_model!(state_variables::Vector{String},
```

**Description:**
flatten_model!(state_variables, parameters, variables, equations, model, prefix)

Flatten a Model into the accumulator vectors, prefixing all variable names with `prefix.`.
Recursively processes subsystems.

---

### flatten_reaction_system!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:185`

**Signature:**
```julia
function flatten_reaction_system!(state_variables::Vector{String},
```

**Description:**
flatten_reaction_system!(state_variables, parameters, variables, equations, rsys, prefix)

Flatten a ReactionSystem into the accumulator vectors, prefixing all names with `prefix.`.
Species become state variables and reaction rate laws become equations.
Recursively processes subsystems.

---

### for

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
for(...)
```

---

### format

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
format(...)
```

---

### format_chemical_subscripts

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:129`

**Signature:**
```julia
function format_chemical_subscripts(variable::String, format::Symbol)
```

**Description:**
format_chemical_subscripts(variable::String, format::Symbol) -> String

Apply element-aware chemical subscript formatting to a variable name.
Uses greedy 2-char-before-1-char matching for element detection per spec Section 6.1.

# Arguments
- `variable::String`: Variable name to format
- `format::Symbol`: Output format (:unicode or :latex)

---

### format_expression_ascii

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
format_expression_ascii(...)
```

---

### format_expression_ascii

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:379`

**Signature:**
```julia
function format_expression_ascii(expr::Expr)
```

**Description:**
format_expression_ascii(expr::Expr) -> String

Format an expression as plain ASCII mathematical notation.

---

### format_expression_latex

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:358`

**Signature:**
```julia
function format_expression_latex(expr::Expr)
```

**Description:**
format_expression_latex(expr::Expr) -> String

Format an expression as LaTeX mathematical notation.

---

### format_expression_unicode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:337`

**Signature:**
```julia
function format_expression_unicode(expr::Expr)
```

**Description:**
format_expression_unicode(expr::Expr) -> String

Format an expression as Unicode mathematical notation.

---

### format_node_label

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
format_node_label(...)
```

---

### format_node_label

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:732`

**Signature:**
```julia
function format_node_label(name::String, node_type::String="")::String
```

**Description:**
format_node_label(name::String, node_type::String="") -> String

Format node label with chemical subscript rendering if applicable.
Detects chemical formulas and applies subscript formatting.

---

### format_number

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:203`

**Signature:**
```julia
function format_number(num::Real, format::Symbol)
```

**Description:**
format_number(num::Real, format::Symbol) -> String

Format a number in scientific notation with appropriate formatting.

---

### format_number_plain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:288`

**Signature:**
```julia
function format_number_plain(value::Float64)::String
```

**Description:**
format_number_plain(value::Float64) -> String

Format a floating-point number as a plain string, using integer notation for whole numbers.

---

### format_operator_expression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:400`

**Signature:**
```julia
function format_operator_expression(node::OpExpr, format::Symbol)
```

**Description:**
format_operator_expression(node::OpExpr, format::Symbol) -> String

Format an OpExpr (operator with arguments).

---

### format_user_friendly

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:215`

**Signature:**
```julia
function format_user_friendly(error::ESMError)
```

**Description:**
format_user_friendly(error)

Format error message for end users.

---

### free_variables

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
free_variables(...)
```

---

### free_variables

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/expression.jl:77`

**Signature:**
```julia
function free_variables(expr::NumExpr)::Set{String}
```

**Description:**
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

---

### from_catalyst_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
from_catalyst_system(...)
```

---

### from_catalyst_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:628`

**Signature:**
```julia
function from_catalyst_system(rs, name::String)
```

**Description:**
from_catalyst_system(rs, name::String) -> ReactionSystem

Convert a Catalyst ReactionSystem or MockCatalystSystem back to ESM ReactionSystem format.
Extracts species, parameters, reactions, and events from Catalyst symbolic form.

This function implements reverse conversion: taking Catalyst systems and reconstructing
ESM ReactionSystems with proper species mapping, parameter extraction, and reaction
reconstruction. Maps Catalyst Reaction objects to ESM Reaction format with proper
stoichiometry and rate expressions.

---

### from_mock_catalyst_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:1206`

**Signature:**
```julia
function from_mock_catalyst_system(sys::MockCatalystSystem, name::String)
```

**Description:**
from_mock_catalyst_system(sys::MockCatalystSystem, name::String) -> ReactionSystem

Convert a MockCatalystSystem back to ESM ReactionSystem format.
This handles the case when Catalyst is not available but we have mock systems.

---

### from_mock_mtk_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:1154`

**Signature:**
```julia
function from_mock_mtk_system(sys::MockMTKSystem, name::String)
```

**Description:**
from_mock_mtk_system(sys::MockMTKSystem, name::String) -> Model

Convert a MockMTKSystem back to ESM Model format.
This handles the case when MTK is not available but we have mock systems.

---

### from_mtk_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
from_mtk_system(...)
```

---

### from_mtk_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:477`

**Signature:**
```julia
function from_mtk_system(sys, name::String)
```

**Description:**
from_mtk_system(sys, name::String) -> Model

Convert a ModelingToolkit ODESystem or MockMTKSystem back to ESM Model format.
Extracts variables, equations, and events from MTK symbolic form.

This function implements reverse conversion: taking MTK systems and reconstructing
ESM Models with proper variable classification, equation extraction, and event handling.
Maps Differential(t)(var) → D(var,t), symbolic operations → OpExpr, and detects
state vs parameter vs observed variable types.

---

### functionality

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
functionality(...)
```

---

### functions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
functions(...)
```

---

### functions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
functions(...)
```

---

### functions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
functions(...)
```

---

### functions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
functions(...)
```

---

### generation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
generation(...)
```

---

### get_expression_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
get_expression_dimensions(...)
```

---

### get_expression_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:51`

**Signature:**
```julia
function get_expression_dimensions(expr::EarthSciSerialization.Expr, var_units::Dict{String, String})::Union{Unitful.Units, Nothing}
```

**Description:**
Get the dimensions of an expression by propagating units through operations.

This performs dimensional analysis to determine the units that result from
evaluating an expression, assuming all variables have known units.

---

### get_operator_precedence

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:252`

**Signature:**
```julia
function get_operator_precedence(op::String)
```

**Description:**
get_operator_precedence(op::String) -> Int

Get operator precedence for proper parenthesization.

---

### get_performance_report

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:332`

**Signature:**
```julia
function get_performance_report(profiler::PerformanceProfiler)
```

**Description:**
get_performance_report(profiler)

Get performance report.

---

### get_products_dict

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:928`

**Signature:**
```julia
function get_products_dict(reaction::Reaction)::Dict{String,Int}
```

**Description:**
get_products_dict(reaction::Reaction) -> Dict{String,Int}

Get products as dictionary for backward compatibility.

---

### get_reactants_dict

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:913`

**Signature:**
```julia
function get_reactants_dict(reaction::Reaction)::Dict{String,Int}
```

**Description:**
get_reactants_dict(reaction::Reaction) -> Dict{String,Int}

Get reactants as dictionary for backward compatibility.

---

### get_summary

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:194`

**Signature:**
```julia
function get_summary(collector::ErrorCollector)
```

**Description:**
get_summary(collector)

Get a summary of all collected errors and warnings.

---

### get_system_domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:869`

**Signature:**
```julia
function get_system_domain(file::EsmFile, system_name::String)
```

**Description:**
get_system_domain(file::EsmFile, system_name::String) -> Union{String,Nothing,Missing}

Get the domain of a system by name. Returns:
- String: the domain name
- nothing: system is 0D (no domain)
- missing: system not found

---

### has_element_pattern

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:72`

**Signature:**
```julia
function has_element_pattern(variable::String)
```

**Description:**
has_element_pattern(variable::String) -> Bool

Check if a variable has element patterns (for chemical formula detection).
Uses greedy matching algorithm per spec Section 6.1.

---

### infer_variable_units

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
infer_variable_units(...)
```

---

### infer_variable_units

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:330`

**Signature:**
```julia
function infer_variable_units(var_name::String, equations::Vector{Equation}, known_units::Dict{String, String})::Union{String, Nothing}
```

**Description:**
Infer appropriate units for a variable based on its usage in equations.

This can help suggest units when they are not explicitly specified.

---

### is_valid_identifier

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
is_valid_identifier(...)
```

---

### is_valid_identifier

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:851`

**Signature:**
```julia
function is_valid_identifier(name::String)::Bool
```

**Description:**
is_valid_identifier(name::String) -> Bool

Check if a string is a valid identifier (letters, numbers, underscores, no leading digit).

---

### load

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
load(...)
```

**Available in other languages:**
- [Python](python.md#load)
- [Typescript](typescript.md#load)

---

### load

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:705`

**Signature:**
```julia
function load(path::String)::EsmFile
```

**Description:**
load(path::String) -> EsmFile

Load and parse an ESM file from a file path.
Automatically resolves any subsystem references (local or remote) relative
to the directory containing the file.

**Available in other languages:**
- [Python](python.md#load)
- [Typescript](typescript.md#load)

---

### load

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:720`

**Signature:**
```julia
function load(io::IO)::EsmFile
```

**Description:**
load(io::IO) -> EsmFile

Load and parse an ESM file from an IO stream.

**Available in other languages:**
- [Python](python.md#load)
- [Typescript](typescript.md#load)

---

### map_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
map_variable(...)
```

---

### map_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:447`

**Signature:**
```julia
function map_variable(file::EsmFile, from::String, to::String, transform::Union{EarthSciSerialization.Expr,Nothing}=nothing)::EsmFile
```

**Description:**
map_variable(file::EsmFile, from::String, to::String, transform::Union{Expr,Nothing}=nothing) -> EsmFile

Convenience function to create a variable_map coupling entry.

---

### mass_action_rate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
mass_action_rate(...)
```

---

### merge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
merge(...)
```

**Available in other languages:**
- [Typescript](typescript.md#merge)

---

### merge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:462`

**Signature:**
```julia
function merge(file_a::EsmFile, file_b::EsmFile)::EsmFile
```

**Description:**
merge(file_a::EsmFile, file_b::EsmFile) -> EsmFile

Merge two ESM files.

Combines all components from both files. In case of conflicts, components
from file_b take precedence.

**Available in other languages:**
- [Typescript](typescript.md#merge)

---

### mock_symbolic_to_esm

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
mock_symbolic_to_esm(...)
```

---

### namespace_expression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:229`

**Signature:**
```julia
function namespace_expression(expr::Expr, prefix::String)::String
```

**Description:**
namespace_expression(expr::Expr, prefix::String) -> String

Convert an ESM expression to a string with all variable references prefixed by `prefix.`.
Numeric literals and operators are preserved as-is.

---

### namespace_op_expression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:251`

**Signature:**
```julia
function namespace_op_expression(expr::OpExpr, prefix::String)::String
```

**Description:**
namespace_op_expression(expr::OpExpr, prefix::String) -> String

Convert an operator expression to a string with namespaced variable references.

---

### needs_parentheses

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:271`

**Signature:**
```julia
function needs_parentheses(parent_op::String, child::Expr, is_right_operand::Bool=false)
```

**Description:**
needs_parentheses(parent_op::String, child::Expr, is_right_operand::Bool=false) -> Bool

Check if parentheses are needed around a subexpression.

---

### operations

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
operations(...)
```

---

### operations

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
operations(...)
```

---

### operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
operator(...)
```

---

### operator_apply

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:693`

**Signature:**
```julia
function operator_apply(coupled_system::MockCoupledSystem, coupling::CouplingOperatorApply, file::EsmFile)
```

**Description:**
operator_apply(coupled_system::MockCoupledSystem, coupling::CouplingOperatorApply, file::EsmFile)

Register an Operator in CoupledSystem.ops for runtime execution.

---

### operator_compose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:118`

**Signature:**
```julia
function operator_compose(coupled_system::MockCoupledSystem, coupling::CouplingOperatorCompose)
```

**Description:**
operator_compose(coupled_system::MockCoupledSystem, coupling::CouplingOperatorCompose)

Implement the operator_compose algorithm from specification Section 4.7.1:
1. Extract dependent variables from both systems
2. Apply translation mappings if specified
3. Match equations (direct, translation, _var placeholder expansion)
4. Combine matched RHS terms by addition
5. Preserve unmatched equations

---

### parse_expression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:31`

**Signature:**
```julia
function parse_expression(data::Any)::Expr
```

**Description:**
parse_expression(data::Any) -> Expr

Parse JSON data into an Expression (NumExpr, VarExpr, or OpExpr).
Handles the oneOf discriminated union based on JSON structure.

---

### parse_mock_expression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:1274`

**Signature:**
```julia
function parse_mock_expression(expr_str::AbstractString)
```

**Description:**
parse_mock_expression(expr_str::AbstractString) -> Expr

Parse a string representation of an expression into an ESM Expr.
This is a simple parser for mock system string representations.

---

### parse_mock_reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:1326`

**Signature:**
```julia
function parse_mock_reaction(rxn_str::String)
```

**Description:**
parse_mock_reaction(rxn_str::String) -> Union{Reaction, Nothing}

Parse a string representation of a reaction into an ESM Reaction.
Expected format: "A + 2B -> C + D, rate: k1" or "A -> B"

---

### parse_model_variable_type

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:62`

**Signature:**
```julia
function parse_model_variable_type(data::String)::ModelVariableType
```

**Description:**
parse_model_variable_type(data::String) -> ModelVariableType

Parse string into ModelVariableType enum.

---

### parse_species_list

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:1391`

**Signature:**
```julia
function parse_species_list(species_str::String)
```

**Description:**
parse_species_list(species_str::String) -> Dict{String, Int}

Parse a species list like "A + 2B + C" into a dictionary of species and stoichiometry.
Handles special case "∅" for empty (null) reactants/products.

---

### parse_trigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:79`

**Signature:**
```julia
function parse_trigger(data::Dict)::DiscreteEventTrigger
```

**Description:**
parse_trigger(data::Dict) -> DiscreteEventTrigger

Parse JSON data into a DiscreteEventTrigger based on discriminator fields.

---

### parse_units

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
parse_units(...)
```

---

### parse_units

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:15`

**Signature:**
```julia
function parse_units(unit_str::String)::Union{Unitful.Units, Nothing}
```

**Description:**
Parse a unit string into a Unitful.Units object.

Handles common scientific units and compositions used in Earth system models.

---

### predecessors

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
predecessors(...)
```

---

### predecessors

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:84`

**Signature:**
```julia
function predecessors(graph::Graph{N, E}, node::N) where {N, E}
```

**Description:**
Get nodes that point to this node.

---

### process_connector_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:454`

**Signature:**
```julia
function process_connector_equation(coupled_system, equation, systems)
```

**Description:**
process_connector_equation(coupled_system, equation, systems)

Process a single connector equation, resolving scoped references and applying transforms.

---

### process_event_affects

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:1089`

**Signature:**
```julia
function process_event_affects(affects, symbolic_vars::Dict, advanced_features::Bool)
```

**Description:**
process_event_affects(affects, symbolic_vars::Dict, advanced_features::Bool)

Process event affects for MTK callbacks.

---

### process_events_enhanced

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:1034`

**Signature:**
```julia
function process_events_enhanced(events::Vector{EventType}, symbolic_vars::Dict, advanced_features::Bool)
```

**Description:**
process_events_enhanced(events::Vector{EventType}, symbolic_vars::Dict, advanced_features::Bool)

Enhanced event processing with comprehensive MTK callback support.

---

### process_reaction_events

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/catalyst.jl:376`

**Signature:**
```julia
function process_reaction_events(events::Vector, var_dict::Dict)
```

**Description:**
process_reaction_events(events::Vector, var_dict::Dict) -> (Vector, Vector)

Process ESM events for inclusion in Catalyst ReactionSystem.
Returns (continuous_events, discrete_events).

---

### reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
reference(...)
```

---

### reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
reference(...)
```

---

### remove_coupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
remove_coupling(...)
```

---

### remove_coupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:411`

**Signature:**
```julia
function remove_coupling(file::EsmFile, index::Int)::EsmFile
```

**Description:**
remove_coupling(file::EsmFile, index::Int) -> EsmFile

Remove a coupling entry by index.

---

### remove_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
remove_equation(...)
```

---

### remove_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:149`

**Signature:**
```julia
function remove_equation(model::Model, index::Int)::Model
```

**Description:**
remove_equation(model::Model, index::Int) -> Model
    remove_equation(model::Model, lhs_pattern::Expr) -> Model

Remove an equation from a model.

Can remove by index (1-based) or by matching the left-hand side expression.

---

### remove_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
remove_event(...)
```

---

### remove_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:360`

**Signature:**
```julia
function remove_event(model::Model, name::String)::Model
```

**Description:**
remove_event(model::Model, name::String) -> Model

Remove an event by name from a model.

Searches both continuous and discrete events.

---

### remove_reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
remove_reaction(...)
```

---

### remove_reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:231`

**Signature:**
```julia
function remove_reaction(system::ReactionSystem, id::String)::ReactionSystem
```

**Description:**
remove_reaction(system::ReactionSystem, id::String) -> ReactionSystem

Remove a reaction by its ID.

Note: This assumes reactions have an `id` field. If not available,
this function will search by reaction equality.

---

### remove_species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
remove_species(...)
```

---

### remove_species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:287`

**Signature:**
```julia
function remove_species(system::ReactionSystem, name::String)::ReactionSystem
```

**Description:**
remove_species(system::ReactionSystem, name::String) -> ReactionSystem

Remove a species from a reaction system.

Warns about dependent reactions but does not automatically update them.

---

### remove_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
remove_variable(...)
```

---

### remove_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:44`

**Signature:**
```julia
function remove_variable(model::Model, name::String)::Model
```

**Description:**
remove_variable(model::Model, name::String) -> Model

Remove a variable from a model.

Creates a new model without the specified variable. Warns about dependencies
but does not automatically update equations that reference the variable.

---

### rename_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
rename_variable(...)
```

---

### rename_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:84`

**Signature:**
```julia
function rename_variable(model::Model, old_name::String, new_name::String)::Model
```

**Description:**
rename_variable(model::Model, old_name::String, new_name::String) -> Model

Rename a variable throughout the model.

Updates the variable definition and all references in equations.

---

### render_chemical_formula

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
render_chemical_formula(...)
```

---

### render_chemical_formula

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:699`

**Signature:**
```julia
function render_chemical_formula(formula::String)::String
```

**Description:**
render_chemical_formula(formula::String) -> String

Convert chemical formula to format with subscripts for visualization.
Replaces numeric digits with Unicode subscript characters.

# Examples
```julia
render_chemical_formula("CO2") # "CO₂"
render_chemical_formula("H2SO4") # "H₂SO₄"
render_chemical_formula("CH3OH") # "CH₃OH"
```

---

### rendering

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
rendering(...)
```

---

### resolution

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
resolution(...)
```

---

### resolution

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
resolution(...)
```

---

### resolve_qualified_reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
resolve_qualified_reference(...)
```

---

### resolve_qualified_reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:685`

**Signature:**
```julia
function resolve_qualified_reference(esm_file::EsmFile, reference::String)::ReferenceResolution
```

**Description:**
resolve_qualified_reference(esm_file::EsmFile, reference::String) -> ReferenceResolution

Resolve a qualified reference string using hierarchical dot notation.

The reference string is split on dots to produce segments [s₁, s₂, …, sₙ].
The final segment sₙ is the variable name. The preceding segments [s₁, …, sₙ₋₁]
form a path through the subsystem hierarchy.

## Algorithm
1. Split reference on "." to get segments
2. First segment must match a top-level system (models, reaction_systems, data_loaders, operators)
3. Each subsequent segment must match a key in the parent system's subsystems map
4. Final segment is the variable name to resolve

## Examples
- `"SuperFast.O3"` → Variable `O3` in top-level model `SuperFast`
- `"SuperFast.GasPhase.O3"` → Variable `O3` in subsystem `GasPhase` of model `SuperFast`
- `"Atmosphere.Chemistry.FastChem.NO2"` → Variable `NO2` in nested subsystems

## Throws
- `QualifiedReferenceError` if reference cannot be resolved

---

### resolve_subsystem_refs!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
resolve_subsystem_refs!(...)
```

---

### resolve_subsystem_refs!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:778`

**Signature:**
```julia
function resolve_subsystem_refs!(file::EsmFile, base_path::String)
```

**Description:**
resolve_subsystem_refs!(file::EsmFile, base_path::String)

Resolve all subsystem references in-place. Walks all models and reaction_systems,
and for each subsystem that was parsed from a `{"ref": "..."}` object, loads the
referenced file and replaces the subsystem content.

References can be:
- Local file paths (resolved relative to `base_path`)
- Remote URLs starting with `http://` or `https://`

Circular references are detected and raise a `SubsystemRefError`.

# Arguments
- `file::EsmFile`: the parsed ESM file to resolve references in
- `base_path::String`: directory path for resolving relative file references

---

### save

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
save(...)
```

**Available in other languages:**
- [Typescript](typescript.md#save)

---

### save

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:700`

**Signature:**
```julia
function save(file::EsmFile, path::String)
```

**Description:**
save(file::EsmFile, path::String)

Save an EsmFile object to a JSON file at the specified path.

**Available in other languages:**
- [Typescript](typescript.md#save)

---

### save

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:711`

**Signature:**
```julia
function save(file::EsmFile, io::IO)
```

**Description:**
save(file::EsmFile, io::IO)

Save an EsmFile object to a JSON stream.

**Available in other languages:**
- [Typescript](typescript.md#save)

---

### serialization

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
serialization(...)
```

---

### serialize_affect_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:150`

**Signature:**
```julia
function serialize_affect_equation(affect::AffectEquation)::Dict{String,Any}
```

**Description:**
serialize_affect_equation(affect::AffectEquation) -> Dict{String,Any}

Serialize AffectEquation to JSON-compatible format.

---

### serialize_callback

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:519`

**Signature:**
```julia
function serialize_callback(entry::CouplingCallback)::Dict{String,Any}
```

**Description:**
serialize_callback(entry::CouplingCallback) -> Dict{String,Any}

Serialize callback coupling entry.

---

### serialize_continuous_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:134`

**Signature:**
```julia
function serialize_continuous_event(event::ContinuousEvent)::Dict{String,Any}
```

**Description:**
serialize_continuous_event(event::ContinuousEvent) -> Dict{String,Any}

Serialize ContinuousEvent to JSON-compatible format.

---

### serialize_couple

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:450`

**Signature:**
```julia
function serialize_couple(entry::CouplingCouple)::Dict{String,Any}
```

**Description:**
serialize_couple(entry::CouplingCouple) -> Dict{String,Any}

Serialize couple coupling entry.

---

### serialize_coupling_entry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
serialize_coupling_entry(...)
```

---

### serialize_coupling_entry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:403`

**Signature:**
```julia
function serialize_coupling_entry(entry::CouplingEntry)::Dict{String,Any}
```

**Description:**
serialize_coupling_entry(entry::CouplingEntry) -> Dict{String,Any}

Serialize CouplingEntry to JSON-compatible format based on concrete type.

---

### serialize_data_loader

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:349`

**Signature:**
```julia
function serialize_data_loader(loader::DataLoader)::Dict{String,Any}
```

**Description:**
serialize_data_loader(loader::DataLoader) -> Dict{String,Any}

Serialize DataLoader to JSON-compatible format.

---

### serialize_discrete_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:118`

**Signature:**
```julia
function serialize_discrete_event(event::DiscreteEvent)::Dict{String,Any}
```

**Description:**
serialize_discrete_event(event::DiscreteEvent) -> Dict{String,Any}

Serialize DiscreteEvent to JSON-compatible format.

---

### serialize_discrete_event_trigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:80`

**Signature:**
```julia
function serialize_discrete_event_trigger(trigger::DiscreteEventTrigger)::Dict{String,Any}
```

**Description:**
serialize_discrete_event_trigger(trigger::DiscreteEventTrigger) -> Dict{String,Any}

Alias for serialize_trigger for backward compatibility.

---

### serialize_domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:629`

**Signature:**
```julia
function serialize_domain(domain::Domain)::Dict{String,Any}
```

**Description:**
serialize_domain(domain::Domain) -> Dict{String,Any}

Serialize Domain to JSON-compatible format.

---

### serialize_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:199`

**Signature:**
```julia
function serialize_equation(eq::Equation)::Dict{String,Any}
```

**Description:**
serialize_equation(eq::Equation) -> Dict{String,Any}

Serialize Equation to JSON-compatible format.

---

### serialize_esm_file

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:664`

**Signature:**
```julia
function serialize_esm_file(file::EsmFile)::Dict{String,Any}
```

**Description:**
serialize_esm_file(file::EsmFile) -> Dict{String,Any}

Serialize EsmFile to JSON-compatible format.

---

### serialize_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:89`

**Signature:**
```julia
function serialize_event(event::EventType)::Dict{String,Any}
```

**Description:**
serialize_event(event::EventType) -> Dict{String,Any}

Serialize EventType to JSON-compatible format.

---

### serialize_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:537`

**Signature:**
```julia
function serialize_event(entry::CouplingEvent)::Dict{String,Any}
```

**Description:**
serialize_event(entry::CouplingEvent) -> Dict{String,Any}

Serialize event coupling entry.

---

### serialize_expression

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:15`

**Signature:**
```julia
function serialize_expression(expr::Expr)
```

**Description:**
serialize_expression(expr::Expr) -> Any

Serialize an Expression to JSON-compatible format.
Handles the union type discrimination.

---

### serialize_functional_affect

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:162`

**Signature:**
```julia
function serialize_functional_affect(affect::FunctionalAffect)::Dict{String,Any}
```

**Description:**
serialize_functional_affect(affect::FunctionalAffect) -> Dict{String,Any}

Serialize FunctionalAffect to JSON-compatible format.

---

### serialize_interface

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:645`

**Signature:**
```julia
function serialize_interface(iface::Interface)::Dict{String,Any}
```

**Description:**
serialize_interface(iface::Interface) -> Dict{String,Any}

Serialize Interface to JSON-compatible format.

---

### serialize_metadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:596`

**Signature:**
```julia
function serialize_metadata(metadata::Metadata)::Dict{String,Any}
```

**Description:**
serialize_metadata(metadata::Metadata) -> Dict{String,Any}

Serialize Metadata to JSON-compatible format.

---

### serialize_model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:215`

**Signature:**
```julia
function serialize_model(model::Model)::Dict{String,Any}
```

**Description:**
serialize_model(model::Model) -> Dict{String,Any}

Serialize Model to JSON-compatible format.

---

### serialize_model_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:178`

**Signature:**
```julia
function serialize_model_variable(var::ModelVariable)::Dict{String,Any}
```

**Description:**
serialize_model_variable(var::ModelVariable) -> Dict{String,Any}

Serialize ModelVariable to JSON-compatible format.

---

### serialize_model_variable_type

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:42`

**Signature:**
```julia
function serialize_model_variable_type(var_type::ModelVariableType)::String
```

**Description:**
serialize_model_variable_type(var_type::ModelVariableType) -> String

Serialize ModelVariableType enum to string.

---

### serialize_operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:378`

**Signature:**
```julia
function serialize_operator(op::Operator)::Dict{String,Any}
```

**Description:**
serialize_operator(op::Operator) -> Dict{String,Any}

Serialize Operator to JSON-compatible format.

---

### serialize_operator_apply

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:504`

**Signature:**
```julia
function serialize_operator_apply(entry::CouplingOperatorApply)::Dict{String,Any}
```

**Description:**
serialize_operator_apply(entry::CouplingOperatorApply) -> Dict{String,Any}

Serialize operator_apply coupling entry.

---

### serialize_operator_compose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:426`

**Signature:**
```julia
function serialize_operator_compose(entry::CouplingOperatorCompose)::Dict{String,Any}
```

**Description:**
serialize_operator_compose(entry::CouplingOperatorCompose) -> Dict{String,Any}

Serialize operator_compose coupling entry.

---

### serialize_parameter

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:269`

**Signature:**
```julia
function serialize_parameter(param::Parameter)::Dict{String,Any}
```

**Description:**
serialize_parameter(param::Parameter) -> Dict{String,Any}

Serialize Parameter to JSON-compatible format.
Note: Parameter name is the key in the parameters dictionary, not a property of the Parameter object.

---

### serialize_reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:288`

**Signature:**
```julia
function serialize_reaction(reaction::Reaction)::Dict{String,Any}
```

**Description:**
serialize_reaction(reaction::Reaction) -> Dict{String,Any}

Serialize Reaction to JSON-compatible format.

---

### serialize_reaction_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:330`

**Signature:**
```julia
function serialize_reaction_system(rs::ReactionSystem)::Dict{String,Any}
```

**Description:**
serialize_reaction_system(rs::ReactionSystem) -> Dict{String,Any}

Serialize ReactionSystem to JSON-compatible format.

---

### serialize_reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:574`

**Signature:**
```julia
function serialize_reference(ref::Reference)::Dict{String,Any}
```

**Description:**
serialize_reference(ref::Reference) -> Dict{String,Any}

Serialize Reference to JSON-compatible format.

---

### serialize_species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:249`

**Signature:**
```julia
function serialize_species(species::Species)::Dict{String,Any}
```

**Description:**
serialize_species(species::Species) -> Dict{String,Any}

Serialize Species to JSON-compatible format.
Note: Species name is the key in the species dictionary, not a property of the Species object.

---

### serialize_trigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:59`

**Signature:**
```julia
function serialize_trigger(trigger::DiscreteEventTrigger)::Dict{String,Any}
```

**Description:**
serialize_trigger(trigger::DiscreteEventTrigger) -> Dict{String,Any}

Serialize DiscreteEventTrigger to JSON-compatible format.

---

### serialize_variable_map

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:475`

**Signature:**
```julia
function serialize_variable_map(entry::CouplingVariableMap)::Dict{String,Any}
```

**Description:**
serialize_variable_map(entry::CouplingVariableMap) -> Dict{String,Any}

Serialize variable_map coupling entry.

---

### simplify

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
simplify(...)
```

**Available in other languages:**
- [Typescript](typescript.md#simplify)

---

### simplify

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/expression.jl:338`

**Signature:**
```julia
function simplify(expr::NumExpr)::Expr
```

**Description:**
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

**Available in other languages:**
- [Typescript](typescript.md#simplify)

---

### start_timer!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:302`

**Signature:**
```julia
function start_timer!(profiler::PerformanceProfiler, operation::String)
```

**Description:**
start_timer!(profiler, operation)

Start timing an operation.

---

### stoichiometric_matrix

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
stoichiometric_matrix(...)
```

---

### stoichiometry_entries_to_dict

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:889`

**Signature:**
```julia
function stoichiometry_entries_to_dict(entries::Vector{StoichiometryEntry})::Dict{String,Int}
```

**Description:**
stoichiometry_entries_to_dict(entries::Vector{StoichiometryEntry}) -> Dict{String,Int}

Convert new StoichiometryEntry vector format to old-style Dict{String,Int} format.

---

### subscript

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
subscript(...)
```

---

### substitute

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
substitute(...)
```

**Available in other languages:**
- [Typescript](typescript.md#substitute)

---

### substitute

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/expression.jl:42`

**Signature:**
```julia
function substitute(expr::NumExpr, bindings::Dict{String,Expr})::Expr
```

**Description:**
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

**Available in other languages:**
- [Typescript](typescript.md#substitute)

---

### substitute_in_equations

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
substitute_in_equations(...)
```

---

### substitute_in_equations

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:186`

**Signature:**
```julia
function substitute_in_equations(model::Model, bindings::Dict{String, EarthSciSerialization.Expr})::Model
```

**Description:**
substitute_in_equations(model::Model, bindings::Dict{String, Expr}) -> Model

Apply substitutions across all equations in a model.

Replaces variables according to the bindings dictionary.

---

### successors

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
successors(...)
```

---

### successors

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:97`

**Signature:**
```julia
function successors(graph::Graph{N, E}, node::N) where {N, E}
```

**Description:**
Get nodes that this node points to.

---

### suggest_model_improvements

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:616`

**Signature:**
```julia
function suggest_model_improvements(esm_file, errors)
```

**Description:**
suggest_model_improvements(esm_file, errors)

Suggest improvements based on error patterns.

---

### symbolic_to_esm

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
symbolic_to_esm(...)
```

---

### symbolic_to_esm

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:830`

**Signature:**
```julia
function symbolic_to_esm(symbolic_expr)
```

**Description:**
symbolic_to_esm(symbolic_expr) -> Expr

Convert Symbolics/MTK symbolic expression back to ESM form.

---

### system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
system(...)
```

---

### system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
system(...)
```

---

### system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
system(...)
```

---

### system_exists_in_file

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:606`

**Signature:**
```julia
function system_exists_in_file(file::EsmFile, system_name::String)::Bool
```

**Description:**
system_exists_in_file(file::EsmFile, system_name::String) -> Bool

Check if a system (model, reaction_system, data_loader, or operator) exists in the ESM file.

---

### tests

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
tests(...)
```

---

### to_ascii

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
to_ascii(...)
```

---

### to_ascii

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:866`

**Signature:**
```julia
function to_ascii(target)
```

**Description:**
to_ascii(target) -> String

Format target as plain ASCII mathematical notation.

Provides plain ASCII output for expressions, equations, models, reaction systems,
and ESM files. Uses standard ASCII operators (*, /, ^) and function call notation
for mathematical functions.

# Arguments
- `target`: Expression, equation, model, reaction system, or ESM file to format

# Returns
- Plain ASCII string representation (no Unicode symbols)

# Examples
```julia
expr = OpExpr("*", [VarExpr("x"), NumExpr(2.0)])
to_ascii(expr)  # Returns "x*2"

eq = Equation(VarExpr("y"), OpExpr("+", [VarExpr("x"), NumExpr(1.0)]))
to_ascii(eq)   # Returns "y = x + 1"
```

---

### to_catalyst_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
to_catalyst_system(...)
```

---

### to_catalyst_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:304`

**Signature:**
```julia
function to_catalyst_system(reaction_system::ReactionSystem, name::String; advanced_features=false)
```

**Description:**
to_catalyst_system(reaction_system::ReactionSystem, name::String; advanced_features=false) -> Union{ReactionSystem, MockCatalystSystem}

Convert an ESM ReactionSystem to a Catalyst ReactionSystem with comprehensive features.

# Arguments
- `reaction_system::ReactionSystem`: ESM reaction system to convert
- `name::String`: Name for the resulting system
- `advanced_features::Bool`: Enable advanced features

# Enhanced Features
- Species and parameter registration with metadata preservation
- Rate law expression translation with kinetics detection
- Conservation law preservation
- Mass action vs. general kinetics handling
- Event system support for reaction systems
- Performance optimization hints for large systems

---

### to_catalyst_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/catalyst.jl:58`

**Signature:**
```julia
function to_catalyst_system(rs::ReactionSystem)
```

**Description:**
to_catalyst_system(rs::ReactionSystem)::Union{ReactionSystem, MockCatalystSystem}

Convert an ESM ReactionSystem to a Catalyst.jl ReactionSystem.

This function implements the ESM → Catalyst system conversion task by:
1. Mapping ESM species to @species declarations
2. Converting ESM parameters to @parameters declarations
3. Translating ESM reactions to Reaction() objects
4. Handling null substrates for source reactions (no reactants)
5. Handling null products for sink reactions (no products)
6. Converting rate expressions via symbolic expression mapping
7. Processing constraint_equations as additional equations (if present)
8. Copying events (if present in the ReactionSystem)

# Arguments
- `rs::ReactionSystem`: ESM ReactionSystem to convert

# Returns
- `Union{ReactionSystem, MockCatalystSystem}`: Catalyst ReactionSystem or mock equivalent

# Examples
```julia
# Simple A → B reaction
species = [Species("A"), Species("B")]
parameters = [Parameter("k", 0.1)]
reactions = [Reaction(Dict("A" => 1), Dict("B" => 1), VarExpr("k"))]
rs = ReactionSystem(species, reactions; parameters=parameters)

catalyst_sys = to_catalyst_system(rs)
```

# Error Handling
- Gracefully falls back to mock implementation if Catalyst.jl unavailable
- Warns about unsupported features but continues processing
- Validates species and parameter references in reactions

---

### to_coupled_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
to_coupled_system(...)
```

---

### to_coupled_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:63`

**Signature:**
```julia
function to_coupled_system(file::EsmFile)::MockCoupledSystem
```

**Description:**
to_coupled_system(file::EsmFile)::MockCoupledSystem

Convert an ESM file with coupling rules into a coupled system.
This implements the Full tier capability for coupled system assembly
handling operator_compose, couple, variable_map, and operator_apply.

The algorithm processes coupling entries in array order for deterministic naming
and applies the four main coupling operations:
1. operator_compose - Compose systems by matching equations
2. couple - Bidirectional coupling via connector equations
3. variable_map - Map variables between systems with transforms
4. operator_apply - Register operators for runtime

Returns a MockCoupledSystem that would be compatible with OrdinaryDiffEq.jl
in a real implementation with EarthSciMLBase.

---

### to_dot

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
to_dot(...)
```

---

### to_dot

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:748`

**Signature:**
```julia
function to_dot(graph::Graph{ComponentNode, CouplingEdge})::String
```

**Description:**
Export graph to DOT format for Graphviz rendering.

---

### to_json

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
to_json(...)
```

---

### to_json

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:892`

**Signature:**
```julia
function to_json(graph::Graph{N, E})::String where {N, E}
```

**Description:**
Export graph to JSON adjacency list format.

---

### to_julia_code

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
to_julia_code(...)
```

---

### to_mermaid

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
to_mermaid(...)
```

---

### to_mermaid

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:825`

**Signature:**
```julia
function to_mermaid(graph::Graph{ComponentNode, CouplingEdge})::String
```

**Description:**
Export graph to Mermaid format for markdown embedding.

---

### to_mtk_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
to_mtk_system(...)
```

---

### to_mtk_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk_catalyst.jl:60`

**Signature:**
```julia
function to_mtk_system(model::Model, name::String; advanced_features=false)
```

**Description:**
to_mtk_system(model::Model, name::String; advanced_features=false) -> Union{ODESystem, MockMTKSystem}

Convert an ESM Model to a ModelingToolkit ODESystem with comprehensive features.

# Arguments
- `model::Model`: ESM model to convert
- `name::String`: Name for the resulting system
- `advanced_features::Bool`: Enable advanced features like algebraic reduction

# Enhanced Features
- Parameter/variable mapping with proper scoping and metadata preservation
- Event system translation (continuous/discrete) with full MTK compatibility
- Initial condition and boundary condition handling
- Symbolic differentiation integration with enhanced expression support
- Hierarchical system composition for complex models
- Cross-system coupling via MTK connectors
- Automated algebraic reduction where possible
- Numerical method selection optimization
- Performance profiling integration

---

### to_mtk_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mtk.jl:57`

**Signature:**
```julia
function to_mtk_system(model::Model, name::Union{String,Nothing}=nothing)
```

**Description:**
to_mtk_system(model::Model, name::Union{String,Nothing}=nothing)

Convert an ESM Model to a ModelingToolkit ODESystem or MockMTKSystem.

# Arguments
- `model::Model`: ESM model containing variables, equations, and events
- `name::Union{String,Nothing}`: Optional name for the system (defaults to :anonymous)

# Returns
- `ODESystem` or `MockMTKSystem`: Real or mock system depending on availability

# Expression mapping:
- `OpExpr('+')` → +
- `OpExpr('D', wrt='t')` → Differential(t)(var)
- `OpExpr('exp')` → exp
- `OpExpr('Pre')` → Pre
- `OpExpr('grad', dim='y')` → Differential(y)(var)
- `OpExpr('ifelse')` → ifelse
- `NumExpr` → literal
- `VarExpr` → @variables/@parameters based on type

Creates symbolic variables for state vars as functions of t, parameters as plain symbols.
Maps equations to MTK ~ syntax. Maps continuous events to SymbolicContinuousCallback,
discrete events to SymbolicDiscreteCallback.

---

### to_python_code

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
to_python_code(...)
```

---

### to_subscript

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:46`

**Signature:**
```julia
function to_subscript(n::Integer)
```

**Description:**
to_subscript(n::Integer) -> String

Convert integer to Unicode subscript representation.

---

### to_superscript

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/display.jl:62`

**Signature:**
```julia
function to_superscript(text::String)
```

**Description:**
to_superscript(text::String) -> String

Convert text to Unicode superscript representation.

---

### types

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
types(...)
```

---

### types

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
types(...)
```

---

### types

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
types(...)
```

---

### types

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
types(...)
```

---

### types

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
types(...)
```

---

### types

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
types(...)
```

---

### types

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
types(...)
```

---

### utilities

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
utilities(...)
```

---

### validate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
validate(...)
```

**Available in other languages:**
- [Typescript](typescript.md#validate)

---

### validate

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:151`

**Signature:**
```julia
function validate(file::EsmFile)::ValidationResult
```

**Description:**
validate(file::EsmFile) -> ValidationResult

Complete validation combining schema, structural, and unit validation.
Returns ValidationResult with all errors and warnings.

**Available in other languages:**
- [Typescript](typescript.md#validate)

---

### validate_coupling_multi_domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:886`

**Signature:**
```julia
function validate_coupling_multi_domain(file::EsmFile, coupling_entry::CouplingEntry, path::String)::Vector{StructuralError}
```

**Description:**
validate_coupling_multi_domain(file::EsmFile, coupling_entry::CouplingEntry, path::String) -> Vector{StructuralError}

Validate coupling interface and lifting fields:
- `interface` must reference a key in `interfaces`
- `lifting` is only valid when source or target is 0D (domain is null)

---

### validate_coupling_references

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:315`

**Signature:**
```julia
function validate_coupling_references(file::EsmFile, coupling_entry::CouplingEntry, path::String)::Vector{StructuralError}
```

**Description:**
validate_coupling_references(file::EsmFile, coupling_entry::CouplingEntry, path::String) -> Vector{StructuralError}

Validate coupling references based on the specific coupling type.
Checks that systems, operators, and variable references can be resolved.

---

### validate_equation_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
validate_equation_dimensions(...)
```

---

### validate_equation_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:196`

**Signature:**
```julia
function validate_equation_dimensions(eq::Equation, var_units::Dict{String, String})::Bool
```

**Description:**
Validate that an equation is dimensionally consistent.

Checks that the left-hand side and right-hand side have the same dimensions.

---

### validate_event_consistency

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:637`

**Signature:**
```julia
function validate_event_consistency(model::Model, path::String)::Vector{StructuralError}
```

**Description:**
validate_event_consistency(model::Model, path::String) -> Vector{StructuralError}

Validate event consistency: continuous conditions are expressions,
discrete conditions produce booleans, affect variables declared,
functional affect refs valid.

---

### validate_event_references

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:469`

**Signature:**
```julia
function validate_event_references(file::EsmFile, event::EventType, path::String)::Vector{StructuralError}
```

**Description:**
validate_event_references(file::EsmFile, event::EventType, path::String) -> Vector{StructuralError}

Validate event variable references.

---

### validate_expression_references

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:276`

**Signature:**
```julia
function validate_expression_references(file::EsmFile, expr::Expr, path::String)::Vector{StructuralError}
```

**Description:**
validate_expression_references(file::EsmFile, expr::Expr, path::String) -> Vector{StructuralError}

Validate that all variable references in an expression can be resolved.

---

### validate_file_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
validate_file_dimensions(...)
```

---

### validate_file_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:301`

**Signature:**
```julia
function validate_file_dimensions(file::EsmFile)::Bool
```

**Description:**
Validate dimensions for all components in an ESM file.

Returns true if all models and reaction systems pass dimensional validation.

---

### validate_interface_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:799`

**Signature:**
```julia
function validate_interface_dimensions(file::EsmFile, iface::Interface, iface_name::String)::Vector{StructuralError}
```

**Description:**
validate_interface_dimensions(file::EsmFile, iface::Interface, iface_name::String) -> Vector{StructuralError}

Validate that dimension_mapping.shared and dimension_mapping.constraints reference
valid dimensions from the domains they belong to.

---

### validate_model_balance

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:173`

**Signature:**
```julia
function validate_model_balance(model::Model, path::String)::Vector{StructuralError}
```

**Description:**
validate_model_balance(model::Model, path::String) -> Vector{StructuralError}

Validate equation-unknown balance for a model.
Each model should have equations for all state variables.

---

### validate_model_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
validate_model_dimensions(...)
```

---

### validate_model_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:220`

**Signature:**
```julia
function validate_model_dimensions(model::Model)::Bool
```

**Description:**
Validate dimensions for all equations in a model.

Returns true if all equations are dimensionally consistent.

---

### validate_model_references

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:244`

**Signature:**
```julia
function validate_model_references(file::EsmFile, model::Model, path::String)::Vector{StructuralError}
```

**Description:**
validate_model_references(file::EsmFile, model::Model, path::String) -> Vector{StructuralError}

Validate variable references within a model.

---

### validate_multi_domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:719`

**Signature:**
```julia
function validate_multi_domain(file::EsmFile)::Vector{StructuralError}
```

**Description:**
validate_multi_domain(file::EsmFile) -> Vector{StructuralError}

Validate multi-domain consistency:
1. Model/ReactionSystem `domain` must reference a key in `domains`
2. Interface `domains` must reference valid domain names
3. Interface dimension_mapping.shared/constraints must reference valid dimensions
4. Coupling `interface` must reference a key in `interfaces`
5. `lifting` only valid when source or target is 0D (domain is null)

---

### validate_reaction_consistency

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:506`

**Signature:**
```julia
function validate_reaction_consistency(rs::ReactionSystem, path::String)::Vector{StructuralError}
```

**Description:**
validate_reaction_consistency(rs::ReactionSystem, path::String) -> Vector{StructuralError}

Validate reaction system consistency: species declared, positive stoichiometries,
no null-null reactions, rate references declared.

---

### validate_reaction_system_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
validate_reaction_system_dimensions(...)
```

---

### validate_reaction_system_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:245`

**Signature:**
```julia
function validate_reaction_system_dimensions(rxn_sys::ReactionSystem)::Bool
```

**Description:**
Validate dimensions for all reactions in a reaction system.

For reactions, validates that rate expressions have appropriate dimensions
(typically concentration/time for elementary reactions).

---

### validate_reference_integrity

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:221`

**Signature:**
```julia
function validate_reference_integrity(file::EsmFile)::Vector{StructuralError}
```

**Description:**
validate_reference_integrity(file::EsmFile) -> Vector{StructuralError}

Validate that all variable references can be resolved through the hierarchy.

---

### validate_reference_syntax

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
validate_reference_syntax(...)
```

---

### validate_reference_syntax

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:820`

**Signature:**
```julia
function validate_reference_syntax(reference::String)::Bool
```

**Description:**
validate_reference_syntax(reference::String) -> Bool

Validate that a reference string follows proper dot notation syntax.

---

### validate_schema

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
validate_schema(...)
```

---

### validate_schema

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:85`

**Signature:**
```julia
function validate_schema(data::Any)::Vector{SchemaError}
```

**Description:**
validate_schema(data::Any) -> Vector{SchemaError}

Validate data against the ESM schema.
Returns empty vector if valid, otherwise returns validation errors.
Each error contains the path, message, and keyword for debugging.

---

### validate_single_event_consistency

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:665`

**Signature:**
```julia
function validate_single_event_consistency(model::Model, event::EventType, event_path::String)::Vector{StructuralError}
```

**Description:**
validate_single_event_consistency(model::Model, event::EventType, event_path::String) -> Vector{StructuralError}

Validate consistency of a single event.

---

### validate_structural

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
validate_structural(...)
```

---

### validate_structural

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:112`

**Signature:**
```julia
function validate_structural(file::EsmFile)::Vector{StructuralError}
```

**Description:**
validate_structural(file::EsmFile) -> Vector{StructuralError}

Validate structural consistency of ESM file according to spec Section 3.2.
Checks equation-unknown balance, reference integrity, reaction consistency,
and event consistency.

---

### validation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
validation(...)
```

---

### validation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
validation(...)
```

---

### variable_exists_in_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:788`

**Signature:**
```julia
function variable_exists_in_system(system::Model, variable_name::String)::Bool
```

**Description:**
variable_exists_in_system(system, variable_name::String) -> Bool

Check if a variable exists in the given system.

---

### variable_map

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:487`

**Signature:**
```julia
function variable_map(coupled_system::MockCoupledSystem, coupling::CouplingVariableMap, file::EsmFile)
```

**Description:**
variable_map(coupled_system::MockCoupledSystem, coupling::CouplingVariableMap, file::EsmFile)

Implement variable mapping with transform operations:
1. Resolve from/to scoped references using the qualified reference system
2. Apply transform: param_to_var, identity, additive, multiplicative, conversion_factor

---

## Types

### AffectEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:85`

**Definition:**
```julia
struct AffectEquation
```

**Description:**
AffectEquation(lhs::String, rhs::Expr)

Assignment equation for discrete events.
- `lhs`: target variable name (string)
- `rhs`: expression for the new value

**Available in other languages:**
- [Python](python.md#affectequation)
- [Typescript](typescript.md#affectequation)

---

### ComponentNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:21`

**Definition:**
```julia
struct ComponentNode
```

**Description:**
Component-level node representing a model, reaction system, data loader, or operator.

**Available in other languages:**
- [Python](python.md#componentnode)
- [Typescript](typescript.md#componentnode)

---

### ConditionTrigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:113`

**Definition:**
```julia
struct ConditionTrigger <: DiscreteEventTrigger
```

**Description:**
ConditionTrigger(expression::Expr)

Trigger based on boolean condition expression.

---

### ContinuousEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:165`

**Definition:**
```julia
struct ContinuousEvent <: EventType
```

**Description:**
ContinuousEvent <: EventType

Event triggered by zero-crossing of condition expressions.

**Available in other languages:**
- [Python](python.md#continuousevent)
- [Typescript](typescript.md#continuousevent)

---

### CouplingCallback

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:411`

**Definition:**
```julia
struct CouplingCallback <: CouplingEntry
```

**Description:**
CouplingCallback <: CouplingEntry

Register a callback for simulation events.

**Available in other languages:**
- [Typescript](typescript.md#couplingcallback)

---

### CouplingCouple

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:364`

**Definition:**
```julia
struct CouplingCouple <: CouplingEntry
```

**Description:**
CouplingCouple <: CouplingEntry

Bi-directional coupling via connector equations.

**Available in other languages:**
- [Python](python.md#couplingcouple)
- [Typescript](typescript.md#couplingcouple)

---

### CouplingEdge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:33`

**Definition:**
```julia
struct CouplingEdge
```

**Description:**
Edge representing coupling between components.

**Available in other languages:**
- [Python](python.md#couplingedge)
- [Python](python.md#couplingedge)
- [Typescript](typescript.md#couplingedge)

---

### CouplingEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:425`

**Definition:**
```julia
struct CouplingEvent <: CouplingEntry
```

**Description:**
CouplingEvent <: CouplingEntry

Cross-system event involving variables from multiple coupled systems.

---

### CouplingOperatorApply

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:398`

**Definition:**
```julia
struct CouplingOperatorApply <: CouplingEntry
```

**Description:**
CouplingOperatorApply <: CouplingEntry

Register an Operator to run during simulation.

**Available in other languages:**
- [Typescript](typescript.md#couplingoperatorapply)

---

### CouplingOperatorCompose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:348`

**Definition:**
```julia
struct CouplingOperatorCompose <: CouplingEntry
```

**Description:**
CouplingOperatorCompose <: CouplingEntry

Match LHS time derivatives and add RHS terms together.

**Available in other languages:**
- [Typescript](typescript.md#couplingoperatorcompose)

---

### CouplingVariableMap

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:380`

**Definition:**
```julia
struct CouplingVariableMap <: CouplingEntry
```

**Description:**
CouplingVariableMap <: CouplingEntry

Replace a parameter in one system with a variable from another.

**Available in other languages:**
- [Typescript](typescript.md#couplingvariablemap)

---

### DataLoader

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:448`

**Definition:**
```julia
struct DataLoader
```

**Description:**
DataLoader

External data source registration (by reference).
Runtime-specific data loading functionality.

**Available in other languages:**
- [Python](python.md#dataloader)
- [Typescript](typescript.md#dataloader)

---

### DependencyEdge

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:56`

**Definition:**
```julia
struct DependencyEdge
```

**Description:**
Edge representing dependency between variables.

**Available in other languages:**
- [Python](python.md#dependencyedge)
- [Typescript](typescript.md#dependencyedge)

---

### DiscreteEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:180`

**Definition:**
```julia
struct DiscreteEvent <: EventType
```

**Description:**
DiscreteEvent <: EventType

Event triggered by discrete triggers with functional affects.

**Available in other languages:**
- [Python](python.md#discreteevent)

---

### Domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:500`

**Definition:**
```julia
struct Domain
```

**Description:**
Domain

Spatial and temporal domain specification.

**Available in other languages:**
- [Python](python.md#domain)
- [Typescript](typescript.md#domain)

---

### ESMError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:127`

**Definition:**
```julia
struct ESMError
```

**Description:**
ESMError

Comprehensive error representation with diagnostics and suggestions.

**Available in other languages:**
- [Python](python.md#esmerror)
- [Typescript](typescript.md#esmerror)

---

### Equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:69`

**Definition:**
```julia
struct Equation
```

**Description:**
Equation(lhs::Expr, rhs::Expr, _comment::Union{String,Nothing}=nothing)

Mathematical equation with left-hand side and right-hand side expressions.
Used for differential equations and algebraic constraints.
Optional _comment field provides human-readable description.

**Available in other languages:**
- [Python](python.md#equation)
- [Python](python.md#equation)
- [Typescript](typescript.md#equation)

---

### ErrorCollector

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:154`

**Definition:**
```julia
mutable struct ErrorCollector
```

**Description:**
ErrorCollector

Collects and manages errors during ESM processing.

**Available in other languages:**
- [Python](python.md#errorcollector)

---

### ErrorContext

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:86`

**Definition:**
```julia
struct ErrorContext
```

**Description:**
ErrorContext

Additional context information for errors.

**Available in other languages:**
- [Python](python.md#errorcontext)
- [Typescript](typescript.md#errorcontext)

---

### EsmFile

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:610`

**Definition:**
```julia
struct EsmFile
```

**Description:**
EsmFile

Main ESM file structure containing all components.

**Available in other languages:**
- [Python](python.md#esmfile)

---

### FixSuggestion

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:112`

**Definition:**
```julia
struct FixSuggestion
```

**Description:**
FixSuggestion

Actionable suggestion for fixing an error.

**Available in other languages:**
- [Python](python.md#fixsuggestion)
- [Typescript](typescript.md#fixsuggestion)

---

### FlattenMetadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:45`

**Definition:**
```julia
struct FlattenMetadata
```

**Description:**
FlattenMetadata

Metadata about which systems were flattened and what coupling rules were applied.

# Fields
- `source_systems::Vector{String}`: names of all systems that were flattened
- `coupling_rules::Vector{String}`: human-readable descriptions of coupling rules

**Available in other languages:**
- [Python](python.md#flattenmetadata)
- [Typescript](typescript.md#flattenmetadata)

---

### FlattenedEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:30`

**Definition:**
```julia
struct FlattenedEquation
```

**Description:**
FlattenedEquation

An equation in the flattened system with namespaced variables.

# Fields
- `lhs::String`: dot-namespaced variable name (e.g., "Atmosphere.T")
- `rhs::String`: expression string with namespaced references
- `source_system::String`: name of the system this equation originated from

**Available in other languages:**
- [Python](python.md#flattenedequation)
- [Typescript](typescript.md#flattenedequation)

---

### FlattenedSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:64`

**Definition:**
```julia
struct FlattenedSystem
```

**Description:**
FlattenedSystem

A coupled system flattened into a single system with dot-namespaced variables.
All variables from individual models and reaction systems are unified into a single
namespace using "SystemName.variable" dot notation.

# Fields
- `state_variables::Vector{String}`: all state variables with system prefixes
- `parameters::Vector{String}`: all parameters with system prefixes
- `variables::Dict{String, String}`: map from namespaced variable name to its type ("state", "parameter", "observed", "species")
- `equations::Vector{FlattenedEquation}`: all equations with namespaced references
- `metadata::FlattenMetadata`: provenance information about the flattening

**Available in other languages:**
- [Python](python.md#flattenedsystem)
- [Typescript](typescript.md#flattenedsystem)

---

### FunctionalAffect

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:146`

**Definition:**
```julia
struct FunctionalAffect
```

**Description:**
FunctionalAffect

Functional affect for discrete events.

**Available in other languages:**
- [Python](python.md#functionalaffect)
- [Typescript](typescript.md#functionalaffect)

---

### Graph

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:13`

**Definition:**
```julia
struct Graph{N, E}
```

**Description:**
Generic graph structure with nodes and edges.

**Available in other languages:**
- [Python](python.md#graph)
- [Typescript](typescript.md#graph)

---

### Interface

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:515`

**Definition:**
```julia
struct Interface
```

**Description:**
Interface

Defines the geometric relationship between two domains of potentially different
dimensionality. Specifies shared dimensions, constraints on non-shared dimensions,
and regridding strategy.

---

### Metadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:583`

**Definition:**
```julia
struct Metadata
```

**Description:**
Metadata

Authorship, provenance, and description metadata.

**Available in other languages:**
- [Python](python.md#metadata)
- [Typescript](typescript.md#metadata)

---

### MockCatalystSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/catalyst.jl:292`

**Definition:**
```julia
struct MockCatalystSystem
```

**Description:**
MockCatalystSystem

Mock Catalyst system for testing and fallback when Catalyst.jl is unavailable.
Preserves all structural information from the ESM ReactionSystem.

---

### MockCoupledSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/coupled.jl:31`

**Definition:**
```julia
mutable struct MockCoupledSystem
```

**Description:**
MockCoupledSystem

Mock implementation of EarthSciMLBase.CoupledSystem for demonstration.
This would be replaced with real EarthSciMLBase integration.

---

### Model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:235`

**Definition:**
```julia
struct Model
```

**Description:**
Model

ODE-based model component containing variables, equations, and optional subsystems.
Supports hierarchical composition through subsystems.

**Available in other languages:**
- [Python](python.md#model)
- [Typescript](typescript.md#model)

---

### ModelVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:213`

**Definition:**
```julia
struct ModelVariable
```

**Description:**
ModelVariable

Structure defining a model variable with its type, default value, and optional expression.

**Available in other languages:**
- [Python](python.md#modelvariable)
- [Typescript](typescript.md#modelvariable)

---

### NumExpr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:25`

**Definition:**
```julia
struct NumExpr <: Expr
```

**Description:**
NumExpr(value::Float64)

Numeric literal expression containing a floating-point value.

---

### OpExpr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:47`

**Definition:**
```julia
struct OpExpr <: Expr
```

**Description:**
OpExpr(op::String, args::Vector{Expr}, wrt::Union{String,Nothing}, dim::Union{String,Nothing})

Operator expression node containing:
- `op`: operator name (e.g., "+", "*", "log", "D")
- `args`: vector of argument expressions
- `wrt`: variable name for differentiation (optional)
- `dim`: dimension for spatial operators (optional)

---

### Operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:474`

**Definition:**
```julia
struct Operator
```

**Description:**
Operator

Registered runtime operator (by reference).
Platform-specific computational kernels and operations.

**Available in other languages:**
- [Python](python.md#operator)
- [Typescript](typescript.md#operator)

---

### Parameter

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:303`

**Definition:**
```julia
struct Parameter
```

**Description:**
Parameter

Model parameter with name, default value, and optional metadata.

**Available in other languages:**
- [Python](python.md#parameter)
- [Typescript](typescript.md#parameter)

---

### ParseError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:17`

**Definition:**
```julia
struct ParseError <: Exception
```

**Description:**
ParseError

Exception thrown when JSON parsing fails.

---

### PerformanceProfiler

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/error_handling.jl:275`

**Definition:**
```julia
mutable struct PerformanceProfiler
```

**Description:**
PerformanceProfiler

Performance profiling tool for ESM operations.

---

### PeriodicTrigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:124`

**Definition:**
```julia
struct PeriodicTrigger <: DiscreteEventTrigger
```

**Description:**
PeriodicTrigger(period::Float64, phase::Float64)

Trigger that fires periodically.
- `period`: time interval between triggers
- `phase`: time offset for first trigger

---

### PresetTimesTrigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:137`

**Definition:**
```julia
struct PresetTimesTrigger <: DiscreteEventTrigger
```

**Description:**
PresetTimesTrigger(times::Vector{Float64})

Trigger that fires at preset times.

---

### QualifiedReferenceError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:643`

**Definition:**
```julia
struct QualifiedReferenceError <: Exception
```

**Description:**
QualifiedReferenceError

Exception thrown when qualified reference resolution fails.
Contains detailed error information.

---

### Reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:545`

**Definition:**
```julia
struct Reaction
```

**Description:**
Reaction

Chemical reaction with substrates, products, and rate expression.

**Available in other languages:**
- [Python](python.md#reaction)
- [Typescript](typescript.md#reaction)

---

### ReactionSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:565`

**Definition:**
```julia
struct ReactionSystem
```

**Description:**
ReactionSystem

Collection of chemical reactions with associated species, supporting hierarchical composition.

**Available in other languages:**
- [Python](python.md#reactionsystem)
- [Typescript](typescript.md#reactionsystem)

---

### Reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:325`

**Definition:**
```julia
struct Reference
```

**Description:**
Reference

Academic citation or data source reference.

**Available in other languages:**
- [Python](python.md#reference)
- [Typescript](typescript.md#reference)

---

### ReferenceResolution

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:655`

**Definition:**
```julia
struct ReferenceResolution
```

**Description:**
ReferenceResolution

Result of qualified reference resolution containing the resolved variable
and its location information.

---

### SchemaError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:16`

**Definition:**
```julia
struct SchemaError
```

**Description:**
SchemaError

Represents a validation error with detailed information.
Contains path, message, and keyword from JSON Schema validation.

**Available in other languages:**
- [Typescript](typescript.md#schemaerror)

---

### SchemaValidationError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:57`

**Definition:**
```julia
struct SchemaValidationError <: Exception
```

**Description:**
SchemaValidationError

Exception thrown when schema validation fails.
Contains detailed error information including paths and messages.

**Available in other languages:**
- [Python](python.md#schemavalidationerror)

---

### Species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:287`

**Definition:**
```julia
struct Species
```

**Description:**
Species

Chemical species definition with name and optional properties.

**Available in other languages:**
- [Python](python.md#species)
- [Typescript](typescript.md#species)

---

### StoichiometryEntry

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:532`

**Definition:**
```julia
struct StoichiometryEntry
```

**Description:**
StoichiometryEntry

A species with its stoichiometric coefficient in a reaction.

**Available in other languages:**
- [Typescript](typescript.md#stoichiometryentry)

---

### StructuralError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:28`

**Definition:**
```julia
struct StructuralError
```

**Description:**
StructuralError

Represents a structural validation error with detailed information.
Contains path, message, and error type for structural issues.

**Available in other languages:**
- [Typescript](typescript.md#structuralerror)

---

### SubsystemRefError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:757`

**Definition:**
```julia
struct SubsystemRefError <: Exception
```

**Description:**
SubsystemRefError

Exception thrown when subsystem reference resolution fails.

**Available in other languages:**
- [Python](python.md#subsystemreferror)

---

### UnboundVariableError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/expression.jl:152`

**Definition:**
```julia
struct UnboundVariableError <: Exception
```

**Description:**
UnboundVariableError

Exception thrown when trying to evaluate an expression with unbound variables.

---

### ValidationResult

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:40`

**Definition:**
```julia
struct ValidationResult
```

**Description:**
ValidationResult

Combined validation result containing schema errors, structural errors,
unit warnings, and overall validation status.

**Available in other languages:**
- [Python](python.md#validationresult)
- [Typescript](typescript.md#validationresult)

---

### VarExpr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:34`

**Definition:**
```julia
struct VarExpr <: Expr
```

**Description:**
VarExpr(name::String)

Variable or parameter reference expression containing a name string.

---

### VariableNode

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/graph.jl:46`

**Definition:**
```julia
struct VariableNode
```

**Description:**
Variable-level node for expression graphs.

**Available in other languages:**
- [Python](python.md#variablenode)
- [Typescript](typescript.md#variablenode)

---

