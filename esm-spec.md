# ESM Format Specification

**EarthSciML Serialization Format — Version 0.1.0 Draft**

## 1. Overview

The ESM (`.esm`) format is a JSON-based serialization format for EarthSciML model components, their composition, and runtime configuration. It serves three primary use cases:

1. **Persistence** — Save and load model definitions to/from disk
2. **Interchange** — Transfer models between Julia, TypeScript/web frontends, Rust, Python, and other languages
3. **Version control** — Produce human-readable, diff-friendly model specifications

ESM is **language-agnostic**. Every model must be fully self-describing: all equations, variables, parameters, species, and reactions are specified in the format itself. A conforming parser in any language can reconstruct the complete mathematical system from the `.esm` file alone, without access to any particular software package.

The two exceptions to full specification are **data loaders** and **registered operators**, which are inherently runtime-specific (file I/O, GPU kernels, platform-specific code) and are therefore referenced by type/name rather than fully defined.

**File extension:** `.esm`  
**MIME type:** `application/vnd.earthsciml+json`  
**Encoding:** UTF-8

---

## 2. Top-Level Structure

```json
{
  "esm": "0.1.0",
  "metadata": { ... },
  "models": { ... },
  "reaction_systems": { ... },
  "data_loaders": { ... },
  "operators": { ... },
  "coupling": [ ... ],
  "domains": { ... },
  "interfaces": { ... },
  "solver": { ... }
}
```

| Field | Required | Description |
|---|---|---|
| `esm` | ✓ | Format version string (semver) |
| `metadata` | ✓ | Authorship, provenance, description |
| `models` | | ODE-based model components (fully specified) |
| `reaction_systems` | | Reaction network components (fully specified) |
| `data_loaders` | | External data source registrations (by reference) |
| `operators` | | Registered runtime operators (by reference) |
| `coupling` | | Composition and coupling rules |
| `domains` | | Named spatial/temporal domain specifications (see Section 11) |
| `interfaces` | | Geometric connections between domains of different dimensionality (see Section 12) |
| `solver` | | Solver strategy and configuration |

At least one of `models` or `reaction_systems` must be present.

---

## 3. Metadata

```json
{
  "metadata": {
    "name": "FullChemistry_NorthAmerica",
    "description": "Coupled gas-phase chemistry with advection and meteorology over North America",
    "authors": ["Chris Tessum"],
    "license": "MIT",
    "created": "2026-02-11T00:00:00Z",
    "modified": "2026-02-11T00:00:00Z",
    "tags": ["atmospheric-chemistry", "advection", "north-america"],
    "references": [
      {
        "doi": "10.5194/acp-8-6365-2008",
        "citation": "Cameron-Smith et al., 2008. A new reduced mechanism for gas-phase chemistry.",
        "url": "https://doi.org/10.5194/acp-8-6365-2008"
      }
    ]
  }
}
```

---

## 4. Expression AST

Mathematical expressions are the foundation of the format. They are represented as a JSON tree that is unambiguous and parseable in any language without a math parser.

### 4.1 Grammar

```
Expr := number | string | ExprNode
ExprNode := { "op": string, "args": [Expr, ...], ...optional_fields }
```

- **Numbers** are JSON numbers: `3.14`, `-1`, `1.8e-12`
- **Strings** are variable/parameter references: `"O3"`, `"k1"`
- **ExprNodes** are operations

### 4.2 Built-in Operators

#### Arithmetic

| Op | Arity | Example | Meaning |
|---|---|---|---|
| `+` | n-ary | `{"op": "+", "args": ["a", "b", "c"]}` | a + b + c |
| `-` | unary or binary | `{"op": "-", "args": ["a"]}` | −a |
| `*` | n-ary | `{"op": "*", "args": ["k", "A", "B"]}` | k·A·B |
| `/` | binary | `{"op": "/", "args": ["a", "b"]}` | a / b |
| `^` | binary | `{"op": "^", "args": ["x", 2]}` | x² |

#### Calculus

| Op | Additional fields | Meaning |
|---|---|---|
| `D` | `"wrt": "t"` | Time derivative: ∂/∂t |
| `grad` | `"dim": "x"` | Spatial gradient: ∂/∂x |
| `div` | | Divergence: ∇· |
| `laplacian` | | Laplacian: ∇² |

Example: `{"op": "D", "args": ["O3"], "wrt": "t"}` represents ∂O₃/∂t.

#### Elementary Functions

`exp`, `log`, `log10`, `sqrt`, `abs`, `sign`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `min`, `max`, `floor`, `ceil`

All take their standard mathematical arguments in `args`.

#### Conditionals

| Op | Args | Meaning |
|---|---|---|
| `ifelse` | `[condition, then_expr, else_expr]` | Ternary conditional |
| `>`, `<`, `>=`, `<=`, `==`, `!=` | `[lhs, rhs]` | Comparison (returns boolean) |
| `and`, `or`, `not` | `[a, b]` or `[a]` | Logical operators |

#### Event-specific

| Op | Args | Meaning |
|---|---|---|
| `Pre` | `[var]` | Value of variable immediately before an event fires (see Section 5) |

### 4.3 Scoped References

Variables are referenced across systems using **hierarchical dot notation**. Systems can contain subsystems to arbitrary depth, and the dot-separated path walks the hierarchy from the top-level system down to the variable:

```
"System.variable"              →  variable in a top-level system
"System.Subsystem.variable"    →  variable in a subsystem of a top-level system
"A.B.C.variable"               →  variable in A → B → C (nested subsystems)
```

The **last** segment is always the variable (or species/parameter) name. All preceding segments are system names forming a path through the subsystem hierarchy. For example:

| Reference | Meaning |
|---|---|
| `"SuperFast.O3"` | Variable `O3` in top-level model `SuperFast` |
| `"SuperFast.GasPhase.O3"` | Variable `O3` in subsystem `GasPhase` of model `SuperFast` |
| `"Atmosphere.Chemistry.FastChem.NO2"` | Variable `NO2` in `Atmosphere` → `Chemistry` → `FastChem` |

**Resolution algorithm:** Given a scoped reference string, split on `"."` to produce segments `[s₁, s₂, …, sₙ]`. The final segment `sₙ` is the variable name. The preceding segments `[s₁, …, sₙ₋₁]` form a path: `s₁` must match a key in the top-level `models`, `reaction_systems`, `data_loaders`, or `operators` section, and each subsequent segment must match a key in the parent system's `subsystems` map.

**Bare references** (no dot) refer to a variable within the current system context. In coupling entries, all references must be fully qualified from the top-level system name.

### 4.4 Subsystem Inclusion by Reference

Subsystems can be defined inline (as described in Sections 6 and 7) or included by reference from an external ESM file. A reference is an object with a single `ref` field containing a local file path or URL:

```json
{
  "subsystems": {
    "Atmosphere": { "ref": "./atmosphere.esm" },
    "Ocean": { "ref": "https://example.com/models/ocean.esm" },
    "Land": {
      "variables": { ... },
      "equations": [ ... ]
    }
  }
}
```

In the example above, `Atmosphere` and `Ocean` are included by reference while `Land` is defined inline. Both forms can be freely mixed within the same `subsystems` map.

**Reference format:**

| Form | Example | Resolution |
|---|---|---|
| Relative path | `"./atmosphere.esm"` | Resolved relative to the directory of the referencing file |
| Absolute path | `"/models/atmosphere.esm"` | Used as-is |
| HTTP/HTTPS URL | `"https://example.com/models/atmosphere.esm"` | Fetched from the network |

**Referenced file requirements:**

- The referenced file must be a valid ESM file (with `esm` version and `metadata` fields).
- It must contain exactly one top-level model or reaction system. The single model or reaction system defined in the file is used as the subsystem definition.
- The subsystem key in the parent file determines the subsystem's name, not any name in the referenced file.

**Scoped references** work identically for referenced subsystems as for inline subsystems. After resolution, `"Parent.RefSubsystem.variable"` works the same regardless of whether `RefSubsystem` was defined inline or loaded from a reference.

**Resolution timing:** Libraries must resolve all references at load time, before validation or any other processing. After resolution, the in-memory representation is identical to a file with all subsystems defined inline.

---

## 5. Events

Events enable changes to system state or parameters when certain conditions are met, or detection of discontinuities during simulation. This section is designed to be compatible with ModelingToolkit.jl's `SymbolicContinuousCallback` and `SymbolicDiscreteCallback` semantics, while remaining language-agnostic.

Events are defined within `models` and `reaction_systems` via the `continuous_events` and `discrete_events` fields. They can also be attached at the coupling level for cross-system events.

### 5.1 Core Semantics: `Pre` and Affect Equations

Event affects (the state changes that occur when an event fires) use a **pre/post** convention for distinguishing values before and after the event:

- The **left-hand side** of an affect equation is the value *after* the event
- `Pre(var)` refers to the value *before* the event
- A variable that does not appear on the LHS of any affect equation is free to be modified by the runtime to maintain algebraic consistency (e.g., in DAE systems)

For example, to increment `x` by 1 when the event fires:

```json
{ "lhs": "x", "rhs": { "op": "+", "args": [{ "op": "Pre", "args": ["x"] }, 1] } }
```

The `Pre` operator is added to the expression AST:

| Op | Args | Meaning |
|---|---|---|
| `Pre` | `[var]` | Value of `var` immediately before the event fired |

### 5.2 Continuous Events

Continuous events fire when a **condition expression crosses zero**. The runtime uses root-finding to locate the precise crossing time. This corresponds to MTK's `SymbolicContinuousCallback` and DifferentialEquations.jl's `ContinuousCallback`.

```json
{
  "continuous_events": [
    {
      "name": "ground_bounce",
      "conditions": [
        { "op": "-", "args": ["x", 0] }
      ],
      "affects": [
        {
          "lhs": "v",
          "rhs": { "op": "*", "args": [-0.9, { "op": "Pre", "args": ["v"] }] }
        }
      ],
      "affect_neg": null,
      "root_find": "left",
      "description": "Ball bounces off ground at x=0 with 0.9 coefficient of restitution"
    },

    {
      "name": "wall_bounce",
      "conditions": [
        { "op": "-", "args": ["y", -1.5] },
        { "op": "-", "args": ["y", 1.5] }
      ],
      "affects": [
        {
          "lhs": "vy",
          "rhs": { "op": "*", "args": [-1, { "op": "Pre", "args": ["vy"] }] }
        }
      ],
      "description": "Bounce off walls at y = ±1.5"
    },

    {
      "name": "discontinuity_detection",
      "conditions": [
        { "op": "-", "args": ["v", 0] }
      ],
      "affects": [],
      "description": "Detect velocity zero crossing for friction discontinuity (no state change)"
    }
  ]
}
```

#### Continuous Event Fields

| Field | Required | Description |
|---|---|---|
| `name` | | Human-readable identifier |
| `conditions` | ✓ | Array of expressions. Event fires when any expression crosses zero. |
| `affects` | ✓ | Array of `{lhs, rhs}` affect equations. Empty array `[]` for pure detection (no state change). |
| `affect_neg` | | Separate affects for negative-going zero crossings. If `null` or absent, `affects` is used for both directions. |
| `root_find` | | Root-finding direction: `"left"` (default), `"right"`, or `"all"`. Maps to DiffEq `rootfind` option. |
| `reinitialize` | | Boolean. Whether to reinitialize the system after the event (default: `false`). |
| `description` | | Human-readable description |

#### Direction-dependent Affects

When a continuous event needs different behavior for positive vs. negative zero crossings (e.g., hysteresis control, quadrature encoding), use `affect_neg`:

```json
{
  "name": "thermostat",
  "conditions": [
    { "op": "-", "args": ["T", "T_setpoint"] }
  ],
  "affects": [
    {
      "lhs": "heater_on",
      "rhs": 0
    }
  ],
  "affect_neg": [
    {
      "lhs": "heater_on",
      "rhs": 1
    }
  ],
  "description": "Turn heater on when T drops below setpoint, off when above"
}
```

- `affects` fires on **positive-going** crossings (condition goes from negative to positive)
- `affect_neg` fires on **negative-going** crossings (condition goes from positive to negative)

### 5.3 Discrete Events

Discrete events fire when a **boolean condition evaluates to true** at the end of an integration step. They can also be triggered at specific times or periodically. This corresponds to MTK's `SymbolicDiscreteCallback`.

```json
{
  "discrete_events": [
    {
      "name": "injection",
      "trigger": {
        "type": "condition",
        "expression": { "op": "==", "args": ["t", "t_inject"] }
      },
      "affects": [
        {
          "lhs": "N",
          "rhs": { "op": "+", "args": [{ "op": "Pre", "args": ["N"] }, "M"] }
        }
      ],
      "description": "Add M cells at time t_inject"
    },

    {
      "name": "kill_production",
      "trigger": {
        "type": "condition",
        "expression": { "op": "==", "args": ["t", "t_kill"] }
      },
      "affects": [
        {
          "lhs": "alpha",
          "rhs": 0.0
        }
      ],
      "discrete_parameters": ["alpha"],
      "description": "Set production rate to zero at t_kill"
    },

    {
      "name": "periodic_emission_decay",
      "trigger": {
        "type": "periodic",
        "interval": 3600.0
      },
      "affects": [
        {
          "lhs": "emission_scale",
          "rhs": { "op": "*", "args": [{ "op": "Pre", "args": ["emission_scale"] }, 0.95] }
        }
      ],
      "discrete_parameters": ["emission_scale"],
      "description": "Reduce emission scaling factor by 5% every hour"
    },

    {
      "name": "preset_measurements",
      "trigger": {
        "type": "preset_times",
        "times": [3600.0, 7200.0, 14400.0, 28800.0]
      },
      "affects": [
        {
          "lhs": "sample_flag",
          "rhs": { "op": "+", "args": [{ "op": "Pre", "args": ["sample_flag"] }, 1] }
        }
      ],
      "discrete_parameters": ["sample_flag"],
      "description": "Mark measurement times"
    }
  ]
}
```

#### Discrete Event Fields

| Field | Required | Description |
|---|---|---|
| `name` | | Human-readable identifier |
| `trigger` | ✓ | Trigger specification (see trigger types below) |
| `affects` | ✓* | Array of `{lhs, rhs}` affect equations. *Required unless `functional_affect` is provided. |
| `discrete_parameters` | | Array of parameter names that are modified by this event. Parameters not listed here are treated as immutable. Required when affects modify parameters rather than state variables. |
| `reinitialize` | | Boolean. Whether to reinitialize the system after the event. |
| `description` | | Human-readable description |

#### Trigger Types

| Type | Fields | Description |
|---|---|---|
| `condition` | `expression` | Fires when the boolean expression is true at the end of a timestep |
| `periodic` | `interval`, `initial_offset` (optional) | Fires every `interval` time units |
| `preset_times` | `times` (array of numbers) | Fires at each specified time |

### 5.4 Discrete Parameters

Some events need to modify parameters rather than state variables. In the MTK model, parameters are immutable by default — they can only be changed by events if explicitly declared as `discrete_parameters`. This convention is preserved in ESM.

A parameter listed in `discrete_parameters` of an event:
- Must also be declared in the model's `variables` (with `"type": "parameter"`) or reaction system's `parameters`
- Will be modifiable by the event's affect equations
- Must be time-dependent in the underlying mathematical sense (even if constant between events)

### 5.5 Functional Affects (Registered)

Some events require behavior too complex for symbolic affect equations — for example, calling external code, performing interpolation lookups, or implementing control logic. These are analogous to MTK's functional affects.

Since ESM is language-agnostic, functional affects cannot embed executable code. Instead, they reference a **registered affect handler**, similar to how operators and data loaders are registered:

```json
{
  "name": "complex_controller",
  "trigger": {
    "type": "periodic",
    "interval": 60.0
  },
  "functional_affect": {
    "handler_id": "PIDController",
    "read_vars": ["T", "T_setpoint", "error_integral"],
    "read_params": ["Kp", "Ki", "Kd"],
    "modified_params": ["heater_power"],
    "config": {
      "anti_windup": true,
      "output_clamp": [0.0, 100.0]
    }
  },
  "reinitialize": true,
  "description": "PID temperature controller, updates heater power every 60s"
}
```

#### Functional Affect Fields

| Field | Required | Description |
|---|---|---|
| `handler_id` | ✓ | Registered identifier for the affect implementation |
| `read_vars` | ✓ | State variables accessed by the handler |
| `read_params` | ✓ | Parameters accessed by the handler |
| `modified_params` | | Parameters modified by the handler (these are implicitly discrete parameters) |
| `config` | | Handler-specific configuration |

### 5.6 Cross-System Events

Events that involve variables from multiple coupled systems can be specified at the coupling level rather than within a single model:

```json
{
  "coupling": [
    {
      "type": "event",
      "event_type": "continuous",
      "conditions": [
        { "op": "-", "args": ["ChemModel.O3", 1e-7] }
      ],
      "affects": [
        {
          "lhs": "EmissionModel.NOx_scale",
          "rhs": 0.5
        }
      ],
      "discrete_parameters": ["EmissionModel.NOx_scale"],
      "description": "Reduce NOx emissions by half when O3 exceeds threshold"
    }
  ]
}
```

---

## 6. Models (ODE Systems)

Each model corresponds to an ODE system — a set of time-dependent equations with state variables and parameters. Models are keyed by a unique identifier.

**All models must be fully specified.** Every equation, variable, and parameter must be present in the `.esm` file. This ensures any conforming parser can reconstruct the model without external dependencies.

### 6.1 Schema

```json
{
  "models": {
    "SuperFast": {
      "coupletype": "SuperFastCoupler",

      "reference": {
        "doi": "10.5194/acp-8-6365-2008",
        "citation": "Cameron-Smith et al., 2008",
        "url": "https://doi.org/10.5194/acp-8-6365-2008",
        "notes": "Simplified tropospheric chemistry mechanism with 16 species"
      },

      "variables": {
        "O3": {
          "type": "state",
          "units": "mol/mol",
          "default": 1.0e-8,
          "description": "Ozone mixing ratio"
        },
        "NO": {
          "type": "state",
          "units": "mol/mol",
          "default": 1.0e-10,
          "description": "Nitric oxide mixing ratio"
        },
        "NO2": {
          "type": "state",
          "units": "mol/mol",
          "default": 1.0e-10,
          "description": "Nitrogen dioxide mixing ratio"
        },
        "jNO2": {
          "type": "parameter",
          "units": "1/s",
          "default": 0.0,
          "description": "NO2 photolysis rate"
        },
        "k_NO_O3": {
          "type": "parameter",
          "units": "cm^3/molec/s",
          "default": 1.8e-12,
          "description": "Rate constant for NO + O3 → NO2 + O2"
        },
        "T": {
          "type": "parameter",
          "units": "K",
          "default": 298.15,
          "description": "Temperature"
        },
        "M": {
          "type": "parameter",
          "units": "molec/cm^3",
          "default": 2.46e19,
          "description": "Number density of air"
        },
        "total_O3_loss": {
          "type": "observed",
          "units": "mol/mol/s",
          "expression": {
            "op": "*",
            "args": ["k_NO_O3", "O3", "NO", "M"]
          },
          "description": "Total ozone chemical loss rate"
        }
      },

      "equations": [
        {
          "lhs": { "op": "D", "args": ["O3"], "wrt": "t" },
          "rhs": {
            "op": "+",
            "args": [
              { "op": "*", "args": [
                  { "op": "-", "args": ["k_NO_O3"] },
                  "O3", "NO", "M"
              ]},
              { "op": "*", "args": ["jNO2", "NO2"] }
            ]
          }
        },
        {
          "lhs": { "op": "D", "args": ["NO2"], "wrt": "t" },
          "rhs": {
            "op": "+",
            "args": [
              { "op": "*", "args": ["k_NO_O3", "O3", "NO", "M"] },
              { "op": "*", "args": [
                  { "op": "-", "args": ["jNO2"] },
                  "NO2"
              ]}
            ]
          }
        }
      ],

      "discrete_events": [],
      "continuous_events": []
    }
  }
}
```

### 6.2 Model Fields

| Field | Required | Description |
|---|---|---|
| `domain` | | Name of a domain from the `domains` section that this model is defined on. Omit or set to `null` for 0D (non-spatial) models — ODE or algebraic systems with no spatial dimensions. |
| `coupletype` | | Coupling type name (maps to EarthSciML `:coupletype` metadata). Used by `couple2` dispatch. |
| `reference` | | Academic citation: `doi`, `citation`, `url`, `notes` |
| `variables` | ✓ | All variables, keyed by name |
| `equations` | ✓ | Array of `{lhs, rhs}` equation objects |
| `discrete_events` | | Discrete events (see Section 5.3) |
| `continuous_events` | | Continuous events (see Section 5.2) |
| `subsystems` | | Named child models (subsystems), keyed by unique identifier. Each subsystem can be defined inline or included by reference (see Section 4.4). Enables hierarchical composition — variables in subsystems are referenced via dot notation (see Section 4.3). |

### 6.3 Variable Types

| Type | Description |
|---|---|
| `state` | Time-dependent unknowns; appear on the LHS of ODEs as D(var, t) |
| `parameter` | Values set externally or held constant during integration |
| `observed` | Derived quantities; must include an `expression` field |

### 6.4 Advection Model Example

Advection is a model like any other — fully specified:

```json
{
  "Advection": {
    "coupletype": null,
    "reference": {
      "notes": "First-order upwind advection operator"
    },
    "variables": {
      "u_wind": { "type": "parameter", "units": "m/s", "default": 0.0, "description": "Eastward wind speed" },
      "v_wind": { "type": "parameter", "units": "m/s", "default": 0.0, "description": "Northward wind speed" }
    },
    "equations": [
      {
        "_comment": "Applied to each coupled state variable via operator_compose",
        "lhs": { "op": "D", "args": ["_var"], "wrt": "t" },
        "rhs": {
          "op": "+",
          "args": [
            { "op": "*", "args": [
                { "op": "-", "args": ["u_wind"] },
                { "op": "grad", "args": ["_var"], "dim": "x" }
            ]},
            { "op": "*", "args": [
                { "op": "-", "args": ["v_wind"] },
                { "op": "grad", "args": ["_var"], "dim": "y" }
            ]}
          ]
        }
      }
    ]
  }
}
```

The special variable `"_var"` is a placeholder used in operator-style models. When coupled via `operator_compose`, it is substituted with each matching state variable from the target system.

### 6.5 Dry Deposition Model Example

A model that computes deposition velocities from surface resistance parameters. This model is coupled to a chemistry system via `couple2` to provide deposition loss terms, while a separate operator (see Section 9) handles grid-level application.

```json
{
  "DryDeposition": {
    "coupletype": "DryDepositionCoupler",
    "reference": {
      "doi": "10.1016/0004-6981(89)90153-4",
      "citation": "Wesely, 1989. Parameterization of surface resistances to gaseous dry deposition.",
      "notes": "Resistance-based model: v_dep = 1 / (r_a + r_b + r_c)"
    },
    "variables": {
      "r_a": {
        "type": "parameter",
        "units": "s/m",
        "default": 100.0,
        "description": "Aerodynamic resistance"
      },
      "r_b": {
        "type": "parameter",
        "units": "s/m",
        "default": 50.0,
        "description": "Quasi-laminar sublayer resistance"
      },
      "r_c_O3": {
        "type": "parameter",
        "units": "s/m",
        "default": 200.0,
        "description": "Surface resistance for O3"
      },
      "v_dep_O3": {
        "type": "observed",
        "units": "m/s",
        "expression": {
          "op": "/",
          "args": [
            1,
            { "op": "+", "args": ["r_a", "r_b", "r_c_O3"] }
          ]
        },
        "description": "Dry deposition velocity for O3"
      }
    },
    "equations": []
  }
}
```

---

## 7. Reaction Systems

Reaction systems provide a declarative representation of chemical or biological reaction networks. They are an alternative to writing raw ODEs — the ODE form is derived automatically from the reaction stoichiometry and rate laws.

This section maps to Catalyst.jl's `ReactionSystem` but is fully self-contained.

### 7.1 Schema

```json
{
  "reaction_systems": {
    "SuperFastReactions": {
      "coupletype": "SuperFastCoupler",

      "reference": {
        "doi": "10.5194/acp-8-6365-2008",
        "citation": "Cameron-Smith et al., 2008"
      },

      "species": {
        "O3":  { "units": "mol/mol", "default": 1.0e-8,  "description": "Ozone" },
        "NO":  { "units": "mol/mol", "default": 1.0e-10, "description": "Nitric oxide" },
        "NO2": { "units": "mol/mol", "default": 1.0e-10, "description": "Nitrogen dioxide" },
        "HO2": { "units": "mol/mol", "default": 1.0e-12, "description": "Hydroperoxyl radical" },
        "OH":  { "units": "mol/mol", "default": 1.0e-12, "description": "Hydroxyl radical" },
        "CO":  { "units": "mol/mol", "default": 1.0e-7,  "description": "Carbon monoxide" },
        "CO2": { "units": "mol/mol", "default": 4.0e-4,  "description": "Carbon dioxide" },
        "CH4": { "units": "mol/mol", "default": 1.8e-6,  "description": "Methane" },
        "CH2O":{ "units": "mol/mol", "default": 1.0e-10, "description": "Formaldehyde" },
        "H2O2":{ "units": "mol/mol", "default": 1.0e-10, "description": "Hydrogen peroxide" }
      },

      "parameters": {
        "T":    { "units": "K",          "default": 298.15,  "description": "Temperature" },
        "M":    { "units": "molec/cm^3", "default": 2.46e19, "description": "Air number density" },
        "jNO2": { "units": "1/s",        "default": 0.005,   "description": "NO2 photolysis rate" },
        "jH2O2":{ "units": "1/s",        "default": 5.0e-6,  "description": "H2O2 photolysis rate" },
        "jCH2O":{ "units": "1/s",        "default": 2.0e-5,  "description": "CH2O photolysis rate" },
        "emission_rate_NO": { "units": "mol/mol/s", "default": 0.0, "description": "NO emission rate" }
      },

      "reactions": [
        {
          "id": "R1",
          "name": "NO_O3",
          "substrates": [
            { "species": "NO", "stoichiometry": 1 },
            { "species": "O3", "stoichiometry": 1 }
          ],
          "products": [
            { "species": "NO2", "stoichiometry": 1 }
          ],
          "rate": {
            "op": "*",
            "args": [
              1.8e-12,
              { "op": "exp", "args": [
                  { "op": "/", "args": [-1370, "T"] }
              ]},
              "M"
            ]
          },
          "reference": { "notes": "JPL 2015 recommendation. Rate includes M factor for mixing-ratio species." }
        },
        {
          "id": "R2",
          "name": "NO2_photolysis",
          "substrates": [
            { "species": "NO2", "stoichiometry": 1 }
          ],
          "products": [
            { "species": "NO", "stoichiometry": 1 },
            { "species": "O3", "stoichiometry": 1 }
          ],
          "rate": "jNO2",
          "reference": { "notes": "NO2 + hν → NO + O(³P); O(³P) + O2 + M → O3" }
        },
        {
          "id": "R3",
          "name": "CO_OH",
          "substrates": [
            { "species": "CO", "stoichiometry": 1 },
            { "species": "OH", "stoichiometry": 1 }
          ],
          "products": [
            { "species": "CO2", "stoichiometry": 1 },
            { "species": "HO2", "stoichiometry": 1 }
          ],
          "rate": {
            "op": "*",
            "args": [
              { "op": "+",
                "args": [
                  1.44e-13,
                  { "op": "/", "args": ["M", 3.43e11] }
                ]
              },
              "M"
            ]
          }
        },
        {
          "id": "R4",
          "name": "H2O2_photolysis",
          "substrates": [
            { "species": "H2O2", "stoichiometry": 1 }
          ],
          "products": [
            { "species": "OH", "stoichiometry": 2 }
          ],
          "rate": "jH2O2"
        },
        {
          "id": "R5",
          "name": "HO2_self",
          "substrates": [
            { "species": "HO2", "stoichiometry": 2 }
          ],
          "products": [
            { "species": "H2O2", "stoichiometry": 1 }
          ],
          "rate": {
            "op": "*",
            "args": [
              2.2e-13,
              { "op": "exp", "args": [
                  { "op": "/", "args": [600, "T"] }
              ]},
              "M"
            ]
          }
        },
        {
          "id": "R6",
          "name": "CH4_OH",
          "substrates": [
            { "species": "CH4", "stoichiometry": 1 },
            { "species": "OH", "stoichiometry": 1 }
          ],
          "products": [
            { "species": "CH2O", "stoichiometry": 1 },
            { "species": "HO2", "stoichiometry": 1 }
          ],
          "rate": {
            "op": "*",
            "args": [
              1.85e-12,
              { "op": "exp", "args": [
                  { "op": "/", "args": [-1690, "T"] }
              ]},
              "M"
            ]
          }
        },
        {
          "id": "R7",
          "name": "CH2O_photolysis",
          "substrates": [
            { "species": "CH2O", "stoichiometry": 1 }
          ],
          "products": [
            { "species": "CO", "stoichiometry": 1 },
            { "species": "HO2", "stoichiometry": 2 }
          ],
          "rate": "jCH2O"
        },
        {
          "id": "R8",
          "name": "emission_NO",
          "substrates": null,
          "products": [
            { "species": "NO", "stoichiometry": 1 }
          ],
          "rate": "emission_rate_NO",
          "reference": { "notes": "Source term from emissions data" }
        }
      ],

      "constraint_equations": [],

      "discrete_events": [],
      "continuous_events": []
    }
  }
}
```

### 7.2 Reaction System Fields

| Field | Required | Description |
|---|---|---|
| `domain` | | Name of a domain from the `domains` section that this reaction system is defined on. Omit or set to `null` for 0D (non-spatial) systems. |
| `coupletype` | | Coupling type name for `couple2` dispatch |
| `reference` | | Academic citation |
| `species` | ✓ | Named reactive species with units, defaults, descriptions |
| `parameters` | ✓ | Named parameters (rate constants, temperature, photolysis rates, etc.) |
| `reactions` | ✓ | Array of reaction definitions |
| `constraint_equations` | | Additional algebraic or ODE constraints (in expression AST form) |
| `discrete_events` | | Discrete events (see Section 5.3) |
| `continuous_events` | | Continuous events (see Section 5.2) |
| `subsystems` | | Named child reaction systems (subsystems), keyed by unique identifier. Each subsystem can be defined inline or included by reference (see Section 4.4). Enables hierarchical composition — variables in subsystems are referenced via dot notation (see Section 4.3). |

### 7.3 Reaction Fields

| Field | Required | Description |
|---|---|---|
| `id` | ✓ | Unique reaction identifier (e.g., `"R1"`) |
| `name` | | Human-readable name |
| `substrates` | ✓ | Array of `{species, stoichiometry}` or `null` for source reactions (∅ → X) |
| `products` | ✓ | Array of `{species, stoichiometry}` or `null` for sink reactions (X → ∅) |
| `rate` | ✓ | Rate expression: a string (parameter ref), number, or expression AST |
| `reference` | | Per-reaction citation or notes |

### 7.4 ODE Generation from Reactions

A conforming implementation generates ODEs from the reaction list using standard mass action kinetics. For a reaction with rate `k`, substrates `{S_i}` with stoichiometries `{n_i}`, and products `{P_j}` with stoichiometries `{m_j}`:

**Rate law:**
```
v = k · ∏ᵢ Sᵢ^nᵢ
```

**ODE contribution** for species X:
```
dX/dt += (net_stoich_X) · v
```

where `net_stoich_X = (stoich as product) − (stoich as substrate)`.

**Unit convention:** The `rate` field in each reaction must be the **effective rate** for the species units used — i.e., mass action applied to the rate and species values must produce the correct ODE tendency in the declared species units. When species are in mixing ratios (e.g., `mol/mol`) but rate constants are in concentration units (e.g., `cm³/molec/s`), the rate expression must include the appropriate number density factor(s) `M` to convert. For a reaction of total substrate order `n`, the rate should include `M^(n−1)`.

---

## 8. Data Loaders

Data loaders are inherently runtime-specific — they involve file I/O, network access, data format parsing, and interpolation. They are therefore **registered by type and name** rather than fully specified.

A data loader declares what variables it provides and how to identify/configure the data source. The actual loading implementation is supplied by the runtime environment.

```json
{
  "data_loaders": {
    "GEOSFP": {
      "type": "gridded_data",
      "loader_id": "GEOSFP",
      "config": {
        "resolution": "0.25x0.3125_NA",
        "coord_defaults": { "lat": 34.0, "lev": 1 }
      },
      "reference": {
        "citation": "Global Modeling and Assimilation Office (GMAO), NASA GSFC",
        "url": "https://gmao.gsfc.nasa.gov/GEOS_systems/"
      },
      "provides": {
        "u": { "units": "m/s", "description": "Eastward wind component" },
        "v": { "units": "m/s", "description": "Northward wind component" },
        "T": { "units": "K", "description": "Air temperature" },
        "PBLH": { "units": "m", "description": "Planetary boundary layer height" }
      },
      "temporal_resolution": "PT3H",
      "spatial_resolution": { "lon": 0.3125, "lat": 0.25 },
      "interpolation": "linear"
    },

    "NEI_Emissions": {
      "type": "emissions",
      "loader_id": "NEI2016",
      "config": {
        "year": 2016,
        "sector": "all"
      },
      "reference": {
        "citation": "US EPA, 2016 National Emissions Inventory",
        "url": "https://www.epa.gov/air-emissions-inventories"
      },
      "provides": {
        "emission_rate_NO": { "units": "mol/mol/s", "description": "NO emission rate" },
        "emission_rate_CO": { "units": "mol/mol/s", "description": "CO emission rate" }
      }
    }
  }
}
```

### 8.1 Data Loader Fields

| Field | Required | Description |
|---|---|---|
| `type` | ✓ | Category: `gridded_data`, `emissions`, `timeseries`, `static`, `callback` |
| `loader_id` | ✓ | Registered identifier the runtime uses to find the implementation |
| `config` | | Implementation-specific configuration (opaque to the format) |
| `reference` | | Data source citation |
| `provides` | ✓ | Named variables this loader makes available, with units and descriptions |
| `temporal_resolution` | | ISO 8601 duration (e.g., `"PT3H"`) |
| `spatial_resolution` | | Grid spacing |
| `interpolation` | | Interpolation method: `"linear"`, `"nearest"`, `"cubic"` |

---

## 9. Operators

Operators correspond to `EarthSciMLBase.Operator` — objects that modify the simulator state directly via `SciMLOperators`. They cannot be expressed purely as ODEs because they involve operations like numerical advection schemes, diffusion stencils, or deposition algorithms that operate on the full discretized state array.

Like data loaders, operators are **registered by type** rather than fully specified, since their implementation is inherently tied to the discretization and runtime.

```json
{
  "operators": {
    "DryDepGrid": {
      "operator_id": "WesleyDryDep",
      "reference": {
        "doi": "10.1016/0004-6981(89)90153-4",
        "citation": "Wesely, 1989. Parameterization of surface resistances to gaseous dry deposition in regional-scale numerical models.",
        "notes": "Resistance-based model: r_total = r_a + r_b + r_c"
      },
      "config": {
        "season": "summer",
        "land_use_categories": 11
      },
      "needed_vars": ["O3", "NO2", "SO2", "T", "u_star", "LAI"],
      "modifies": ["O3", "NO2", "SO2"],
      "description": "First-order dry deposition loss based on surface resistance parameterization"
    },

    "WetScavenging": {
      "operator_id": "BelowCloudScav",
      "reference": {
        "doi": "10.1029/2001JD001480"
      },
      "needed_vars": ["precip_rate", "cloud_fraction"],
      "modifies": ["H2O2", "CH2O", "HNO3"],
      "description": "Below-cloud washout of soluble species"
    }
  }
}
```

### 9.1 Operator Fields

| Field | Required | Description |
|---|---|---|
| `operator_id` | ✓ | Registered identifier the runtime uses to find the implementation |
| `reference` | | Academic citation |
| `config` | | Implementation-specific configuration |
| `needed_vars` | ✓ | Variables required by the operator (input to `get_needed_vars`) |
| `modifies` | | Variables the operator modifies (informational, for dependency analysis) |
| `description` | | Human-readable description |

---

## 10. Coupling

The coupling section defines how models, reaction systems, data loaders, and operators connect to form a `CoupledSystem`. Each entry maps to an EarthSciML composition mechanism.

```json
{
  "coupling": [
    {
      "type": "operator_compose",
      "systems": ["SuperFastReactions", "Advection"],
      "description": "Add advection terms to all state variables in chemistry system"
    },

    {
      "type": "couple2",
      "systems": ["SuperFastReactions", "DryDeposition"],
      "coupletype_pair": ["SuperFastCoupler", "DryDepositionCoupler"],
      "connector": {
        "equations": [
          {
            "from": "DryDeposition.v_dep_O3",
            "to": "SuperFastReactions.O3",
            "transform": "additive",
            "expression": {
              "op": "*",
              "args": [
                { "op": "-", "args": ["DryDeposition.v_dep_O3"] },
                "SuperFastReactions.O3"
              ]
            }
          }
        ]
      },
      "description": "Bi-directional: deposition velocities computed from chemistry state"
    },

    {
      "type": "variable_map",
      "from": "GEOSFP.T",
      "to": "SuperFastReactions.T",
      "transform": "param_to_var",
      "description": "Replace constant temperature with GEOS-FP field"
    },

    {
      "type": "variable_map",
      "from": "GEOSFP.u",
      "to": "Advection.u_wind",
      "transform": "param_to_var"
    },

    {
      "type": "variable_map",
      "from": "GEOSFP.v",
      "to": "Advection.v_wind",
      "transform": "param_to_var"
    },

    {
      "type": "variable_map",
      "from": "NEI_Emissions.emission_rate_NO",
      "to": "SuperFastReactions.emission_rate_NO",
      "transform": "param_to_var"
    },

    {
      "type": "operator_apply",
      "operator": "DryDepGrid",
      "description": "Apply dry deposition operator during simulation"
    },

    {
      "type": "operator_apply",
      "operator": "WetScavenging",
      "description": "Apply wet scavenging operator during simulation"
    }
  ]
}
```

### 10.1 Coupling Types

| Type | EarthSciML Mechanism | Description |
|---|---|---|
| `operator_compose` | `operator_compose(a, b)` | Match LHS time derivatives and add RHS terms together |
| `couple2` | `couple2(::ACoupler, ::BCoupler)` | Bi-directional coupling via coupletype dispatch. `connector` specifies the `ConnectorSystem` equations. |
| `variable_map` | `param_to_var` + connection | Replace a parameter in one system with a variable from another |
| `operator_apply` | `Operator` in `CoupledSystem.ops` | Register an Operator to run during simulation |
| `callback` | `init_callback` | Register a callback for simulation events |
| `event` | Cross-system event | Continuous or discrete event involving multiple coupled systems (see Section 5.6) |

### 10.2 The `translate` Field

For `operator_compose`, `translate` specifies variable mappings when LHS variables don't have matching names. Keys and values use scoped references (`"System.var"`). Note that the `_var` placeholder (Section 6.4) is automatically expanded to all state variables in the target system, so `translate` is only needed when two non-placeholder systems have differently-named variables representing the same quantity:

```json
"translate": {
  "ChemModel.ozone": "PhotolysisModel.O3"
}
```

Optionally with a conversion factor:

```json
"translate": {
  "ChemModel.ozone": { "var": "PhotolysisModel.O3", "factor": 1e-9 }
}
```

### 10.3 The `connector` Field

For `couple2`, `connector` defines the `ConnectorSystem` — the set of equations that link two systems. Each equation specifies which variable is affected and how:

| Transform | Description |
|---|---|
| `additive` | Add expression as source/sink term |
| `multiplicative` | Multiply existing tendency by expression |
| `replacement` | Replace the variable value entirely |

### 10.4 The `variable_map` Transforms

For `variable_map` coupling entries, `transform` specifies how the source variable maps to the target:

| Transform | Description |
|---|---|
| `param_to_var` | Replace a constant parameter with a time-varying variable from another system |
| `identity` | Direct assignment without type change |
| `additive` | Add the source variable as an additional term |
| `multiplicative` | Multiply the target by the source variable |
| `conversion_factor` | Apply a unit conversion factor (specified in the `factor` field) |

### 10.5 Cross-Domain Coupling

When two coupled systems live on different domains, the coupling entry must specify how to handle the dimension mismatch. There are two mechanisms: **interface-mediated** coupling (for spatial domains that share a geometric boundary) and **lifting** (for coupling between 0D and spatial systems).

#### The `interface` Field

For coupling between spatial domains of different dimensionality, reference a named interface from the `interfaces` section (see Section 12). The interface defines the geometric relationship — which dimensions are shared, how non-shared dimensions are constrained, and what regridding strategy to use.

```json
{
  "type": "variable_map",
  "from": "AtmosphericDynamics.wind_u",
  "to": "WildfirePropagation.wind_u",
  "transform": "param_to_var",
  "interface": "ground_surface",
  "description": "Ground-level eastward wind drives wildfire spread"
}
```

The interface handles both dimension reduction (e.g., extracting a 2D slice from a 3D field) and regridding (when shared dimensions have different resolutions across domains). The coupling entry only needs to name the interface — the dimensional details are defined once in the interface specification.

For `operator_compose` and `couple2`, the `interface` field works similarly:

```json
{
  "type": "operator_compose",
  "systems": ["AtmosphericDynamics", "WildfireHeatSource"],
  "interface": "ground_surface",
  "description": "Inject wildfire heat release into lowest atmospheric layer"
}
```

#### The `lifting` Field

For coupling between a 0D (non-spatial) system and a spatially-resolved system, the `lifting` field specifies how the 0D system's inputs and outputs map to the spatial grid. The lifting is relative to the **target system's domain** — i.e., the spatial grid on which the operation is evaluated.

```json
{
  "type": "variable_map",
  "from": "FireSpreadCalculator.spread_rate",
  "to": "WildfirePropagation.spread_rate",
  "transform": "param_to_var",
  "lifting": "pointwise",
  "description": "Wind-computed spread rate feeds wildfire PDE at each grid point"
}
```

| Lifting | Description |
|---|---|
| `pointwise` | **(Default.)** The 0D system is evaluated independently at each grid point. Inputs are pointwise values extracted from spatial fields; outputs are pointwise values applied to the spatial grid. This is how column physics parameterizations work in climate models. |
| `broadcast` | A single scalar output from the 0D system is applied uniformly to all grid points. Use when the 0D system computes a domain-wide quantity (e.g., a global scaling factor). |
| `mean` | Inputs to the 0D system are the spatial mean of the source fields. Output is scalar (combine with `broadcast` on the output side if needed). |
| `integral` | Inputs to the 0D system are the spatial integral of the source fields. Output is scalar. |

When `lifting` is omitted and the source or target system has `"domain": null`, pointwise lifting is assumed.

#### Combining `interface` and `lifting`

A coupling chain may require both an interface (for dimension reduction between spatial domains) and lifting (for 0D intermediaries). This is expressed as separate coupling entries. For example, extracting ground-level winds from a 3D atmosphere, passing them through a 0D algebraic fire-spread calculator, and feeding the result into a 2D wildfire model:

```json
[
  {
    "type": "variable_map",
    "from": "AtmosphericDynamics.wind_u",
    "to": "FireSpreadCalculator.wind_u",
    "transform": "param_to_var",
    "interface": "ground_surface",
    "lifting": "pointwise",
    "description": "Ground-level u-wind to fire spread calculator"
  },
  {
    "type": "variable_map",
    "from": "FireSpreadCalculator.spread_rate",
    "to": "WildfirePropagation.R_spread",
    "transform": "param_to_var",
    "lifting": "pointwise",
    "description": "Calculated spread rate drives wildfire propagation"
  }
]
```

In the first entry, `interface` reduces 3D→2D (extracting at the ground surface) and `lifting: "pointwise"` maps the resulting 2D field into the 0D system at each grid point. In the second entry, `lifting: "pointwise"` maps the 0D output to the 2D wildfire grid.

### 10.6 Cross-Domain Coupling Rules

1. **Same-domain coupling** requires no `interface` or `lifting` field and works as described in Sections 10.1–10.4.

2. **Cross-domain spatial coupling** (between domains that share a geometric boundary) **must** reference a named `interface`. The interface defines dimension mapping and regridding. It is an error to couple systems on different spatial domains without an interface.

3. **0D ↔ spatial coupling** **must** specify a `lifting` strategy (or accept the default `pointwise`). A 0D system coupled to a spatial system is evaluated on the spatial system's grid according to the lifting strategy.

4. **0D ↔ 0D coupling** requires neither `interface` nor `lifting` — it is standard scalar coupling.

5. **Cross-domain with 0D intermediary**: When a 0D system mediates between two spatial domains (e.g., atmosphere → 0D calculator → wildfire), each leg of the coupling is a separate entry. The first entry uses `interface` + `lifting`, the second uses `lifting` alone.

6. **Interface-mediated `operator_compose`**: When `operator_compose` crosses an interface, the operator's equations are evaluated on the *lower-dimensional* domain's grid. The interface handles projection/injection automatically — the operator adds terms to the target system's equations after the interface has mapped the fields.

7. **Bidirectional interfaces**: An interface can be traversed in either direction. Coupling from a 3D domain to a 2D domain through an interface performs restriction (slicing + regridding). Coupling from a 2D domain to a 3D domain through the same interface performs prolongation (injection into the constrained dimension level + regridding).

8. **Multiple interfaces between the same domain pair**: Different interfaces between the same two domains are permitted (e.g., `ground_surface` at `lev=min` and `tropopause` at a specific pressure level). Each coupling entry references the specific interface it uses.

### 10.7 Coupled System Flattening

The coupling section defines relationships between component systems, but simulation and analysis require a single unified equation system. **Flattening** is the process of resolving all coupling rules and producing a single flat system with dot-namespaced variables.

**Dot-namespaced variables:** In the flattened system, every variable, parameter, and species is prefixed with its owning system's name using dot notation. For nested subsystems, each level is included:

```
SimpleOzone.O3            # species O3 from the SimpleOzone reaction system
Advection.u_wind          # parameter u_wind from the Advection model
Atmosphere.Chemistry.NO2  # species NO2 from a nested subsystem
```

The last dot-separated segment is always the variable name; all preceding segments form the system path. This convention is consistent with the scoped reference notation used in coupling entries (Section 4.3) — the difference is that in the flattened system, **all** variable references are fully qualified, not just cross-system references.

**Flattening is a core operation.** All libraries (not just simulation-tier) must be able to flatten a coupled system. The flattened representation is the input to:

- **Graph construction** — the expression graph (Section 4.8.2 of the library spec) operates on the flattened system to produce cross-system dependency edges.
- **Coupled system validation** — checking that all coupling references resolve, no variables are orphaned, and equation–unknown balance holds across the full system.
- **Simulation** — Julia libraries convert the flattened system to a single MTK `ODESystem` (for 0D/ODE-only systems) or `PDESystem` (for systems with spatial derivatives), using MTK's native namespace separator (`₊`) in place of dots.
- **Export and display** — pretty-printing the full coupled system as a single set of equations.

The flattening algorithm is specified in detail in the ESM Library Specification (Section 4.7.5).

---

## 11. Domains

The `domains` section is a dictionary of named spatiotemporal domains. Each domain corresponds to an `EarthSciMLBase.DomainInfo` and specifies the extent, discretization, coordinate system, and boundary/initial conditions for one spatial region. Models and reaction systems reference domains by name via their `domain` field.

Multi-domain configurations enable coupling between systems of different dimensionality — for example, a 3D atmospheric dynamics PDE coupled to a 2D wildfire propagation PDE, or a 3D ocean coupled to the atmosphere at the sea surface.

### 11.1 Schema

```json
{
  "domains": {
    "atmosphere": {
      "independent_variable": "t",

      "temporal": {
        "start": "2024-07-15T00:00:00Z",
        "end": "2024-07-16T00:00:00Z",
        "reference_time": "2024-07-15T00:00:00Z"
      },

      "spatial": {
        "lon": { "min": -120.0, "max": -115.0, "units": "degrees", "grid_spacing": 0.1 },
        "lat": { "min": 33.0, "max": 36.0, "units": "degrees", "grid_spacing": 0.1 },
        "lev": { "min": 0.0, "max": 20000.0, "units": "m", "grid_spacing": 500.0 }
      },

      "coordinate_transforms": [
        { "id": "lonlat_to_meters", "dimensions": ["lon", "lat"] }
      ],
      "spatial_ref": "WGS84",

      "initial_conditions": { "type": "constant", "value": 0.0 },
      "boundary_conditions": [
        { "type": "zero_gradient", "dimensions": ["lon", "lat"] },
        { "type": "zero_gradient", "dimensions": ["lev"] }
      ],
      "element_type": "Float64",
      "array_type": "Array"
    },

    "wildfire_surface": {
      "independent_variable": "t",

      "temporal": {
        "start": "2024-07-15T00:00:00Z",
        "end": "2024-07-16T00:00:00Z"
      },

      "spatial": {
        "lon": { "min": -119.0, "max": -117.0, "units": "degrees", "grid_spacing": 0.01 },
        "lat": { "min": 34.0, "max": 35.0, "units": "degrees", "grid_spacing": 0.01 }
      },

      "coordinate_transforms": [
        { "id": "lonlat_to_meters", "dimensions": ["lon", "lat"] }
      ],
      "spatial_ref": "WGS84",

      "initial_conditions": { "type": "constant", "value": 0.0 },
      "boundary_conditions": [
        { "type": "zero_gradient", "dimensions": ["lon", "lat"] }
      ],
      "element_type": "Float64"
    },

    "ocean": {
      "independent_variable": "t",

      "temporal": {
        "start": "2024-07-15T00:00:00Z",
        "end": "2024-07-16T00:00:00Z"
      },

      "spatial": {
        "lon": { "min": -120.0, "max": -115.0, "units": "degrees", "grid_spacing": 0.25 },
        "lat": { "min": 33.0, "max": 36.0, "units": "degrees", "grid_spacing": 0.25 },
        "depth": { "min": 0.0, "max": 5000.0, "units": "m", "grid_spacing": 50.0 }
      },

      "coordinate_transforms": [
        { "id": "lonlat_to_meters", "dimensions": ["lon", "lat"] }
      ],
      "spatial_ref": "WGS84",

      "initial_conditions": { "type": "constant", "value": 0.0 },
      "boundary_conditions": [
        { "type": "periodic", "dimensions": ["lon"] },
        { "type": "zero_gradient", "dimensions": ["lat"] },
        { "type": "zero_gradient", "dimensions": ["depth"] }
      ],
      "element_type": "Float64"
    }
  }
}
```

### 11.2 Domain Dimensionality

Domains are categorized by their spatial dimensionality:

| Dimensionality | `spatial` field | Example use cases |
|---|---|---|
| **0D** | Omitted or `{}` | Box models, point-source chemistry, algebraic parameterizations |
| **1D** | 1 spatial dimension | Column models, vertical profiles, transect models |
| **2D** | 2 spatial dimensions | Surface fire spread, sea-ice extent, land surface models |
| **3D** | 3 spatial dimensions | Atmospheric dynamics, ocean circulation, subsurface flow |

Models with `"domain": null` are 0D regardless of whether a 0D domain exists. A 0D model has no spatial grid — when coupled to a spatial system, the lifting strategy (Section 10.5) determines how it maps to the spatial grid.

### 11.3 Domain Fields

Each named domain supports the following fields:

| Field | Required | Description |
|---|---|---|
| `independent_variable` | | Name of the time variable (default: `"t"`) |
| `temporal` | | Temporal extent: `start`, `end`, `reference_time` (ISO 8601) |
| `spatial` | | Dictionary of named spatial dimensions, each with `min`, `max`, `units`, `grid_spacing` |
| `coordinate_transforms` | | Array of coordinate transform specifications |
| `spatial_ref` | | Spatial reference system (e.g., `"WGS84"`) |
| `initial_conditions` | | Initial condition specification (see Section 11.4) |
| `boundary_conditions` | | Array of boundary condition specifications (see Section 11.5) |
| `element_type` | | Numeric element type (e.g., `"Float32"`, `"Float64"`) |
| `array_type` | | Array implementation type (e.g., `"Array"`) |

### 11.4 Initial Condition Types

| Type | Fields | Description |
|---|---|---|
| `constant` | `value` | Uniform initial value for all state variables |
| `per_variable` | `values: {var: value}` | Per-variable initial values |
| `from_file` | `path`, `format` | Load from external file |

### 11.5 Boundary Condition Types

| Type | Description |
|---|---|
| `constant` | Fixed value at boundaries |
| `zero_gradient` | ∂u/∂n = 0 at boundaries (Neumann) |
| `periodic` | Wrap-around boundaries |
| `dirichlet` | Fixed value at boundaries (equivalent to `constant`) |
| `neumann` | ∂u/∂n = 0 at boundaries (equivalent to `zero_gradient`) |
| `robin` | Mixed boundary condition: αu + β∂u/∂n = γ |

#### Additional Boundary Condition Fields

| Field | Type | Description |
|---|---|---|
| `value` | number | Boundary value (for `constant`/`dirichlet` types) |
| `function` | string | Function specification for time/space-varying boundaries |
| `robin_alpha` | number | Robin BC coefficient α for u term in αu + β∂u/∂n = γ |
| `robin_beta` | number | Robin BC coefficient β for ∂u/∂n term in αu + β∂u/∂n = γ |
| `robin_gamma` | number | Robin BC RHS value γ in αu + β∂u/∂n = γ |

**Note:** `dirichlet` and `neumann` are alternative names for `constant` and `zero_gradient` respectively. The Robin boundary condition provides a general mixed formulation where appropriate coefficients can recover Dirichlet (α=1, β=0) or Neumann (α=0, β=1) conditions as special cases.

### 11.6 Shared Temporal Domain

All domains in a coupled system must have compatible temporal extents. The solver (Section 13) advances the entire coupled system in time; individual domains may use different spatial discretizations but share the same simulation time window. If temporal extents differ, the solver uses the intersection of all domain temporal ranges.

---

## 12. Interfaces

Interfaces define the geometric relationship between two domains of potentially different dimensionality. They specify which spatial dimensions are shared, how non-shared dimensions are constrained at the interface, and what regridding strategy is used when shared dimensions have different resolutions.

### 12.1 Schema

```json
{
  "interfaces": {
    "ground_surface": {
      "description": "Ground-level interface between atmosphere and land surface / wildfire domain",
      "domains": ["atmosphere", "wildfire_surface"],
      "dimension_mapping": {
        "shared": {
          "atmosphere.lon": "wildfire_surface.lon",
          "atmosphere.lat": "wildfire_surface.lat"
        },
        "constraints": {
          "atmosphere.lev": {
            "value": "min",
            "description": "Ground level (lowest atmospheric layer)"
          }
        }
      },
      "regridding": {
        "method": "bilinear"
      }
    },

    "sea_surface": {
      "description": "Air-sea interface between atmosphere and ocean",
      "domains": ["atmosphere", "ocean"],
      "dimension_mapping": {
        "shared": {
          "atmosphere.lon": "ocean.lon",
          "atmosphere.lat": "ocean.lat"
        },
        "constraints": {
          "atmosphere.lev": {
            "value": "min",
            "description": "Lowest atmospheric level"
          },
          "ocean.depth": {
            "value": "min",
            "description": "Ocean surface layer"
          }
        }
      },
      "regridding": {
        "method": "conservative",
        "description": "Flux-conserving interpolation for energy and mass exchange"
      }
    }
  }
}
```

### 12.2 Interface Fields

| Field | Required | Description |
|---|---|---|
| `description` | | Human-readable description of the interface |
| `domains` | ✓ | Two-element array naming the domains connected by this interface |
| `dimension_mapping` | ✓ | Specifies shared dimensions and constraints (see below) |
| `regridding` | | Regridding strategy when shared dimensions differ in resolution |

### 12.3 Dimension Mapping

The `dimension_mapping` object has two sub-fields:

**`shared`**: A dictionary mapping dimensions that correspond across the two domains. Keys and values use `"domain.dimension"` notation. Shared dimensions define the geometric surface where the two domains meet. If the shared dimensions have different extents, the interface surface is their intersection.

```json
"shared": {
  "atmosphere.lon": "wildfire_surface.lon",
  "atmosphere.lat": "wildfire_surface.lat"
}
```

**`constraints`**: A dictionary specifying how non-shared dimensions are fixed at the interface. Each key is a `"domain.dimension"` reference; the value specifies where that dimension is constrained.

| Constraint value | Description |
|---|---|
| `"min"` | The minimum value of the dimension's range |
| `"max"` | The maximum value of the dimension's range |
| *(number)* | A specific coordinate value within the dimension's range |
| `"boundary"` | The domain boundary (equivalent to `"min"` or `"max"` depending on orientation) |

```json
"constraints": {
  "atmosphere.lev": { "value": "min", "description": "Ground level" },
  "ocean.depth": { "value": 0.0, "description": "Sea surface" }
}
```

**Constraint semantics**: When a variable is transferred **from** a domain with a constrained dimension, the field is *sliced* (restricted) at that coordinate — reducing dimensionality by one per constraint. When a variable is transferred **to** a domain with a constrained dimension, the lower-dimensional field is *injected* (prolongated) at that coordinate — embedded into the higher-dimensional grid at the specified level.

### 12.4 Regridding

When shared dimensions have different resolutions or extents across the two domains, regridding interpolates fields between the grids. The `regridding` field specifies the interpolation strategy.

| Method | Description |
|---|---|
| `bilinear` | Bilinear interpolation. Suitable for smooth fields (temperature, pressure, winds). |
| `conservative` | Flux-conserving remapping. Preserves integrated quantities (mass, energy). Required for budget-critical exchanges. |
| `nearest` | Nearest-neighbor assignment. Suitable for categorical or discontinuous fields (land use type, fire/no-fire mask). |
| `patch` | Higher-order patch recovery interpolation. Smooth and accurate but more expensive. |

If `regridding` is omitted and the shared dimensions have identical grids (same min, max, and grid_spacing), no regridding is needed. If grids differ and `regridding` is omitted, it is an error.

### 12.5 Interface Examples

#### 3D Atmosphere ↔ 2D Wildfire Surface

The atmosphere has 3 spatial dimensions (lon, lat, lev). The wildfire model has 2 (lon, lat). They share the horizontal dimensions; the vertical dimension is constrained at ground level.

```json
{
  "ground_surface": {
    "description": "Ground-level interface: atmosphere ↔ wildfire",
    "domains": ["atmosphere", "wildfire_surface"],
    "dimension_mapping": {
      "shared": {
        "atmosphere.lon": "wildfire_surface.lon",
        "atmosphere.lat": "wildfire_surface.lat"
      },
      "constraints": {
        "atmosphere.lev": { "value": "min" }
      }
    },
    "regridding": { "method": "bilinear" }
  }
}
```

Transferring `atmosphere.wind_u` through this interface: the 3D field is sliced at `lev=min` to produce a 2D field on the atmosphere's horizontal grid, then regridded to the wildfire grid via bilinear interpolation.

Transferring `wildfire.heat_flux` through this interface in reverse: the 2D field on the wildfire grid is regridded to the atmosphere's horizontal grid, then injected into the 3D atmospheric grid at `lev=min`.

#### 3D Atmosphere ↔ 3D Ocean

Both domains are 3D, but they share only the horizontal dimensions. The vertical dimensions are independent (atmospheric levels vs. ocean depth), and both are constrained at their interface values.

```json
{
  "sea_surface": {
    "description": "Air-sea interface: atmosphere ↔ ocean",
    "domains": ["atmosphere", "ocean"],
    "dimension_mapping": {
      "shared": {
        "atmosphere.lon": "ocean.lon",
        "atmosphere.lat": "ocean.lat"
      },
      "constraints": {
        "atmosphere.lev": { "value": "min" },
        "ocean.depth": { "value": "min" }
      }
    },
    "regridding": { "method": "conservative" }
  }
}
```

Transferring `atmosphere.surface_stress` through this interface: the 3D atmospheric field is sliced at `lev=min` to produce a 2D field, regridded from the atmosphere's horizontal grid to the ocean's horizontal grid (conservative), then injected into the ocean at `depth=min`.

#### 1D Column ↔ 3D Atmosphere

A 1D column model (e.g., vertical turbulence parameterization) coupled to a 3D atmosphere. The column model has one spatial dimension (height); the interface constrains the atmospheric horizontal coordinates to a specific column.

```json
{
  "observation_column": {
    "description": "Single column extracted from 3D atmosphere",
    "domains": ["atmosphere", "column_model"],
    "dimension_mapping": {
      "shared": {
        "atmosphere.lev": "column_model.z"
      },
      "constraints": {
        "atmosphere.lon": { "value": -118.0 },
        "atmosphere.lat": { "value": 34.0 }
      }
    }
  }
}
```

---

## 13. Solver

The solver section specifies the `SolverStrategy` for time integration. In multi-domain configurations, the solver advances the entire coupled system; operator splitting (Strang or IMEX) handles the interaction between domains at each time step.

```json
{
  "solver": {
    "strategy": "strang_threads",
    "config": {
      "threads": 8,
      "stiff_algorithm": "Rosenbrock23",
      "timestep": 1800.0,
      "stiff_kwargs": {
        "abstol": 1e-6,
        "reltol": 1e-3
      },
      "nonstiff_algorithm": "Euler",
      "map_algorithm": "broadcast"
    }
  }
}
```

### 13.1 Solver Strategies

| Strategy | EarthSciML Type | Description |
|---|---|---|
| `strang_threads` | `SolverStrangThreads` | Strang splitting, parallelized |
| `strang_serial` | `SolverStrangSerial` | Strang splitting, serial |
| `imex` | `SolverIMEX` | Implicit-explicit time integration |

---

## 14. Complete Examples

### 14.1 Single-Domain: Atmospheric Chemistry with Advection

A minimal but complete `.esm` file representing atmospheric chemistry with advection:

```json
{
  "esm": "0.1.0",
  "metadata": {
    "name": "MinimalChemAdvection",
    "description": "O3-NO-NO2 chemistry with advection and external meteorology",
    "authors": ["Chris Tessum"],
    "created": "2026-02-11T00:00:00Z"
  },

  "reaction_systems": {
    "SimpleOzone": {
      "coupletype": "SimpleOzoneCoupler",
      "reference": { "notes": "Minimal O3-NOx photochemical cycle" },
      "species": {
        "O3":  { "units": "mol/mol", "default": 40e-9,  "description": "Ozone" },
        "NO":  { "units": "mol/mol", "default": 0.1e-9, "description": "Nitric oxide" },
        "NO2": { "units": "mol/mol", "default": 1.0e-9, "description": "Nitrogen dioxide" }
      },
      "parameters": {
        "T":    { "units": "K", "default": 298.15, "description": "Temperature" },
        "M":    { "units": "molec/cm^3", "default": 2.46e19, "description": "Air number density" },
        "jNO2": { "units": "1/s", "default": 0.005, "description": "NO2 photolysis rate" }
      },
      "reactions": [
        {
          "id": "R1",
          "name": "NO_O3",
          "substrates": [
            { "species": "NO", "stoichiometry": 1 },
            { "species": "O3", "stoichiometry": 1 }
          ],
          "products": [
            { "species": "NO2", "stoichiometry": 1 }
          ],
          "rate": { "op": "*", "args": [1.8e-12, { "op": "exp", "args": [{ "op": "/", "args": [-1370, "T"] }] }, "M"] }
        },
        {
          "id": "R2",
          "name": "NO2_photolysis",
          "substrates": [ { "species": "NO2", "stoichiometry": 1 } ],
          "products": [
            { "species": "NO", "stoichiometry": 1 },
            { "species": "O3", "stoichiometry": 1 }
          ],
          "rate": "jNO2"
        }
      ]
    }
  },

  "models": {
    "Advection": {
      "reference": { "notes": "First-order advection" },
      "variables": {
        "u_wind": { "type": "parameter", "units": "m/s", "default": 0.0 },
        "v_wind": { "type": "parameter", "units": "m/s", "default": 0.0 }
      },
      "equations": [
        {
          "lhs": { "op": "D", "args": ["_var"], "wrt": "t" },
          "rhs": {
            "op": "+", "args": [
              { "op": "*", "args": [{ "op": "-", "args": ["u_wind"] }, { "op": "grad", "args": ["_var"], "dim": "x" }] },
              { "op": "*", "args": [{ "op": "-", "args": ["v_wind"] }, { "op": "grad", "args": ["_var"], "dim": "y" }] }
            ]
          }
        }
      ]
    }
  },

  "data_loaders": {
    "GEOSFP": {
      "type": "gridded_data",
      "loader_id": "GEOSFP",
      "config": { "resolution": "0.25x0.3125_NA", "coord_defaults": { "lat": 34.0, "lev": 1 } },
      "provides": {
        "u": { "units": "m/s", "description": "Eastward wind" },
        "v": { "units": "m/s", "description": "Northward wind" },
        "T": { "units": "K", "description": "Temperature" }
      }
    }
  },

  "coupling": [
    { "type": "operator_compose", "systems": ["SimpleOzone", "Advection"] },
    { "type": "variable_map", "from": "GEOSFP.T", "to": "SimpleOzone.T", "transform": "param_to_var" },
    { "type": "variable_map", "from": "GEOSFP.u", "to": "Advection.u_wind", "transform": "param_to_var" },
    { "type": "variable_map", "from": "GEOSFP.v", "to": "Advection.v_wind", "transform": "param_to_var" }
  ],

  "domains": {
    "default": {
      "temporal": { "start": "2024-05-01T00:00:00Z", "end": "2024-05-03T00:00:00Z" },
      "spatial": {
        "lon": { "min": -130.0, "max": -100.0, "grid_spacing": 0.3125, "units": "degrees" }
      },
      "coordinate_transforms": [
        { "id": "lonlat_to_meters", "dimensions": ["lon"] }
      ],
      "initial_conditions": { "type": "constant", "value": 1.0e-9 },
      "boundary_conditions": [
        { "type": "zero_gradient", "dimensions": ["lon"] }
      ],
      "element_type": "Float32"
    }
  },

  "solver": {
    "strategy": "strang_threads",
    "config": { "stiff_algorithm": "Rosenbrock23", "timestep": 1.0 }
  }
}
```

**Note:** When all models share a single domain, `"domain"` fields on individual models may be omitted — all models default to the sole domain.

### 14.2 Multi-Domain: Wildfire–Atmosphere–Ocean Coupling

A coupled system with a 3D atmospheric dynamics PDE, a 2D wildfire propagation PDE, a 3D ocean dynamics PDE, and 0D algebraic intermediaries. This example demonstrates mixed-dimension coupling through interfaces and pointwise lifting of 0D systems.

```json
{
  "esm": "0.1.0",
  "metadata": {
    "name": "WildfireAtmosphereOcean",
    "description": "Coupled wildfire-atmosphere-ocean system with 0D parameterizations",
    "authors": ["EarthSciML"],
    "created": "2026-04-08T00:00:00Z"
  },

  "models": {
    "AtmosphericDynamics": {
      "domain": "atmosphere",
      "reference": { "notes": "Simplified 3D atmospheric dynamics" },
      "variables": {
        "T": { "type": "state", "units": "K", "default": 288.0, "description": "Temperature" },
        "wind_u": { "type": "state", "units": "m/s", "default": 0.0, "description": "Eastward wind" },
        "wind_v": { "type": "state", "units": "m/s", "default": 0.0, "description": "Northward wind" },
        "q_heat": { "type": "parameter", "units": "K/s", "default": 0.0, "description": "External heating rate" }
      },
      "equations": [
        {
          "lhs": { "op": "D", "args": ["T"], "wrt": "t" },
          "rhs": {
            "op": "+",
            "args": [
              { "op": "*", "args": [{ "op": "-", "args": ["wind_u"] }, { "op": "grad", "args": ["T"], "dim": "x" }] },
              { "op": "*", "args": [{ "op": "-", "args": ["wind_v"] }, { "op": "grad", "args": ["T"], "dim": "y" }] },
              "q_heat"
            ]
          }
        }
      ]
    },

    "WildfirePropagation": {
      "domain": "wildfire_surface",
      "reference": { "notes": "Level-set wildfire spread model" },
      "variables": {
        "phi": { "type": "state", "units": "1", "default": 1.0, "description": "Level-set function (phi<0 = burned)" },
        "R_spread": { "type": "parameter", "units": "m/s", "default": 0.0, "description": "Fire spread rate" },
        "fuel": { "type": "state", "units": "kg/m^2", "default": 10.0, "description": "Fuel load" },
        "heat_release": {
          "type": "observed", "units": "W/m^2",
          "expression": {
            "op": "*",
            "args": [
              "R_spread", "fuel",
              { "op": "ifelse", "args": [
                { "op": "<", "args": ["phi", 0] }, 18000.0, 0.0
              ]}
            ]
          },
          "description": "Heat release rate at fire front"
        }
      },
      "equations": [
        {
          "lhs": { "op": "D", "args": ["phi"], "wrt": "t" },
          "rhs": {
            "op": "*",
            "args": [
              { "op": "-", "args": ["R_spread"] },
              { "op": "sqrt", "args": [
                { "op": "+", "args": [
                  { "op": "^", "args": [{ "op": "grad", "args": ["phi"], "dim": "x" }, 2] },
                  { "op": "^", "args": [{ "op": "grad", "args": ["phi"], "dim": "y" }, 2] }
                ]}
              ]}
            ]
          }
        },
        {
          "lhs": { "op": "D", "args": ["fuel"], "wrt": "t" },
          "rhs": {
            "op": "ifelse",
            "args": [
              { "op": "<", "args": ["phi", 0] },
              { "op": "*", "args": [-0.01, "fuel"] },
              0.0
            ]
          }
        }
      ]
    },

    "FireSpreadCalculator": {
      "domain": null,
      "reference": { "notes": "Rothermel-style wind-driven spread rate (algebraic)" },
      "variables": {
        "wind_u": { "type": "parameter", "units": "m/s", "default": 0.0, "description": "Eastward wind at ground level" },
        "wind_v": { "type": "parameter", "units": "m/s", "default": 0.0, "description": "Northward wind at ground level" },
        "R_base": { "type": "parameter", "units": "m/s", "default": 0.05, "description": "Base spread rate (no wind)" },
        "wind_factor": { "type": "parameter", "units": "1", "default": 0.3, "description": "Wind enhancement coefficient" },
        "wind_speed": {
          "type": "observed", "units": "m/s",
          "expression": {
            "op": "sqrt",
            "args": [{ "op": "+", "args": [
              { "op": "^", "args": ["wind_u", 2] },
              { "op": "^", "args": ["wind_v", 2] }
            ]}]
          },
          "description": "Wind speed magnitude"
        },
        "spread_rate": {
          "type": "observed", "units": "m/s",
          "expression": {
            "op": "*",
            "args": [
              "R_base",
              { "op": "+", "args": [1.0, { "op": "*", "args": ["wind_factor", "wind_speed"] }] }
            ]
          },
          "description": "Wind-enhanced fire spread rate"
        }
      },
      "equations": []
    },

    "OceanDynamics": {
      "domain": "ocean",
      "reference": { "notes": "Simplified 3D ocean dynamics" },
      "variables": {
        "SST": { "type": "state", "units": "K", "default": 290.0, "description": "Sea surface temperature" },
        "u_ocean": { "type": "state", "units": "m/s", "default": 0.0, "description": "Eastward ocean current" },
        "surface_heat_flux": { "type": "parameter", "units": "W/m^2", "default": 0.0, "description": "Net heat flux from atmosphere" }
      },
      "equations": [
        {
          "lhs": { "op": "D", "args": ["SST"], "wrt": "t" },
          "rhs": {
            "op": "+",
            "args": [
              { "op": "*", "args": [{ "op": "-", "args": ["u_ocean"] }, { "op": "grad", "args": ["SST"], "dim": "x" }] },
              { "op": "/", "args": ["surface_heat_flux", 4.18e6] }
            ]
          }
        }
      ]
    },

    "AirSeaFluxCalculator": {
      "domain": null,
      "reference": { "notes": "Bulk formula for air-sea heat exchange (algebraic)" },
      "variables": {
        "T_atm": { "type": "parameter", "units": "K", "default": 288.0, "description": "Atmospheric temperature at surface" },
        "SST": { "type": "parameter", "units": "K", "default": 290.0, "description": "Sea surface temperature" },
        "wind_speed": { "type": "parameter", "units": "m/s", "default": 5.0, "description": "Surface wind speed" },
        "C_H": { "type": "parameter", "units": "1", "default": 1.2e-3, "description": "Heat transfer coefficient" },
        "rho_air": { "type": "parameter", "units": "kg/m^3", "default": 1.225, "description": "Air density" },
        "c_p": { "type": "parameter", "units": "J/(kg*K)", "default": 1005.0, "description": "Specific heat of air" },
        "sensible_heat_flux": {
          "type": "observed", "units": "W/m^2",
          "expression": {
            "op": "*",
            "args": ["rho_air", "c_p", "C_H", "wind_speed",
              { "op": "-", "args": ["T_atm", "SST"] }
            ]
          },
          "description": "Sensible heat flux (positive = ocean to atmosphere)"
        }
      },
      "equations": []
    }
  },

  "domains": {
    "atmosphere": {
      "temporal": { "start": "2024-07-15T00:00:00Z", "end": "2024-07-16T00:00:00Z" },
      "spatial": {
        "lon": { "min": -120.0, "max": -115.0, "units": "degrees", "grid_spacing": 0.1 },
        "lat": { "min": 33.0, "max": 36.0, "units": "degrees", "grid_spacing": 0.1 },
        "lev": { "min": 0.0, "max": 20000.0, "units": "m", "grid_spacing": 500.0 }
      },
      "coordinate_transforms": [{ "id": "lonlat_to_meters", "dimensions": ["lon", "lat"] }],
      "spatial_ref": "WGS84",
      "initial_conditions": { "type": "constant", "value": 0.0 },
      "boundary_conditions": [
        { "type": "zero_gradient", "dimensions": ["lon", "lat"] },
        { "type": "zero_gradient", "dimensions": ["lev"] }
      ],
      "element_type": "Float64"
    },
    "wildfire_surface": {
      "temporal": { "start": "2024-07-15T00:00:00Z", "end": "2024-07-16T00:00:00Z" },
      "spatial": {
        "lon": { "min": -119.0, "max": -117.0, "units": "degrees", "grid_spacing": 0.01 },
        "lat": { "min": 34.0, "max": 35.0, "units": "degrees", "grid_spacing": 0.01 }
      },
      "coordinate_transforms": [{ "id": "lonlat_to_meters", "dimensions": ["lon", "lat"] }],
      "spatial_ref": "WGS84",
      "initial_conditions": { "type": "constant", "value": 1.0 },
      "boundary_conditions": [
        { "type": "zero_gradient", "dimensions": ["lon", "lat"] }
      ],
      "element_type": "Float64"
    },
    "ocean": {
      "temporal": { "start": "2024-07-15T00:00:00Z", "end": "2024-07-16T00:00:00Z" },
      "spatial": {
        "lon": { "min": -120.0, "max": -115.0, "units": "degrees", "grid_spacing": 0.25 },
        "lat": { "min": 33.0, "max": 36.0, "units": "degrees", "grid_spacing": 0.25 },
        "depth": { "min": 0.0, "max": 5000.0, "units": "m", "grid_spacing": 50.0 }
      },
      "coordinate_transforms": [{ "id": "lonlat_to_meters", "dimensions": ["lon", "lat"] }],
      "spatial_ref": "WGS84",
      "initial_conditions": { "type": "constant", "value": 290.0 },
      "boundary_conditions": [
        { "type": "periodic", "dimensions": ["lon"] },
        { "type": "zero_gradient", "dimensions": ["lat", "depth"] }
      ],
      "element_type": "Float64"
    }
  },

  "interfaces": {
    "ground_surface": {
      "description": "Ground-level interface: atmosphere ↔ wildfire",
      "domains": ["atmosphere", "wildfire_surface"],
      "dimension_mapping": {
        "shared": {
          "atmosphere.lon": "wildfire_surface.lon",
          "atmosphere.lat": "wildfire_surface.lat"
        },
        "constraints": {
          "atmosphere.lev": { "value": "min" }
        }
      },
      "regridding": { "method": "bilinear" }
    },
    "sea_surface": {
      "description": "Air-sea interface: atmosphere ↔ ocean",
      "domains": ["atmosphere", "ocean"],
      "dimension_mapping": {
        "shared": {
          "atmosphere.lon": "ocean.lon",
          "atmosphere.lat": "ocean.lat"
        },
        "constraints": {
          "atmosphere.lev": { "value": "min" },
          "ocean.depth": { "value": "min" }
        }
      },
      "regridding": { "method": "conservative" }
    }
  },

  "coupling": [
    {
      "type": "variable_map",
      "from": "AtmosphericDynamics.wind_u",
      "to": "FireSpreadCalculator.wind_u",
      "transform": "param_to_var",
      "interface": "ground_surface",
      "lifting": "pointwise",
      "description": "Ground-level u-wind to fire spread calculator"
    },
    {
      "type": "variable_map",
      "from": "AtmosphericDynamics.wind_v",
      "to": "FireSpreadCalculator.wind_v",
      "transform": "param_to_var",
      "interface": "ground_surface",
      "lifting": "pointwise",
      "description": "Ground-level v-wind to fire spread calculator"
    },
    {
      "type": "variable_map",
      "from": "FireSpreadCalculator.spread_rate",
      "to": "WildfirePropagation.R_spread",
      "transform": "param_to_var",
      "lifting": "pointwise",
      "description": "Calculated spread rate drives wildfire propagation"
    },
    {
      "type": "variable_map",
      "from": "WildfirePropagation.heat_release",
      "to": "AtmosphericDynamics.q_heat",
      "transform": "param_to_var",
      "interface": "ground_surface",
      "factor": 2.4e-7,
      "description": "Wildfire heat injection into lowest atmospheric layer (W/m^2 → K/s)"
    },
    {
      "type": "variable_map",
      "from": "AtmosphericDynamics.T",
      "to": "AirSeaFluxCalculator.T_atm",
      "transform": "param_to_var",
      "interface": "sea_surface",
      "lifting": "pointwise",
      "description": "Surface air temperature to air-sea flux calculator"
    },
    {
      "type": "variable_map",
      "from": "OceanDynamics.SST",
      "to": "AirSeaFluxCalculator.SST",
      "transform": "param_to_var",
      "interface": "sea_surface",
      "lifting": "pointwise",
      "description": "Sea surface temperature to air-sea flux calculator"
    },
    {
      "type": "variable_map",
      "from": "AirSeaFluxCalculator.sensible_heat_flux",
      "to": "OceanDynamics.surface_heat_flux",
      "transform": "param_to_var",
      "lifting": "pointwise",
      "description": "Calculated heat flux drives ocean surface temperature"
    }
  ],

  "solver": {
    "strategy": "strang_threads",
    "config": {
      "stiff_algorithm": "Rosenbrock23",
      "timestep": 60.0,
      "nonstiff_algorithm": "Euler"
    }
  }
}
```

This example demonstrates:
- **3D → 2D coupling** via the `ground_surface` interface (atmospheric winds → fire spread)
- **2D → 3D coupling** via the same interface in reverse (wildfire heat → atmosphere)
- **3D → 3D coupling** via the `sea_surface` interface (atmosphere ↔ ocean, both constrained to surface)
- **0D intermediaries** with `"lifting": "pointwise"` (`FireSpreadCalculator`, `AirSeaFluxCalculator`)
- **Cross-domain 0D algebraic systems** that take inputs from one domain and produce outputs for another

---

## 15. Design Principles

### Full specification is mandatory for models and reactions

Every equation, species, reaction, parameter, and variable must be present in the `.esm` file. This guarantees:

- A parser in **any language** can reconstruct the mathematical system
- Models are **reproducible** without access to specific software versions
- The format is **archival** — it remains meaningful years later even if packages change
- **Diffs are meaningful** — every change to the science is visible in version control

### Data loaders and operators are registered by reference

These are runtime-specific: they involve I/O, numerical discretization schemes, GPU kernels, and platform code that cannot be meaningfully serialized as math. The `.esm` file declares *what* they provide and *what* they need, but delegates *how* to the runtime.

### Expression AST over string math

String-based math (LaTeX, Mathematica, sympy) requires building a parser for every target language. The JSON AST is immediately parseable everywhere and supports programmatic transformation.

### Reaction systems are distinct from ODE models

Reaction networks are a higher-level, more constrained representation. Keeping them separate from raw ODE models:

- Preserves **chemical meaning** (stoichiometry, mass action semantics)
- Enables **analysis** (conservation laws, stoichiometric matrices, deficiency theory) without equation manipulation
- Maps naturally to **multiple simulation types** (ODE, SDE, jump/Gillespie) from the same declaration
- Avoids the error-prone manual derivation of ODEs from reaction networks

### Coupling is first-class

The composition rules are arguably more important than the individual models, since they capture the scientific decisions about how processes interact. Making coupling explicit and inspectable is essential for understanding and reproducing complex Earth system models.

### Interfaces separate geometry from physics

Cross-domain coupling requires two distinct concerns: the *geometric relationship* between domains (shared dimensions, constraints, regridding) and the *physical coupling* (which variables connect, how they transform). Interfaces capture the geometry once; coupling entries reference interfaces and specify the physics. This separation means:

- The same interface can be reused by many coupling entries (e.g., dozens of variables exchanged at the sea surface)
- Geometric details don't clutter individual coupling rules
- Changes to grid resolution or regridding strategy propagate automatically to all couplings that use the interface

### 0D systems are first-class coupling intermediaries

Many physical parameterizations are algebraic or ODE systems with no intrinsic spatial dimensions — they compute pointwise relationships (e.g., wind speed → fire spread rate, bulk surface fluxes). Rather than embedding these calculations in the spatial model's equations, they are declared as separate 0D models with explicit coupling. This preserves modularity: the same 0D parameterization can be swapped, tested independently, or coupled to different spatial domains.

### Coupled systems flatten to a single equation system

The composition of multiple models, reaction systems, and data loaders resolves to a **single flat equation system** with dot-namespaced variables (`Atmosphere.Chemistry.O3`). This is not merely a convenience — it is the canonical intermediate representation that all downstream operations (simulation, validation, graph construction) consume. Dot-namespacing preserves provenance (you can always trace a variable back to its originating component) while producing a system that maps directly to a single solver object (MTK `ODESystem` or `PDESystem` in Julia, a single ODE integrator call in Python). The separation between modular component definitions (in the `.esm` file) and the unified flat system (produced by flattening) mirrors the distinction between source code and compiled output: the file is for humans and version control, the flattened system is for machines and solvers.

---

## 16. Future Considerations

- **Formal JSON Schema** — A `.json` schema file for automated validation
- **Binary variant** — MessagePack or CBOR for large mechanisms (hundreds of species/reactions)
- **Semantic diffing** — CLI tools that understand `.esm` structure for meaningful diffs
- **Stoichiometric matrix export** — Direct computation of substrate/product/net stoichiometry matrices from the reaction system section
- **Unit validation** — Tooling for dimensional analysis across coupled systems
- **Provenance hashing** — Content-addressable hashing of model components for reproducibility
- **SBML interop** — Import/export to Systems Biology Markup Language for broader compatibility
- **Web editor** — Visual model composition interface producing `.esm` files
