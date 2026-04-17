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

### ConflictingDerivativeError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
ConflictingDerivativeError(...)
```

**Available in other languages:**
- [Python](python.md#conflictingderivativeerror)

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

### CyclicPromotionError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
CyclicPromotionError(...)
```

**Available in other languages:**
- [Python](python.md#cyclicpromotionerror)

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

### DataLoaderRegridding

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DataLoaderRegridding(...)
```

**Available in other languages:**
- [Python](python.md#dataloaderregridding)
- [Typescript](typescript.md#dataloaderregridding)

---

### DataLoaderSource

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DataLoaderSource(...)
```

**Available in other languages:**
- [Python](python.md#dataloadersource)
- [Typescript](typescript.md#dataloadersource)

---

### DataLoaderSpatial

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DataLoaderSpatial(...)
```

**Available in other languages:**
- [Python](python.md#dataloaderspatial)
- [Typescript](typescript.md#dataloaderspatial)

---

### DataLoaderTemporal

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DataLoaderTemporal(...)
```

**Available in other languages:**
- [Python](python.md#dataloadertemporal)
- [Typescript](typescript.md#dataloadertemporal)

---

### DataLoaderVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DataLoaderVariable(...)
```

**Available in other languages:**
- [Python](python.md#dataloadervariable)
- [Typescript](typescript.md#dataloadervariable)

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

### DimensionPromotionError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DimensionPromotionError(...)
```

**Available in other languages:**
- [Python](python.md#dimensionpromotionerror)

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

### DomainExtentMismatchError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DomainExtentMismatchError(...)
```

**Available in other languages:**
- [Python](python.md#domainextentmismatcherror)

---

### DomainUnitMismatchError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
DomainUnitMismatchError(...)
```

**Available in other languages:**
- [Python](python.md#domainunitmismatcherror)

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

### Flatten

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Flatten(...)
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

**Available in other languages:**
- [Typescript](typescript.md#interface)

---

### JSON

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
JSON(...)
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

### Mock

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
Mock(...)
```

---

### MockCatalystSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
MockCatalystSystem(...)
```

---

### MockCatalystSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mock_systems.jl:294`

**Signature:**
```julia
function MockCatalystSystem(rsys::ReactionSystem;
```

**Description:**
MockCatalystSystem(rsys::ReactionSystem; name=:anonymous)

Build a `MockCatalystSystem` snapshot from an ESM `ReactionSystem`.

---

### MockMTKSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
MockMTKSystem(...)
```

---

### MockMTKSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mock_systems.jl:171`

**Signature:**
```julia
function MockMTKSystem(flat::FlattenedSystem;
```

**Description:**
MockMTKSystem(flat::FlattenedSystem; name=:anonymous)

Construct a `MockMTKSystem` from a `FlattenedSystem`. Errors with a clear
redirect to `MockPDESystem` when the flattened system has spatial
independent variables (i.e. is actually a PDE).

---

### MockMTKSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mock_systems.jl:210`

**Signature:**
```julia
function MockMTKSystem(model::Model;
```

**Description:**
MockMTKSystem(model::Model; name=:anonymous)

Convenience constructor: flatten the model first, then build the
`MockMTKSystem` from the resulting `FlattenedSystem`.

---

### MockPDESystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
MockPDESystem(...)
```

---

### MockPDESystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mock_systems.jl:227`

**Signature:**
```julia
function MockPDESystem(flat::FlattenedSystem;
```

**Description:**
MockPDESystem(flat::FlattenedSystem; name=:anonymous)

Construct a `MockPDESystem` from a `FlattenedSystem`. Errors with a clear
redirect to `MockMTKSystem` when the flattened system is a pure ODE
(i.e. has only `:t` as its independent variable).

---

### MockPDESystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mock_systems.jl:279`

**Signature:**
```julia
function MockPDESystem(model::Model;
```

**Description:**
MockPDESystem(model::Model; name=:anonymous)

Convenience constructor: flatten the model first, then build the
`MockPDESystem` from the resulting `FlattenedSystem`.

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:1137`

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

### SliceOutOfDomainError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
SliceOutOfDomainError(...)
```

**Available in other languages:**
- [Python](python.md#sliceoutofdomainerror)

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

### UnmappedDomainError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
UnmappedDomainError(...)
```

**Available in other languages:**
- [Python](python.md#unmappeddomainerror)

---

### UnsupportedMappingError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
UnsupportedMappingError(...)
```

**Available in other languages:**
- [Python](python.md#unsupportedmappingerror)

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

### _apply_couple!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:970`

**Signature:**
```julia
function _apply_couple!(equations::Vector{Equation},
```

**Description:**
Apply a `CouplingCouple` entry: attach the connector equations to the
flattened equation list. The connector.equations field may contain full
equation structures; we accept both raw Equation objects and dict-shaped
connector entries.

---

### _apply_operator_compose!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:820`

**Signature:**
```julia
function _apply_operator_compose!(equations::Vector{Equation},
```

**Description:**
Apply a `CouplingOperatorCompose` entry: for each equation LHS dependent
variable (with `translate` and `_var` placeholder expansion), find matching
equations across the listed systems and sum their RHS terms. In the flattened
representation, "matching" means "has the same namespaced dependent variable".

---

### _apply_variable_map!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:1011`

**Signature:**
```julia
function _apply_variable_map!(equations::Vector{Equation},
```

**Description:**
Apply a `CouplingVariableMap` entry: substitute the `to` parameter/variable
with the `from` variable in every flattened equation. For `param_to_var` and
`conversion_factor`, also promote `to` out of the parameters map.

---

### _canonical_ref

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1217`

**Signature:**
```julia
function _canonical_ref(ref::String, base_path::String)::String
```

**Description:**
_canonical_ref(ref::String, base_path::String) -> String

Produce a canonical key for a reference, used for cycle detection.
URLs are returned as-is; local paths are resolved to absolute paths.

---

### _check_coupling_domain_coverage!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:708`

**Signature:**
```julia
function _check_coupling_domain_coverage!(file::EsmFile)
```

**Description:**
For every coupling entry that references two or more systems (`operator_compose`,
`couple`), raise `UnmappedDomainError` if any pair of referenced systems lives
on distinct, non-null domains and no declared `Interface` covers both domains.

§4.7.6: "Any other hybrid coupling (N-D ↔ M-D with N ≠ M, or different grids
of the same dimensionality) requires an explicit Interface in the file's
interfaces section; its absence raises `UnmappedDomainError`."

---

### _check_interfaces!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:631`

**Signature:**
```julia
function _check_interfaces!(file::EsmFile)
```

**Description:**
Validate that every declared `Interface` names a dimension mapping and
regridding strategy that the Julia flatten pipeline actually implements.

§4.7.6 defines five canonical mapping types: `broadcast`, `identity`, `slice`,
`project`, `regrid`. The Julia library's flatten pipeline currently wires only
`broadcast` and `identity` (the Core-tier minimum). Interfaces that declare
`slice` or `project` raise `DimensionPromotionError`; interfaces that declare
a regridding method outside the supported set raise `UnsupportedMappingError`.

---

### _check_variable_map_units!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:741`

**Signature:**
```julia
function _check_variable_map_units!(file::EsmFile)
```

**Description:**
Walk every `variable_map` coupling entry with `transform == "identity"` and
raise `DomainUnitMismatchError` when the source and target variables carry
non-empty, declared-different units. `param_to_var` and `conversion_factor`
transforms are exempt: `conversion_factor` declares the conversion explicitly;
`param_to_var` replaces a parameter with a variable and does not imply unit
equivalence at the mapping site (units are still validated elsewhere).

---

### _collect_model!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:428`

**Signature:**
```julia
function _collect_model!(states::OrderedDict{String, ModelVariable},
```

**Description:**
Collect a Model's variables and equations into the flattener accumulators,
recursing through subsystems. All names are rewritten to `prefix.local_name`.

---

### _collect_reaction_system!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:500`

**Signature:**
```julia
function _collect_reaction_system!(states::OrderedDict{String, ModelVariable},
```

**Description:**
Lower a ReactionSystem into the flattener accumulators. Species become state
variables, rate constants become parameters, and reactions are converted to
ODE equations via `lower_reactions_to_equations`. Both species and equation
variables are then namespaced by `prefix`.

---

### _collect_system_domains

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:666`

**Signature:**
```julia
function _collect_system_domains(file::EsmFile)::Dict{String, String}
```

**Description:**
Build a mapping `system_name => domain_name` from a file's models and
reaction systems. Systems without a declared domain are omitted.

---

### _expr_to_string

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mock_systems.jl:131`

**Signature:**
```julia
function _expr_to_string(expr::Expr)
```

**Description:**
_expr_to_string(expr::Expr) -> String

Render an ESM Expr tree as a readable string. Shared helper for mock
system equation rendering.

---

### _find_conflicting_derivatives

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:562`

**Signature:**
```julia
function _find_conflicting_derivatives(file::EsmFile)::Vector{String}
```

**Description:**
_find_conflicting_derivatives(file) -> Vector{String}

Return the sorted list of fully-qualified species names that appear both as
the LHS dependent variable of an explicit `D(X, t) = ...` equation in any
`models[*]` (including subsystems) AND as a substrate or product of a
reaction in any `reaction_systems[*]` (after namespacing).

Used by `flatten` to throw `ConflictingDerivativeError` before any lowering,
and by `validate_structural` to catch the same class of error at load time.

---

### _interface_covers

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:689`

**Signature:**
```julia
function _interface_covers(file::EsmFile, d_a::String, d_b::String)::Bool
```

**Description:**
True if `file.interfaces` contains an Interface whose `domains` vector covers
both `d_a` and `d_b` (order-insensitive).

---

### _load_local_ref

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1230`

**Signature:**
```julia
function _load_local_ref(ref::String, base_path::String, visited::Set{String})::EsmFile
```

**Description:**
_load_local_ref(ref::String, base_path::String, visited::Set{String}) -> EsmFile

Load a locally referenced ESM file.

---

### _load_ref

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1187`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1255`

**Signature:**
```julia
function _load_remote_ref(ref::String)::EsmFile
```

**Description:**
_load_remote_ref(ref::String) -> EsmFile

Load a remotely referenced ESM file from a URL.
Uses the Downloads stdlib to fetch the content.

---

### _lookup_variable_units

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:761`

**Signature:**
```julia
function _lookup_variable_units(file::EsmFile, qualified::String)::Union{String, Nothing}
```

**Description:**
Look up a dot-qualified variable's declared units across models, subsystems,
and reaction systems (species + parameters). Returns `nothing` when the
variable is missing or carries no declared units.

---

### _pde_independent_vars

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mock_systems.jl:120`

**Signature:**
```julia
function _pde_independent_vars(flat::FlattenedSystem)
```

**Description:**
_pde_independent_vars(flat::FlattenedSystem) -> Bool

Return true when the flattened system has spatial independent variables
(i.e. needs a PDESystem rather than an ODESystem). A FlattenedSystem with
`[:t]` only is a pure ODE; anything else is a PDE.

---

### _resolve_model_refs!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1156`

**Signature:**
```julia
function _resolve_model_refs!(models_dict::Dict{String,Model}, name::String,
```

**Description:**
_resolve_model_refs!(models_dict, name, model, base_path, visited)

Recursively resolve subsystem references within a Model's subsystems.

---

### _resolve_reaction_system_refs!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1169`

**Signature:**
```julia
function _resolve_reaction_system_refs!(rsys_dict::Dict{String,ReactionSystem}, name::String,
```

**Description:**
_resolve_reaction_system_refs!(rsys_dict, name, rsys, base_path, visited)

Recursively resolve subsystem references within a ReactionSystem's subsystems.

---

### _resolve_refs_in_file!

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1135`

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

### coerce_affect_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:573`

**Signature:**
```julia
function coerce_affect_equation(data::Any)::AffectEquation
```

**Description:**
coerce_affect_equation(data::Any) -> AffectEquation

Coerce JSON data into AffectEquation type.

---

### coerce_assertion

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:394`

**Signature:**
```julia
function coerce_assertion(data::Any)::Assertion
```

**Description:**
coerce_assertion(data::Any) -> Assertion

Parse a schema `Assertion` object.

---

### coerce_callback

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:942`

**Signature:**
```julia
function coerce_callback(data::AbstractDict)::CouplingCallback
```

**Description:**
coerce_callback(data::AbstractDict) -> CouplingCallback

Parse callback coupling entry.

---

### coerce_continuous_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:548`

**Signature:**
```julia
function coerce_continuous_event(data::Any)::ContinuousEvent
```

**Description:**
coerce_continuous_event(data::Any) -> ContinuousEvent

Coerce JSON data specifically into ContinuousEvent.

Handles optional schema fields (affect_neg, root_find, name, discrete_parameters)
by ignoring them — the current Julia ContinuousEvent type does not model them,
but their presence must not cause load to fail.

---

### coerce_couple

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:862`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:808`

**Signature:**
```julia
function coerce_coupling_entry(data::Any)::CouplingEntry
```

**Description:**
coerce_coupling_entry(data::Any) -> CouplingEntry

Coerce JSON data into concrete CouplingEntry subtype based on the 'type' field.

---

### coerce_data_loader

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:754`

**Signature:**
```julia
function coerce_data_loader(data::Any)::DataLoader
```

**Description:**
coerce_data_loader(data::Any) -> DataLoader

Coerce JSON data into the STAC-like DataLoader type.

---

### coerce_data_loader_regridding

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:743`

**Signature:**
```julia
function coerce_data_loader_regridding(data::Any)::DataLoaderRegridding
```

**Description:**
coerce_data_loader_regridding(data::Any) -> DataLoaderRegridding

---

### coerce_data_loader_source

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:675`

**Signature:**
```julia
function coerce_data_loader_source(data::Any)::DataLoaderSource
```

**Description:**
coerce_data_loader_source(data::Any) -> DataLoaderSource

Coerce JSON data into a DataLoaderSource.

---

### coerce_data_loader_spatial

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:705`

**Signature:**
```julia
function coerce_data_loader_spatial(data::Any)::DataLoaderSpatial
```

**Description:**
coerce_data_loader_spatial(data::Any) -> DataLoaderSpatial

---

### coerce_data_loader_temporal

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:685`

**Signature:**
```julia
function coerce_data_loader_temporal(data::Any)::DataLoaderTemporal
```

**Description:**
coerce_data_loader_temporal(data::Any) -> DataLoaderTemporal

---

### coerce_data_loader_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:723`

**Signature:**
```julia
function coerce_data_loader_variable(data::Any)::DataLoaderVariable
```

**Description:**
coerce_data_loader_variable(data::Any) -> DataLoaderVariable

---

### coerce_discrete_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:495`

**Signature:**
```julia
function coerce_discrete_event(data::Any)::DiscreteEvent
```

**Description:**
coerce_discrete_event(data::Any) -> DiscreteEvent

Coerce JSON data specifically into DiscreteEvent.

Schema: DiscreteEvent must have a trigger, and either 'affects' (array of
AffectEquation) or 'functional_affect' (a registered handler). The Julia
DiscreteEvent type stores affects as a Vector{FunctionalAffect} where each
FunctionalAffect represents an assignment (target, expression, operation).
Schema AffectEquation entries {lhs, rhs} are converted to that form with
operation="set". The schema's 'functional_affect' (handler_id + metadata) is
currently collapsed to an empty affects list — the handler cannot be executed
symbolically, but parsing does not fail.

---

### coerce_domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1024`

**Signature:**
```julia
function coerce_domain(data::Any)::Domain
```

**Description:**
coerce_domain(data::Any) -> Domain

Coerce JSON data into Domain type.

---

### coerce_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:459`

**Signature:**
```julia
function coerce_equation(data::Any)::Equation
```

**Description:**
coerce_equation(data::Any) -> Equation

Coerce JSON data into Equation type.

---

### coerce_esm_file

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:222`

**Signature:**
```julia
function coerce_esm_file(data::Any)::EsmFile
```

**Description:**
coerce_esm_file(data::Any) -> EsmFile

Coerce raw JSON data into properly typed EsmFile with custom union type handling.

---

### coerce_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:471`

**Signature:**
```julia
function coerce_event(data::Any)::EventType
```

**Description:**
coerce_event(data::Any) -> EventType

Coerce JSON data into EventType (ContinuousEvent or DiscreteEvent).

---

### coerce_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:965`

**Signature:**
```julia
function coerce_event(data::AbstractDict)::CouplingEvent
```

**Description:**
coerce_event(data::AbstractDict) -> CouplingEvent

Parse event coupling entry.

---

### coerce_functional_affect

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:584`

**Signature:**
```julia
function coerce_functional_affect(data::Any)::FunctionalAffect
```

**Description:**
coerce_functional_affect(data::Any) -> FunctionalAffect

Coerce JSON data into FunctionalAffect type.

---

### coerce_interface

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1036`

**Signature:**
```julia
function coerce_interface(data::Any)::Interface
```

**Description:**
coerce_interface(data::Any) -> Interface

Coerce JSON data into Interface type.

---

### coerce_metadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:285`

**Signature:**
```julia
function coerce_metadata(data::Any)::Metadata
```

**Description:**
coerce_metadata(data::Any) -> Metadata

Coerce JSON data into Metadata type.

---

### coerce_model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:324`

**Signature:**
```julia
function coerce_model(data::Any)::Model
```

**Description:**
coerce_model(data::Any) -> Model

Coerce JSON data into Model type.

---

### coerce_model_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:440`

**Signature:**
```julia
function coerce_model_variable(data::Any)::ModelVariable
```

**Description:**
coerce_model_variable(data::Any) -> ModelVariable

Coerce JSON data into ModelVariable type.

---

### coerce_operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:787`

**Signature:**
```julia
function coerce_operator(data::Any)::Operator
```

**Description:**
coerce_operator(data::Any) -> Operator

Coerce JSON data into Operator type.

---

### coerce_operator_apply

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:926`

**Signature:**
```julia
function coerce_operator_apply(data::AbstractDict)::CouplingOperatorApply
```

**Description:**
coerce_operator_apply(data::AbstractDict) -> CouplingOperatorApply

Parse operator_apply coupling entry.

---

### coerce_operator_compose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:837`

**Signature:**
```julia
function coerce_operator_compose(data::AbstractDict)::CouplingOperatorCompose
```

**Description:**
coerce_operator_compose(data::AbstractDict) -> CouplingOperatorCompose

Parse operator_compose coupling entry.

---

### coerce_parameter

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:661`

**Signature:**
```julia
function coerce_parameter(name::String, data::Any)::Parameter
```

**Description:**
coerce_parameter(name::String, data::Any) -> Parameter

Coerce JSON data into Parameter type with explicit name.

---

### coerce_reaction

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:627`

**Signature:**
```julia
function coerce_reaction(data::Any)::Reaction
```

**Description:**
coerce_reaction(data::Any) -> Reaction

Coerce JSON data into Reaction type.

---

### coerce_reaction_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:596`

**Signature:**
```julia
function coerce_reaction_system(data::Any)::ReactionSystem
```

**Description:**
coerce_reaction_system(data::Any) -> ReactionSystem

Coerce JSON data into ReactionSystem type.

---

### coerce_reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:310`

**Signature:**
```julia
function coerce_reference(data::Any)::Reference
```

**Description:**
coerce_reference(data::Any) -> Reference

Coerce JSON data into Reference type.

---

### coerce_species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:613`

**Signature:**
```julia
function coerce_species(name::String, data::Any)::Species
```

**Description:**
coerce_species(name::String, data::Any) -> Species

Coerce JSON data into Species type with explicit name.

---

### coerce_test

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:408`

**Signature:**
```julia
function coerce_test(data::Any)::EarthSciSerialization.Test
```

**Description:**
coerce_test(data::Any) -> Test

Parse a schema `Test` object into the Julia `Test` struct.

---

### coerce_time_span

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:383`

**Signature:**
```julia
function coerce_time_span(data::Any)::TimeSpan
```

**Description:**
coerce_time_span(data::Any) -> TimeSpan

Parse a schema `TimeSpan` object.

---

### coerce_tolerance

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:372`

**Signature:**
```julia
function coerce_tolerance(data::Any)::Tolerance
```

**Description:**
coerce_tolerance(data::Any) -> Tolerance

Parse a schema `Tolerance` object into the Julia `Tolerance` struct.

---

### coerce_variable_map

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:893`

**Signature:**
```julia
function coerce_variable_map(data::AbstractDict)::CouplingVariableMap
```

**Description:**
coerce_variable_map(data::AbstractDict) -> CouplingVariableMap

Parse variable_map coupling entry.

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:439`

**Signature:**
```julia
function compose(file::EsmFile, system_a::String, system_b::String)::EsmFile
```

**Description:**
compose(file::EsmFile, system_a::String, system_b::String) -> EsmFile

Convenience function to create an operator_compose coupling entry linking two systems.

**Available in other languages:**
- [Typescript](typescript.md#compose)

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

### coupling

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
coupling(...)
```

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

### create_model_with_mixed_events

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:400`

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

### cross

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
cross(...)
```

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:1217`

**Signature:**
```julia
function describe_coupling_entry(entry::CouplingEntry)::String
```

**Description:**
describe_coupling_entry(entry::CouplingEntry) -> String

Produce a human-readable description of a coupling entry for the flattened
system's metadata.

---

### dict_to_stoichiometry_entries

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:1119`

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

### error

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
error(...)
```

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:519`

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

### fallbacks

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
fallbacks(...)
```

---

### find_subsystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:1009`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:979`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:1095`

**Signature:**
```julia
function flatten(file::EsmFile)::FlattenedSystem
```

**Description:**
flatten(file::EsmFile) -> FlattenedSystem

Flatten the coupled systems in `file` into a single symbolic representation
per spec §4.7.5 (+ §4.7.6 for hybrid dimension-promoted cases).

Throws `ConflictingDerivativeError` if any species is both the LHS of an
explicit `D(X, t) = ...` equation and a reactant/product of a reaction — such
a system is over-determined.

**Available in other languages:**
- [Typescript](typescript.md#flatten)

---

### flatten

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:1190`

**Signature:**
```julia
function flatten(model::Model; name::String="anonymous")::FlattenedSystem
```

**Description:**
flatten(model::Model; name::String="anonymous") -> FlattenedSystem

Convenience: wrap a single Model in a synthetic EsmFile (with a default system
name) and run the full flattener. This is the call path used by
`ModelingToolkit.System(::Model)` in the Julia extension (see gt-fpw).

**Available in other languages:**
- [Typescript](typescript.md#flatten)

---

### flatten

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:1201`

**Signature:**
```julia
function flatten(rsys::ReactionSystem; name::String="anonymous")::FlattenedSystem
```

**Description:**
flatten(rsys::ReactionSystem; name::String="anonymous") -> FlattenedSystem

Convenience: wrap a ReactionSystem in a synthetic EsmFile and flatten.

**Available in other languages:**
- [Typescript](typescript.md#flatten)

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:66`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:1167`

**Signature:**
```julia
function get_products_dict(reaction::Reaction)::Dict{String,Int}
```

**Description:**
get_products_dict(reaction::Reaction) -> Dict{String,Int}

Get products as dictionary for backward compatibility.

---

### get_reactants_dict

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:1152`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:881`

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

### has_spatial_operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:375`

**Signature:**
```julia
function has_spatial_operator(expr::EarthSciSerialization.Expr)::Bool
```

**Description:**
has_spatial_operator(expr) -> Bool

True if the expression contains any spatial operator (`grad`, `div`,
`laplacian`, or `D` with `wrt != "t"`).

---

### infer_array_shapes

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
infer_array_shapes(...)
```

---

### infer_array_shapes

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:1294`

**Signature:**
```julia
function infer_array_shapes(equations::Vector{Equation})
```

**Description:**
infer_array_shapes(equations::Vector{Equation}) -> Dict{String, Vector{UnitRange{Int}}}

Walk every `arrayop`, `makearray`, and `index` node in the equation set and
compute, for each array-shaped variable, the union of ranges observed across
all references. The result maps variable name → per-axis `UnitRange{Int}`
vector (empty for scalar variables; one entry per dimension for array
variables). Only variables that actually appear inside an array operator get
a shape — scalar variables are absent from the result dict.

Semantics:
- For a `VarExpr` appearing as the first argument of an `index` node, each
  subsequent argument is an index expression (literal int, symbolic index
  name, or affine offset like `i+1`). The range of that index determines the
  variable's length on that axis. Affine offsets widen the required range
  (e.g. `u[i-1]` and `u[i+1]` in `i in 2:9` force `u` to span `1:10`).
- For an `arrayop`, its `output_idx` and `ranges` combined define the
  iteration space. Index names with no explicit range are left for
  inference from their usages inside the body.
- Conflicts: if a variable is referenced with inconsistent dimensionality
  across equations, this function raises an `ArgumentError`.

This pass is deliberately standalone — it does not mutate `FlattenedSystem`.
It is called at MTK build time from `ext/EarthSciSerializationMTKExt.jl` so
scalar-only callers pay no cost.

---

### infer_variable_units

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
infer_variable_units(...)
```

---

### infer_variable_units

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:347`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:1090`

**Signature:**
```julia
function is_valid_identifier(name::String)::Bool
```

**Description:**
is_valid_identifier(name::String) -> Bool

Check if a string is a valid identifier (letters, numbers, underscores, no leading digit).

---

### language

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
language(...)
```

---

### lhs_dependent_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:360`

**Signature:**
```julia
function lhs_dependent_variable(expr::EarthSciSerialization.Expr)::Union{String, Nothing}
```

**Description:**
lhs_dependent_variable(expr) -> Union{String, Nothing}

Extract the dependent variable name from an equation LHS. For `D(x, t)`, returns
`"x"`. For a bare `VarExpr("x")`, returns `"x"`. Otherwise returns `nothing`.

---

### load

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
load(...)
```

**Available in other languages:**
- [Typescript](typescript.md#load)

---

### load

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1052`

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
- [Typescript](typescript.md#load)

---

### load

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1067`

**Signature:**
```julia
function load(io::IO)::EsmFile
```

**Description:**
load(io::IO) -> EsmFile

Load and parse an ESM file from an IO stream.

**Available in other languages:**
- [Typescript](typescript.md#load)

---

### lower_reactions_to_equations

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
lower_reactions_to_equations(...)
```

---

### lower_reactions_to_equations

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:244`

**Signature:**
```julia
function lower_reactions_to_equations(reactions::Vector{Reaction},
```

**Description:**
lower_reactions_to_equations(reactions, species, domain=nothing) -> Vector{Equation}

Produce the ODE equations induced by a set of reactions using standard
mass-action kinetics: `d[X]/dt = Σ (stoich_ij * rate_j)`.

Shared by `derive_odes` (reaction → Model) and `flatten` (EsmFile → FlattenedSystem)
so there is exactly one place that turns stoichiometry into equations.

On a 0D domain (`domain === nothing`), the LHS is `D(X, t)`. On a PDE domain,
the LHS is still `D(X, t)` symbolically — dimension promotion (§4.7.6) is
applied by `flatten`, not here. The resulting equation lives on the caller's
domain; spatial operators are added downstream when coupling adds them.

---

### map_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
map_variable(...)
```

---

### map_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:451`

**Signature:**
```julia
function map_variable(file::EsmFile, from::String, to::String; transform::String="identity")::EsmFile
```

**Description:**
map_variable(file::EsmFile, from::String, to::String; transform::String="identity") -> EsmFile

Convenience function to create a variable_map coupling entry that forwards a
variable reference `from` into `to`. `transform` names the transform function
(e.g. `"identity"`, `"affine"`).

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:466`

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

### namespace_expr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:318`

**Signature:**
```julia
function namespace_expr(expr::NumExpr, prefix::String, local_names::Set{String})::EarthSciSerialization.Expr
```

**Description:**
namespace_expr(expr, prefix, local_names) -> Expr

Return a new Expr tree with every VarExpr referencing a name in `local_names`
rewritten as `"<prefix>.<name>"`. Variables whose name already contains a dot
(already qualified) are left unchanged. Numeric literals are unchanged.

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

### no

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
no(...)
```

---

### no

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
no(...)
```

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

### parity

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
parity(...)
```

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

### parse_model_variable_type

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:126`

**Signature:**
```julia
function parse_model_variable_type(data::String)::ModelVariableType
```

**Description:**
parse_model_variable_type(data::String) -> ModelVariableType

Parse string into ModelVariableType enum.

---

### parse_trigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:151`

**Signature:**
```julia
function parse_trigger(data)::DiscreteEventTrigger
```

**Description:**
parse_trigger(data) -> DiscreteEventTrigger

Parse JSON data into a DiscreteEventTrigger based on the schema discriminator.

Accepts Dict or JSON3.Object. Uses the "type" field (preferred, per current schema)
with fallback to field-based discrimination for backward compatibility.

Schema-defined variants:
- {"type": "condition", "expression": ...} -> ConditionTrigger
- {"type": "periodic", "interval": ..., "initial_offset": ...} -> PeriodicTrigger
- {"type": "preset_times", "times": [...]} -> PresetTimesTrigger

---

### parse_units

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
parse_units(...)
```

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/edit.jl:412`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:924`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1125`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:882`

**Signature:**
```julia
function save(file::EsmFile, path::String)
```

**Description:**
save(file::EsmFile, path::String)
    save(path::String, file::EsmFile)

Save an EsmFile object to a JSON file at the specified path.
Accepts either argument order for ergonomics (file, path) or (path, file).

**Available in other languages:**
- [Typescript](typescript.md#save)

---

### save

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:895`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:179`

**Signature:**
```julia
function serialize_affect_equation(affect::AffectEquation)::Dict{String,Any}
```

**Description:**
serialize_affect_equation(affect::AffectEquation) -> Dict{String,Any}

Serialize AffectEquation to JSON-compatible format.

---

### serialize_assertion

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:307`

**Signature:**
```julia
function serialize_assertion(a::Assertion)::Dict{String,Any}
```

**Description:**
serialize_assertion(a::Assertion) -> Dict{String,Any}

---

### serialize_callback

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:699`

**Signature:**
```julia
function serialize_callback(entry::CouplingCallback)::Dict{String,Any}
```

**Description:**
serialize_callback(entry::CouplingCallback) -> Dict{String,Any}

Serialize callback coupling entry.

---

### serialize_continuous_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:163`

**Signature:**
```julia
function serialize_continuous_event(event::ContinuousEvent)::Dict{String,Any}
```

**Description:**
serialize_continuous_event(event::ContinuousEvent) -> Dict{String,Any}

Serialize ContinuousEvent to JSON-compatible format.

---

### serialize_couple

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:630`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:583`

**Signature:**
```julia
function serialize_coupling_entry(entry::CouplingEntry)::Dict{String,Any}
```

**Description:**
serialize_coupling_entry(entry::CouplingEntry) -> Dict{String,Any}

Serialize CouplingEntry to JSON-compatible format based on concrete type.

---

### serialize_data_loader

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:527`

**Signature:**
```julia
function serialize_data_loader(loader::DataLoader)::Dict{String,Any}
```

**Description:**
serialize_data_loader(loader::DataLoader) -> Dict{String,Any}

Serialize DataLoader to JSON-compatible format (STAC-like shape).

---

### serialize_data_loader_regridding

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:515`

**Signature:**
```julia
function serialize_data_loader_regridding(r::DataLoaderRegridding)::Dict{String,Any}
```

**Description:**
serialize_data_loader_regridding(r::DataLoaderRegridding) -> Dict{String,Any}

---

### serialize_data_loader_source

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:459`

**Signature:**
```julia
function serialize_data_loader_source(src::DataLoaderSource)::Dict{String,Any}
```

**Description:**
serialize_data_loader_source(src::DataLoaderSource) -> Dict{String,Any}

---

### serialize_data_loader_spatial

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:484`

**Signature:**
```julia
function serialize_data_loader_spatial(s::DataLoaderSpatial)::Dict{String,Any}
```

**Description:**
serialize_data_loader_spatial(s::DataLoaderSpatial) -> Dict{String,Any}

---

### serialize_data_loader_temporal

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:470`

**Signature:**
```julia
function serialize_data_loader_temporal(t::DataLoaderTemporal)::Dict{String,Any}
```

**Description:**
serialize_data_loader_temporal(t::DataLoaderTemporal) -> Dict{String,Any}

---

### serialize_data_loader_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:498`

**Signature:**
```julia
function serialize_data_loader_variable(v::DataLoaderVariable)::Dict{String,Any}
```

**Description:**
serialize_data_loader_variable(v::DataLoaderVariable) -> Dict{String,Any}

---

### serialize_discrete_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:144`

**Signature:**
```julia
function serialize_discrete_event(event::DiscreteEvent)::Dict{String,Any}
```

**Description:**
serialize_discrete_event(event::DiscreteEvent) -> Dict{String,Any}

Serialize DiscreteEvent to the schema shape. Julia stores event affects as a
Vector{FunctionalAffect}(target, expression, operation) for legacy reasons,
but the schema requires discrete_events[].affects to be an array of
AffectEquation objects ({lhs, rhs}). Emit the schema shape.

---

### serialize_discrete_event_trigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:110`

**Signature:**
```julia
function serialize_discrete_event_trigger(trigger::DiscreteEventTrigger)::Dict{String,Any}
```

**Description:**
serialize_discrete_event_trigger(trigger::DiscreteEventTrigger) -> Dict{String,Any}

Alias for serialize_trigger for backward compatibility.

---

### serialize_domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:809`

**Signature:**
```julia
function serialize_domain(domain::Domain)::Dict{String,Any}
```

**Description:**
serialize_domain(domain::Domain) -> Dict{String,Any}

Serialize Domain to JSON-compatible format.

---

### serialize_equation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:231`

**Signature:**
```julia
function serialize_equation(eq::Equation)::Dict{String,Any}
```

**Description:**
serialize_equation(eq::Equation) -> Dict{String,Any}

Serialize Equation to JSON-compatible format.

---

### serialize_esm_file

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:844`

**Signature:**
```julia
function serialize_esm_file(file::EsmFile)::Dict{String,Any}
```

**Description:**
serialize_esm_file(file::EsmFile) -> Dict{String,Any}

Serialize EsmFile to JSON-compatible format.

---

### serialize_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:119`

**Signature:**
```julia
function serialize_event(event::EventType)::Dict{String,Any}
```

**Description:**
serialize_event(event::EventType) -> Dict{String,Any}

Serialize EventType to JSON-compatible format.

---

### serialize_event

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:717`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:191`

**Signature:**
```julia
function serialize_functional_affect(affect::FunctionalAffect)::Dict{String,Any}
```

**Description:**
serialize_functional_affect(affect::FunctionalAffect) -> Dict{String,Any}

Serialize FunctionalAffect to JSON-compatible format.

---

### serialize_interface

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:825`

**Signature:**
```julia
function serialize_interface(iface::Interface)::Dict{String,Any}
```

**Description:**
serialize_interface(iface::Interface) -> Dict{String,Any}

Serialize Interface to JSON-compatible format.

---

### serialize_metadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:776`

**Signature:**
```julia
function serialize_metadata(metadata::Metadata)::Dict{String,Any}
```

**Description:**
serialize_metadata(metadata::Metadata) -> Dict{String,Any}

Serialize Metadata to JSON-compatible format.

---

### serialize_model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:247`

**Signature:**
```julia
function serialize_model(model::Model)::Dict{String,Any}
```

**Description:**
serialize_model(model::Model) -> Dict{String,Any}

Serialize Model to JSON-compatible format.

---

### serialize_model_variable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:207`

**Signature:**
```julia
function serialize_model_variable(var::ModelVariable)::Dict{String,Any}
```

**Description:**
serialize_model_variable(var::ModelVariable) -> Dict{String,Any}

Serialize ModelVariable to JSON-compatible format.

---

### serialize_model_variable_type

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:72`

**Signature:**
```julia
function serialize_model_variable_type(var_type::ModelVariableType)::String
```

**Description:**
serialize_model_variable_type(var_type::ModelVariableType) -> String

Serialize ModelVariableType enum to string.

---

### serialize_operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:558`

**Signature:**
```julia
function serialize_operator(op::Operator)::Dict{String,Any}
```

**Description:**
serialize_operator(op::Operator) -> Dict{String,Any}

Serialize Operator to JSON-compatible format.

---

### serialize_operator_apply

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:684`

**Signature:**
```julia
function serialize_operator_apply(entry::CouplingOperatorApply)::Dict{String,Any}
```

**Description:**
serialize_operator_apply(entry::CouplingOperatorApply) -> Dict{String,Any}

Serialize operator_apply coupling entry.

---

### serialize_operator_compose

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:606`

**Signature:**
```julia
function serialize_operator_compose(entry::CouplingOperatorCompose)::Dict{String,Any}
```

**Description:**
serialize_operator_compose(entry::CouplingOperatorCompose) -> Dict{String,Any}

Serialize operator_compose coupling entry.

---

### serialize_parameter

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:374`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:396`

**Signature:**
```julia
function serialize_reaction(reaction::Reaction)::Dict{String,Any}
```

**Description:**
serialize_reaction(reaction::Reaction) -> Dict{String,Any}

Serialize Reaction to JSON-compatible format.

---

### serialize_reaction_system

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:442`

**Signature:**
```julia
function serialize_reaction_system(rs::ReactionSystem)::Dict{String,Any}
```

**Description:**
serialize_reaction_system(rs::ReactionSystem) -> Dict{String,Any}

Serialize ReactionSystem to JSON-compatible format.

---

### serialize_reference

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:754`

**Signature:**
```julia
function serialize_reference(ref::Reference)::Dict{String,Any}
```

**Description:**
serialize_reference(ref::Reference) -> Dict{String,Any}

Serialize Reference to JSON-compatible format.

---

### serialize_species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:351`

**Signature:**
```julia
function serialize_species(species::Species)::Dict{String,Any}
```

**Description:**
serialize_species(species::Species) -> Dict{String,Any}

Serialize Species to JSON-compatible format.
Note: Species name is the key in the species dictionary, not a property of the Species object.

---

### serialize_test

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:322`

**Signature:**
```julia
function serialize_test(t::EarthSciSerialization.Test)::Dict{String,Any}
```

**Description:**
serialize_test(t::Test) -> Dict{String,Any}

---

### serialize_time_span

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:300`

**Signature:**
```julia
function serialize_time_span(span::TimeSpan)::Dict{String,Any}
```

**Description:**
serialize_time_span(span::TimeSpan) -> Dict{String,Any}

---

### serialize_tolerance

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:286`

**Signature:**
```julia
function serialize_tolerance(tol::Tolerance)::Dict{String,Any}
```

**Description:**
serialize_tolerance(tol::Tolerance) -> Dict{String,Any}

---

### serialize_trigger

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:89`

**Signature:**
```julia
function serialize_trigger(trigger::DiscreteEventTrigger)::Dict{String,Any}
```

**Description:**
serialize_trigger(trigger::DiscreteEventTrigger) -> Dict{String,Any}

Serialize DiscreteEventTrigger to JSON-compatible format.

---

### serialize_variable_map

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/serialize.jl:655`

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

### spatial_dims_in_expr

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:398`

**Signature:**
```julia
function spatial_dims_in_expr(expr::EarthSciSerialization.Expr)::Set{Symbol}
```

**Description:**
spatial_dims_in_expr(expr) -> Set{Symbol}

Collect all spatial dimension names referenced by spatial operators in `expr`.

---

### spec

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
spec(...)
```

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:1128`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:618`

**Signature:**
```julia
function system_exists_in_file(file::EsmFile, system_name::String)::Bool
```

**Description:**
system_exists_in_file(file::EsmFile, system_name::String) -> Bool

Check if a system (model, reaction_system, data_loader, or operator) exists in the ESM file.

---

### systems

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
systems(...)
```

---

### taxonomy

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
taxonomy(...)
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

### types

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/EarthSciSerialization.jl:0`

**Signature:**
```julia
types(...)
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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:163`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:898`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:327`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:211`

**Signature:**
```julia
function validate_equation_dimensions(eq::Equation, var_units::Dict{String, String})::Bool
```

**Description:**
Validate that an equation is dimensionally consistent.

Checks that the left-hand side and right-hand side have the same dimensions.

---

### validate_event_consistency

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:649`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:481`

**Signature:**
```julia
function validate_event_references(file::EsmFile, event::EventType, path::String)::Vector{StructuralError}
```

**Description:**
validate_event_references(file::EsmFile, event::EventType, path::String) -> Vector{StructuralError}

Validate event variable references.

---

### validate_expression_references

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:288`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:316`

**Signature:**
```julia
function validate_file_dimensions(file::EsmFile)::Bool
```

**Description:**
Validate dimensions for all components in an ESM file.

Returns true if all models and reaction systems pass dimensional validation.

---

### validate_interface_dimensions

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:811`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:185`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:235`

**Signature:**
```julia
function validate_model_dimensions(model::Model)::Bool
```

**Description:**
Validate dimensions for all equations in a model.

Returns true if all equations are dimensionally consistent.

---

### validate_model_references

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:256`

**Signature:**
```julia
function validate_model_references(file::EsmFile, model::Model, path::String)::Vector{StructuralError}
```

**Description:**
validate_model_references(file::EsmFile, model::Model, path::String) -> Vector{StructuralError}

Validate variable references within a model.

---

### validate_multi_domain

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:731`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:518`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/units.jl:260`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:233`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:1059`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/validate.jl:677`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:1027`

**Signature:**
```julia
function variable_exists_in_system(system::Model, variable_name::String)::Bool
```

**Description:**
variable_exists_in_system(system, variable_name::String) -> Bool

Check if a variable exists in the given system.

---

## Types

### AffectEquation

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:128`

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

### Assertion

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:302`

**Definition:**
```julia
struct Assertion
```

**Description:**
Assertion(variable::String, time::Float64, expected::Float64, tolerance::Union{Tolerance,Nothing})

A scalar `(variable, time, expected)` check used inside a `Test`.

**Available in other languages:**
- [Typescript](typescript.md#assertion)

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:156`

**Definition:**
```julia
struct ConditionTrigger <: DiscreteEventTrigger
```

**Description:**
ConditionTrigger(expression::Expr)

Trigger based on boolean condition expression.

---

### ConflictingDerivativeError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:31`

**Definition:**
```julia
struct ConflictingDerivativeError <: Exception
```

**Description:**
ConflictingDerivativeError

Raised when a species appears both as the left-hand side of an explicit
differential equation (`D(X, t) = ...`) and as a substrate or product of any
reaction in the same flattened file. Such a system is over-determined: the
reaction contribution to `d[X]/dt` would silently shadow the user's equation.

Fields:
- `species::Vector{String}`: fully-qualified (dot-namespaced) names of every
  offending species.

**Available in other languages:**
- [Python](python.md#conflictingderivativeerror)

---

### ContinuousEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:208`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:552`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:505`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:566`

**Definition:**
```julia
struct CouplingEvent <: CouplingEntry
```

**Description:**
CouplingEvent <: CouplingEntry

Cross-system event involving variables from multiple coupled systems.

---

### CouplingOperatorApply

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:539`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:489`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:521`

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

### CyclicPromotionError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:144`

**Definition:**
```julia
struct CyclicPromotionError <: Exception
```

**Description:**
CyclicPromotionError

Defined for cross-language error-name parity. Not raised by Core-tier Julia
because no promotion graph is built — reserved for a future tier upgrade that
does promotion-graph analysis. Would signal that the declared `Interface`
rules form a cycle (A promotes to B, B promotes back to A on a different
axis).

**Available in other languages:**
- [Python](python.md#cyclicpromotionerror)

---

### DataLoader

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:687`

**Definition:**
```julia
struct DataLoader
```

**Description:**
DataLoader

Generic, runtime-agnostic description of an external data source. Carries
enough structural information to locate files, map timestamps to files,
describe spatial/variable semantics, and regrid — rather than pointing at a
runtime handler. Authentication and algorithm-specific tuning are runtime-only
and not part of the schema.

Fields:
- `kind`: "grid" | "points" | "static" (structural kind; scientific role goes in `metadata.tags`)
- `source`: `DataLoaderSource` with url_template + optional mirrors
- `temporal`: optional `DataLoaderTemporal`
- `spatial`: optional `DataLoaderSpatial`
- `variables`: schema-level variable name → `DataLoaderVariable` (minimum one)
- `regridding`: optional `DataLoaderRegridding`
- `reference`: optional academic/data-source citation
- `metadata`: optional free-form map (conventionally carries a `tags` array)

**Available in other languages:**
- [Python](python.md#dataloader)
- [Typescript](typescript.md#dataloader)

---

### DataLoaderRegridding

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:660`

**Definition:**
```julia
struct DataLoaderRegridding
```

**Description:**
DataLoaderRegridding

Structural regridding configuration for a DataLoader.

**Available in other languages:**
- [Python](python.md#dataloaderregridding)
- [Typescript](typescript.md#dataloaderregridding)

---

### DataLoaderSource

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:591`

**Definition:**
```julia
struct DataLoaderSource
```

**Description:**
DataLoaderSource

File discovery configuration for a DataLoader. Describes how to locate data
files at runtime via a URL template with `{date:<strftime>}`, `{var}`,
`{sector}`, `{species}`, and custom substitutions. Optional `mirrors` list
gives ordered fallback templates.

**Available in other languages:**
- [Python](python.md#dataloadersource)
- [Typescript](typescript.md#dataloadersource)

---

### DataLoaderSpatial

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:623`

**Definition:**
```julia
struct DataLoaderSpatial
```

**Description:**
DataLoaderSpatial

Spatial grid description for a DataLoader.

**Available in other languages:**
- [Python](python.md#dataloaderspatial)
- [Typescript](typescript.md#dataloaderspatial)

---

### DataLoaderTemporal

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:604`

**Definition:**
```julia
struct DataLoaderTemporal
```

**Description:**
DataLoaderTemporal

Temporal coverage and record layout for a DataLoader.

**Available in other languages:**
- [Python](python.md#dataloadertemporal)
- [Typescript](typescript.md#dataloadertemporal)

---

### DataLoaderVariable

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:641`

**Definition:**
```julia
struct DataLoaderVariable
```

**Description:**
DataLoaderVariable

A variable exposed by a DataLoader, mapped from a source-file variable.
`unit_conversion` may be a numeric factor or an Expression AST.

**Available in other languages:**
- [Python](python.md#dataloadervariable)
- [Typescript](typescript.md#dataloadervariable)

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

### DimensionPromotionError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:48`

**Definition:**
```julia
struct DimensionPromotionError <: Exception
```

**Description:**
DimensionPromotionError

Raised during flatten when a variable or equation cannot be promoted from
its source domain to the target domain given the available `Interface` rules
(§4.7.6).

**Available in other languages:**
- [Python](python.md#dimensionpromotionerror)

---

### DiscreteEvent

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:223`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:739`

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

### DomainExtentMismatchError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:112`

**Definition:**
```julia
struct DomainExtentMismatchError <: Exception
```

**Description:**
DomainExtentMismatchError

Defined for cross-language error-name parity with the Rust `FlattenError`
taxonomy and the Python `flatten()` exception set. Would be raised when an
`identity` mapping bridges two domains whose spatial extents on a shared
independent variable disagree. The Julia flatten pipeline does not currently
perform this check, so this type is reserved and never raised by the current
implementation — it exists so consumers can catch it by name.

**Available in other languages:**
- [Python](python.md#domainextentmismatcherror)

---

### DomainUnitMismatchError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:92`

**Definition:**
```julia
struct DomainUnitMismatchError <: Exception
```

**Description:**
DomainUnitMismatchError

Raised when coupling across an `Interface` requires a unit conversion that
was not declared by the user (§4.7.6).

**Available in other languages:**
- [Python](python.md#domainunitmismatcherror)

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:112`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:849`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:170`

**Definition:**
```julia
struct FlattenMetadata
```

**Description:**
FlattenMetadata

Provenance metadata for a flattened system.

Fields:
- `source_systems::Vector{String}`: names of the component systems that were
  flattened (sorted for determinism).
- `coupling_rules_applied::Vector{String}`: human-readable summary of each
  coupling entry applied.
- `dimension_promotions_applied::Vector{NamedTuple}`: records of each dimension
  promotion — e.g. `(variable="Chem.O3", source_domain=nothing, target_domain="grid2d", kind=:broadcast)`.
- `opaque_coupling_refs::Vector{String}`: opaque runtime references recorded
  for `operator_apply` and `callback` couplings.

**Available in other languages:**
- [Python](python.md#flattenmetadata)
- [Typescript](typescript.md#flattenmetadata)

---

### FlattenedSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:214`

**Definition:**
```julia
struct FlattenedSystem
```

**Description:**
FlattenedSystem

A coupled ESM file flattened into a single symbolic representation.

All variables, parameters, and species are dot-namespaced (e.g.
`"SimpleOzone.O3"`, `"Atmosphere.Chemistry.NO2"`). Equations are real
`Equation` objects whose Expr trees reference namespaced names via `VarExpr`.
This is the canonical intermediate form consumed by MTK/PDESystem constructors
(in the Julia extension) and by cross-language code generators.

Fields:
- `independent_variables::Vector{Symbol}`: `[:t]` for pure-ODE systems, or
  `[:t, :x, :y, ...]` when spatial operators are present.
- `state_variables::OrderedDict{String, ModelVariable}`: namespaced state
  variables and (former-reaction) species.
- `parameters::OrderedDict{String, ModelVariable}`: namespaced parameters,
  minus any promoted to variables by `variable_map`.
- `observed_variables::OrderedDict{String, ModelVariable}`: namespaced
  observed variables.
- `equations::Vector{Equation}`: all equations after reaction lowering and
  coupling, with variable references rewritten to namespaced form.
- `continuous_events::Vector{ContinuousEvent}`: collected from every source
  model with references rewritten.
- `discrete_events::Vector{DiscreteEvent}`: ditto.
- `domain::Union{Domain, Nothing}`: the target domain after any dimension
  promotion (§4.7.6), or `nothing` for purely 0D systems.
- `metadata::FlattenMetadata`: provenance.

**Available in other languages:**
- [Python](python.md#flattenedsystem)
- [Typescript](typescript.md#flattenedsystem)

---

### FunctionalAffect

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:189`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:754`

**Definition:**
```julia
struct Interface
```

**Description:**
Interface

Defines the geometric relationship between two domains of potentially different
dimensionality. Specifies shared dimensions, constraints on non-shared dimensions,
and regridding strategy.

**Available in other languages:**
- [Typescript](typescript.md#interface)

---

### Metadata

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:822`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mock_systems.jl:96`

**Definition:**
```julia
struct MockCatalystSystem
```

**Description:**
MockCatalystSystem

No-Catalyst fallback for `Catalyst.ReactionSystem`. Captures the structure
of an ESM `ReactionSystem` as plain-Julia collections.

Fields:
- `name::Symbol`: system name.
- `species::Vector{String}`: species names.
- `parameters::Vector{String}`: parameter names.
- `reactions::Vector{String}`: string-rendered reactions (e.g. `"A + B → C, rate: k*A*B"`).
- `events::Vector{String}`: string summaries of any reaction-system events.
- `constraints::Vector{String}`: string dump of any constraint equations.
- `metadata::Dict{String,Any}`: provenance.

---

### MockMTKSystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mock_systems.jl:38`

**Definition:**
```julia
struct MockMTKSystem
```

**Description:**
MockMTKSystem

No-MTK fallback for `ModelingToolkit.System`. Captures the ODE form of a
flattened ESM system as plain-Julia collections.

Fields:
- `name::Symbol`: system name.
- `state_variables::Vector{String}`: namespaced state-variable names.
- `parameters::Vector{String}`: namespaced parameter names.
- `observed_variables::Vector{String}`: namespaced observed-variable names.
- `equations::Vector{String}`: string dump of the flattened equations
  (one per equation, e.g. `"D(x, t) ~ -k * x"`).
- `events::Vector{String}`: string summaries of continuous/discrete events.
- `metadata::Dict{String,Any}`: provenance (source system, creation time, ...).

---

### MockPDESystem

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/mock_systems.jl:68`

**Definition:**
```julia
struct MockPDESystem
```

**Description:**
MockPDESystem

No-MTK fallback for `ModelingToolkit.PDESystem`. Captures the PDE form of a
flattened ESM system as plain-Julia collections.

Fields:
- `name::Symbol`: system name.
- `independent_variables::Vector{Symbol}`: e.g. `[:t, :x, :y]`.
- `state_variables::Vector{String}`: namespaced spatial-field names.
- `parameters::Vector{String}`: namespaced parameter names.
- `observed_variables::Vector{String}`: namespaced observed-variable names.
- `equations::Vector{String}`: string dump of the flattened PDE equations.
- `boundary_conditions::Vector{String}`: string dump of BCs derived from
  the domain and slice-based coupling patterns.
- `initial_conditions::Vector{String}`: string dump of ICs from variable
  defaults.
- `domain::Union{Domain,Nothing}`: the target domain of the flattened system.
- `metadata::Dict{String,Any}`: provenance.

---

### Model

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:347`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:256`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:64`

**Definition:**
```julia
struct OpExpr <: Expr
```

**Description:**
OpExpr(op::String, args::Vector{Expr}; wrt, dim, output_idx, expr_body, reduce, ranges, regions, values, shape, perm, axis, fn)

Operator expression node containing:
- `op`: operator name (e.g., "+", "*", "log", "D", "arrayop")
- `args`: vector of argument expressions
- `wrt`: variable name for differentiation (optional; for `D`)
- `dim`: dimension for spatial operators (optional; for `grad`, `div`)
- `output_idx`: for `arrayop`, list of result index symbols (String) or literal
  singleton dimensions (Int 1). Mirrors SymbolicUtils.ArrayOp.output_idx.
- `expr_body`: for `arrayop`, the scalar body evaluated at each index point
  (a nested `Expr` tree). Named `expr_body` — not `expr` — to avoid shadowing
  the `EarthSciSerialization.Expr` abstract type.
- `reduce`: for `arrayop`, the reduction operator applied to contracted
  indices (one of "+", "*", "max", "min"; default "+").
- `ranges`: for `arrayop`, map from index symbol name to iteration range
  (vector of 2 or 3 ints `[start, stop]` / `[start, step, stop]`).
- `regions`: for `makearray`, list of sub-region boxes, each a list of
  `[start, stop]` pairs per output dimension.
- `values`: for `makearray`, one sub-expression per entry in `regions`.
- `shape`: for `reshape`, target shape; entries are `Int` (concrete length)
  or `String` (symbolic dimension).
- `perm`: for `transpose`, optional 0-based axis permutation.
- `axis`: for `concat`, 0-based axis to concatenate along.
- `fn`: for `broadcast`, the scalar operator to apply element-wise.

---

### Operator

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:713`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:443`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:167`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:180`

**Definition:**
```julia
struct PresetTimesTrigger <: DiscreteEventTrigger
```

**Description:**
PresetTimesTrigger(times::Vector{Float64})

Trigger that fires at preset times.

---

### QualifiedReferenceError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:882`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:784`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:804`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:466`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:894`

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

### SliceOutOfDomainError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:127`

**Definition:**
```julia
struct SliceOutOfDomainError <: Exception
```

**Description:**
SliceOutOfDomainError

Defined for cross-language error-name parity; only raised if `slice` is ever
implemented at a higher tier in the Julia flatten pipeline. Would be raised
when a `slice` mapping's fixed coordinate lies outside the source variable's
declared domain extent.

**Available in other languages:**
- [Python](python.md#sliceoutofdomainerror)

---

### Species

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:426`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:771`

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

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/parse.jl:1104`

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

### Test

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:320`

**Definition:**
```julia
struct Test
```

**Description:**
Test(id, time_span, assertions; description, initial_conditions, parameter_overrides, tolerance)

Inline validation test for a Model (schema gt-cc1). Defines the run
configuration — initial conditions, parameter overrides, simulation time
span — and a list of scalar assertions that must hold.

**Available in other languages:**
- [Typescript](typescript.md#test)

---

### TimeSpan

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:279`

**Definition:**
```julia
struct TimeSpan
```

**Description:**
TimeSpan(start::Float64, stop::Float64)

Simulation time interval for inline model tests and examples (§gt-cc1).

**Available in other languages:**
- [Typescript](typescript.md#timespan)

---

### Tolerance

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/types.jl:290`

**Definition:**
```julia
struct Tolerance
```

**Description:**
Tolerance(abs::Union{Float64,Nothing}, rel::Union{Float64,Nothing})

Numerical comparison tolerance. Either or both of `abs` / `rel` may be
set; an assertion passes when any set bound is satisfied.

**Available in other languages:**
- [Typescript](typescript.md#tolerance)

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

### UnmappedDomainError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:60`

**Definition:**
```julia
struct UnmappedDomainError <: Exception
```

**Description:**
UnmappedDomainError

Raised when two systems on different domains are coupled without an `Interface`
that defines their dimension mapping (§4.7.6).

**Available in other languages:**
- [Python](python.md#unmappeddomainerror)

---

### UnsupportedMappingError

**File:** `/home/runner/work/EarthSciSerialization/EarthSciSerialization/packages/EarthSciSerialization.jl/src/flatten.jl:79`

**Definition:**
```julia
struct UnsupportedMappingError <: Exception
```

**Description:**
UnsupportedMappingError

Raised when an `Interface` requests a `dimension_mapping` type or regridding
strategy that is not supported by the current library tier (§4.7.6). The
`mapping_type` field carries the offending type or strategy name (e.g.
`"slice"`, `"project"`, `"regrid"`, or a specific regridding method like
`"cubic_spline"`). Matches the Rust `FlattenError::UnsupportedMapping` variant
and the Python `UnsupportedMappingError` exception for cross-language
error-name parity.

**Available in other languages:**
- [Python](python.md#unsupportedmappingerror)

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

