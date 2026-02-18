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
  "domain": { ... },
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
| `domain` | | Spatial/temporal domain specification |
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
| `coupletype` | | Coupling type name (maps to EarthSciML `:coupletype` metadata). Used by `couple2` dispatch. |
| `reference` | | Academic citation: `doi`, `citation`, `url`, `notes` |
| `variables` | ✓ | All variables, keyed by name |
| `equations` | ✓ | Array of `{lhs, rhs}` equation objects |
| `discrete_events` | | Discrete events (see Section 5.3) |
| `continuous_events` | | Continuous events (see Section 5.2) |
| `subsystems` | | Named child models (subsystems), keyed by unique identifier. Enables hierarchical composition — variables in subsystems are referenced via dot notation (see Section 4.3). |

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
| `coupletype` | | Coupling type name for `couple2` dispatch |
| `reference` | | Academic citation |
| `species` | ✓ | Named reactive species with units, defaults, descriptions |
| `parameters` | ✓ | Named parameters (rate constants, temperature, photolysis rates, etc.) |
| `reactions` | ✓ | Array of reaction definitions |
| `constraint_equations` | | Additional algebraic or ODE constraints (in expression AST form) |
| `discrete_events` | | Discrete events (see Section 5.3) |
| `continuous_events` | | Continuous events (see Section 5.2) |
| `subsystems` | | Named child reaction systems (subsystems), keyed by unique identifier. Enables hierarchical composition — variables in subsystems are referenced via dot notation (see Section 4.3). |

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

---

## 11. Domain

The domain section corresponds to `EarthSciMLBase.DomainInfo`. It specifies the spatiotemporal extent, discretization, coordinate system, and boundary/initial conditions.

```json
{
  "domain": {
    "independent_variable": "t",

    "temporal": {
      "start": "2024-05-01T00:00:00Z",
      "end": "2024-05-03T00:00:00Z",
      "reference_time": "2024-05-01T00:00:00Z"
    },

    "spatial": {
      "lon": {
        "min": -130.0,
        "max": -60.0,
        "units": "degrees",
        "grid_spacing": 0.3125
      },
      "lat": {
        "min": 20.0,
        "max": 55.0,
        "units": "degrees",
        "grid_spacing": 0.25
      },
      "lev": {
        "min": 1,
        "max": 72,
        "units": "level",
        "grid_spacing": 1
      }
    },

    "coordinate_transforms": [
      {
        "id": "lonlat_to_meters",
        "description": "Convert lon/lat degrees to x/y meters assuming spherical Earth",
        "dimensions": ["lon", "lat"]
      }
    ],

    "spatial_ref": "WGS84",

    "initial_conditions": {
      "type": "constant",
      "value": 0.0
    },

    "boundary_conditions": [
      {
        "type": "zero_gradient",
        "dimensions": ["lon", "lat"]
      },
      {
        "type": "constant",
        "dimensions": ["lev"],
        "value": 0.0
      }
    ],

    "element_type": "Float32",
    "array_type": "Array"
  }
}
```

### 11.1 Initial Condition Types

| Type | Fields | Description |
|---|---|---|
| `constant` | `value` | Uniform initial value for all state variables |
| `per_variable` | `values: {var: value}` | Per-variable initial values |
| `from_file` | `path`, `format` | Load from external file |

### 11.2 Boundary Condition Types

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

**Note:** `dirichlet` and `neumann` are alternative names for `constant` and `zero_gradient` respectively, following standard PDE nomenclature. The Robin boundary condition provides a general mixed formulation where appropriate coefficients can recover Dirichlet (α=1, β=0) or Neumann (α=0, β=1) conditions as special cases.

---

## 12. Solver

The solver section specifies the `SolverStrategy` for time integration.

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

### 12.1 Solver Strategies

| Strategy | EarthSciML Type | Description |
|---|---|---|
| `strang_threads` | `SolverStrangThreads` | Strang splitting, parallelized |
| `strang_serial` | `SolverStrangSerial` | Strang splitting, serial |
| `imex` | `SolverIMEX` | Implicit-explicit time integration |

---

## 13. Complete Example

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

  "domain": {
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
  },

  "solver": {
    "strategy": "strang_threads",
    "config": { "stiff_algorithm": "Rosenbrock23", "timestep": 1.0 }
  }
}
```

---

## 14. Design Principles

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

---

## 15. Future Considerations

- **Formal JSON Schema** — A `.json` schema file for automated validation
- **Binary variant** — MessagePack or CBOR for large mechanisms (hundreds of species/reactions)
- **Semantic diffing** — CLI tools that understand `.esm` structure for meaningful diffs
- **Stoichiometric matrix export** — Direct computation of substrate/product/net stoichiometry matrices from the reaction system section
- **Unit validation** — Tooling for dimensional analysis across coupled systems
- **Provenance hashing** — Content-addressable hashing of model components for reproducibility
- **SBML interop** — Import/export to Systems Biology Markup Language for broader compatibility
- **Web editor** — Visual model composition interface producing `.esm` files
