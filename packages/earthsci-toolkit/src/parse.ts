/**
 * ESM Format JSON Parsing
 *
 * Provides functionality to load and validate ESM files from JSON strings or objects.
 * Separates concerns: JSON parsing → schema validation → type coercion.
 */

import Ajv, { ErrorObject, ValidateFunction } from 'ajv'
import addFormats from 'ajv-formats'
import type { EsmFile, Expression, CouplingEntry } from './types.js'
import { validateUnits } from './units.js'
import { isNumericLiteral, losslessJsonParse } from './numeric-literal.js'

/**
 * Schema validation error with JSON Pointer path
 */
export interface SchemaError {
  /** JSON Pointer path to the error location */
  path: string
  /** Human-readable error message */
  message: string
  /** AJV validation keyword that failed */
  keyword: string
}

/**
 * Parse error - thrown when JSON parsing fails
 */
export class ParseError extends Error {
  constructor(message: string, public originalError?: Error) {
    super(message)
    this.name = 'ParseError'
  }
}

/**
 * Schema validation error - thrown when schema validation fails
 */
export class SchemaValidationError extends Error {
  constructor(message: string, public errors: SchemaError[]) {
    super(message)
    this.name = 'SchemaValidationError'
  }
}

/**
 * Grid-generator validation error — thrown for the post-schema checks in
 * RFC §6.5 (loader references must resolve; 'builtin' names must be from
 * the canonical closed set). Uses `code` to identify the specific failure
 * class (E_UNKNOWN_LOADER, E_UNKNOWN_BUILTIN).
 */
export class GridValidationError extends Error {
  constructor(message: string, public code: 'E_UNKNOWN_LOADER' | 'E_UNKNOWN_BUILTIN') {
    super(message)
    this.name = 'GridValidationError'
  }
}

/**
 * Closed set of canonical grid builtins (RFC §6.4.1). Adding a new name
 * here is a minor version bump.
 */
const KNOWN_GRID_BUILTINS = new Set<string>([
  'gnomonic_c6_neighbors',
  'gnomonic_c6_d4_action',
])

// Embedded ESM schema - browser-compatible (no file system access required)
const schema = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://earthsciml.org/schemas/esm/0.1.0/esm.schema.json",
  "title": "ESM Format",
  "description": "EarthSciML Serialization Format (v0.1.0) — a language-agnostic JSON format for Earth system model components, their composition, and runtime configuration.",
  "type": "object",
  "required": ["esm", "metadata"],
  "additionalProperties": false,
  "anyOf": [
    { "required": ["models"] },
    { "required": ["reaction_systems"] }
  ],
  "properties": {
    "esm": {
      "type": "string",
      "enum": ["0.1.0", "0.2.0"],
      "description": "Format version string (semver). v0.2.0 adds model-level boundary_conditions (RFC §9)."
    },
    "metadata": { "$ref": "#/$defs/Metadata" },
    "models": {
      "type": "object",
      "description": "ODE-based model components, keyed by unique identifier.",
      "additionalProperties": { "$ref": "#/$defs/Model" }
    },
    "reaction_systems": {
      "type": "object",
      "description": "Reaction network components, keyed by unique identifier.",
      "additionalProperties": { "$ref": "#/$defs/ReactionSystem" }
    },
    "data_loaders": {
      "type": "object",
      "description": "External data source registrations (by reference).",
      "additionalProperties": { "$ref": "#/$defs/DataLoader" }
    },
    "operators": {
      "type": "object",
      "description": "Registered runtime operators (by reference).",
      "additionalProperties": { "$ref": "#/$defs/Operator" }
    },
    "registered_functions": {
      "type": "object",
      "description": "Registry of named pure functions invoked inside expressions via the 'call' op (esm-spec §9.2).",
      "additionalProperties": { "$ref": "#/$defs/RegisteredFunction" }
    },
    "coupling": {
      "type": "array",
      "description": "Composition and coupling rules.",
      "items": { "$ref": "#/$defs/CouplingEntry" }
    },
    "domains": {
      "type": "object",
      "description": "Named spatiotemporal domains, keyed by unique identifier.",
      "additionalProperties": { "$ref": "#/$defs/Domain" }
    },
    "interfaces": {
      "type": "object",
      "description": "Named coupling interfaces between domains.",
      "additionalProperties": { "$ref": "#/$defs/Interface" }
    },
    "grids": {
      "type": "object",
      "description": "Named discretization grids (v0.2.0). Each entry declares a cartesian/unstructured/cubed_sphere topology with dimensions, staggering locations, metric arrays, and (for unstructured/cubed-sphere) connectivity tables. See docs/rfcs/discretization.md §6.",
      "additionalProperties": { "$ref": "#/$defs/Grid" }
    }
  },

  "$defs": {

    "Metadata": {
      "type": "object",
      "description": "Authorship, provenance, and description.",
      "required": ["name"],
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": "string",
          "description": "Short identifier for the model configuration."
        },
        "description": { "type": "string" },
        "authors": {
          "type": "array",
          "items": { "type": "string" }
        },
        "license": { "type": "string" },
        "created": {
          "type": "string",
          "description": "ISO 8601 creation timestamp or date.",
          "anyOf": [
            { "format": "date-time" },
            { "format": "date" }
          ]
        },
        "modified": {
          "type": "string",
          "description": "ISO 8601 last-modified timestamp or date.",
          "anyOf": [
            { "format": "date-time" },
            { "format": "date" }
          ]
        },
        "tags": {
          "type": "array",
          "items": { "type": "string" }
        },
        "references": {
          "type": "array",
          "items": { "$ref": "#/$defs/Reference" }
        }
      }
    },

    "Reference": {
      "type": "object",
      "description": "Academic citation or data source reference.",
      "additionalProperties": false,
      "properties": {
        "doi": {
          "type": "string",
          "pattern": "^10\\.\\d{4,}/"
        },
        "citation": { "type": "string" },
        "url": { "type": "string", "format": "uri" },
        "notes": { "type": "string" }
      }
    },

    "Expression": {
      "description": "Mathematical expression: a number literal, a variable/parameter reference string, or an operator node.",
      "oneOf": [
        { "type": "number" },
        { "type": "string" },
        { "$ref": "#/$defs/ExpressionNode" }
      ]
    },

    "ExpressionNode": {
      "type": "object",
      "description": "An operation in the expression AST.",
      "required": ["op", "args"],
      "properties": {
        "op": {
          "type": "string",
          "description": "Operator name.",
          "enum": [
            "+", "-", "*", "/", "^",
            "D", "grad", "div", "laplacian",
            "exp", "log", "log10", "sqrt", "abs",
            "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
            "min", "max", "floor", "ceil",
            "ifelse",
            ">", "<", ">=", "<=", "==", "!=",
            "and", "or", "not",
            "Pre",
            "sign",
            "index",
            "call",
            "bc"
          ]
        },
        "args": {
          "type": "array",
          "items": { "$ref": "#/$defs/Expression" },
          "minItems": 1
        },
        "wrt": {
          "type": "string",
          "description": "Differentiation variable for D operator (e.g., \"t\")."
        },
        "dim": {
          "type": "string",
          "description": "Spatial dimension for grad operator (e.g., \"x\", \"y\", \"z\")."
        },
        "handler_id": {
          "type": "string",
          "description": "For call: id of a registered function (esm-spec §4.4)."
        },
        "kind": {
          "type": "string",
          "enum": ["constant", "dirichlet", "neumann", "robin", "zero_gradient", "periodic", "flux_contrib"],
          "description": "For the 'bc' pattern-match op: BC kind to match (RFC §9.2)."
        },
        "side": {
          "type": "string",
          "description": "For the 'bc' pattern-match op: BC side to match (RFC §9.2)."
        }
      },
      "additionalProperties": false,
      "allOf": [
        {
          "if": { "properties": { "op": { "const": "call" } }, "required": ["op"] },
          "then": { "required": ["handler_id"] }
        }
      ]
    },

    "Equation": {
      "type": "object",
      "description": "An equation: lhs = rhs (or lhs ~ rhs in MTK notation).",
      "required": ["lhs", "rhs"],
      "additionalProperties": false,
      "properties": {
        "lhs": { "$ref": "#/$defs/Expression" },
        "rhs": { "$ref": "#/$defs/Expression" },
        "_comment": { "type": "string" }
      }
    },

    "AffectEquation": {
      "type": "object",
      "description": "An affect equation in an event: lhs is the target variable (string), rhs is an expression.",
      "required": ["lhs", "rhs"],
      "additionalProperties": false,
      "properties": {
        "lhs": {
          "type": "string",
          "description": "Target variable name (value after the event)."
        },
        "rhs": {
          "$ref": "#/$defs/Expression",
          "description": "Expression for the new value. Use Pre(var) to reference pre-event values."
        }
      }
    },

    "ContinuousEvent": {
      "type": "object",
      "description": "Fires when a condition expression crosses zero (root-finding). Maps to MTK SymbolicContinuousCallback.",
      "required": ["conditions", "affects"],
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": "string",
          "description": "Human-readable identifier."
        },
        "conditions": {
          "type": "array",
          "description": "Expressions that trigger the event when they cross zero.",
          "items": { "$ref": "#/$defs/Expression" },
          "minItems": 1
        },
        "affects": {
          "type": "array",
          "description": "Affect equations applied on positive-going zero crossings (or both directions if affect_neg is absent). Empty array for pure detection.",
          "items": { "$ref": "#/$defs/AffectEquation" }
        },
        "affect_neg": {
          "description": "Separate affects for negative-going zero crossings. If null or absent, affects is used for both directions.",
          "oneOf": [
            { "type": "null" },
            {
              "type": "array",
              "items": { "$ref": "#/$defs/AffectEquation" }
            }
          ]
        },
        "root_find": {
          "type": "string",
          "description": "Root-finding direction.",
          "enum": ["left", "right", "all"],
          "default": "left"
        },
        "reinitialize": {
          "type": "boolean",
          "description": "Whether to reinitialize the system after the event.",
          "default": false
        },
        "description": { "type": "string" }
      }
    },

    "DiscreteEventTrigger": {
      "description": "Trigger specification for a discrete event.",
      "oneOf": [
        {
          "type": "object",
          "description": "Fires when the boolean expression is true at the end of a timestep.",
          "required": ["type", "expression"],
          "additionalProperties": false,
          "properties": {
            "type": { "const": "condition" },
            "expression": { "$ref": "#/$defs/Expression" }
          }
        },
        {
          "type": "object",
          "description": "Fires every interval time units.",
          "required": ["type", "interval"],
          "additionalProperties": false,
          "properties": {
            "type": { "const": "periodic" },
            "interval": {
              "type": "number",
              "exclusiveMinimum": 0,
              "description": "Interval in simulation time units."
            },
            "initial_offset": {
              "type": "number",
              "description": "Offset from t=0 for the first firing.",
              "default": 0
            }
          }
        },
        {
          "type": "object",
          "description": "Fires at each specified time.",
          "required": ["type", "times"],
          "additionalProperties": false,
          "properties": {
            "type": { "const": "preset_times" },
            "times": {
              "type": "array",
              "items": { "type": "number" },
              "minItems": 1,
              "description": "Array of simulation times at which to fire."
            }
          }
        }
      ]
    },

    "FunctionalAffect": {
      "type": "object",
      "description": "A registered functional affect handler for complex event behavior that cannot be expressed symbolically.",
      "required": ["handler_id", "read_vars", "read_params"],
      "additionalProperties": false,
      "properties": {
        "handler_id": {
          "type": "string",
          "description": "Registered identifier for the affect implementation."
        },
        "read_vars": {
          "type": "array",
          "items": { "type": "string" },
          "description": "State variables accessed by the handler."
        },
        "read_params": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Parameters accessed by the handler."
        },
        "modified_params": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Parameters modified by the handler (implicitly discrete parameters)."
        },
        "config": {
          "type": "object",
          "description": "Handler-specific configuration.",
          "additionalProperties": true
        }
      }
    },

    "DiscreteEvent": {
      "type": "object",
      "description": "Fires when a boolean condition is true at end of a timestep, or at preset/periodic times. Maps to MTK SymbolicDiscreteCallback.",
      "required": ["trigger"],
      "additionalProperties": false,
      "properties": {
        "name": {
          "type": "string",
          "description": "Human-readable identifier."
        },
        "trigger": { "$ref": "#/$defs/DiscreteEventTrigger" },
        "affects": {
          "type": "array",
          "description": "Affect equations. Required unless functional_affect is used.",
          "items": { "$ref": "#/$defs/AffectEquation" }
        },
        "functional_affect": {
          "$ref": "#/$defs/FunctionalAffect",
          "description": "Registered functional affect handler (alternative to symbolic affects)."
        },
        "discrete_parameters": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Parameters modified by this event. Required when affects modify parameters rather than state variables."
        },
        "reinitialize": {
          "type": "boolean",
          "description": "Whether to reinitialize the system after the event."
        },
        "description": { "type": "string" }
      },
      "oneOf": [
        { "required": ["affects"] },
        { "required": ["functional_affect"] }
      ]
    },

    "ModelVariable": {
      "type": "object",
      "description": "A variable in an ODE/SDE model.",
      "required": ["type"],
      "additionalProperties": false,
      "properties": {
        "type": {
          "type": "string",
          "enum": ["state", "parameter", "observed", "brownian"],
          "description": "state = time-dependent unknown; parameter = externally set constant; observed = derived quantity; brownian = stochastic noise source (Wiener) that drives an SDE."
        },
        "units": { "type": "string" },
        "default": { "type": "number" },
        "description": { "type": "string" },
        "expression": {
          "$ref": "#/$defs/Expression",
          "description": "Defining expression for observed variables."
        },
        "shape": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Arrayed-variable shape: ordered dimension names from the enclosing model's domain.spatial."
        },
        "location": {
          "type": "string",
          "description": "Staggered-grid location tag (e.g., cell_center, edge_normal, vertex)."
        },
        "noise_kind": {
          "type": "string",
          "enum": ["wiener"],
          "default": "wiener",
          "description": "Brownian-only: kind of stochastic process."
        },
        "correlation_group": {
          "type": "string",
          "description": "Brownian-only: opaque tag grouping correlated noise sources."
        }
      },
      "allOf": [
        {
          "if": { "properties": { "type": { "const": "observed" } }, "required": ["type"] },
          "then": { "required": ["expression"] }
        },
        {
          "if": { "not": { "properties": { "type": { "const": "brownian" } }, "required": ["type"] } },
          "then": { "not": { "anyOf": [{ "required": ["noise_kind"] }, { "required": ["correlation_group"] }] } }
        }
      ]
    },

    "Model": {
      "type": "object",
      "description": "An ODE system — a fully specified set of time-dependent equations.",
      "required": ["variables", "equations"],
      "additionalProperties": false,
      "properties": {
        "domain": {
          "description": "Domain this model belongs to.",
          "oneOf": [
            { "type": "string" },
            { "type": "null" }
          ]
        },
        "coupletype": {
          "description": "Coupling type name for couple dispatch.",
          "oneOf": [
            { "type": "string" },
            { "type": "null" }
          ]
        },
        "reference": { "$ref": "#/$defs/Reference" },
        "variables": {
          "type": "object",
          "description": "All variables, keyed by name.",
          "additionalProperties": { "$ref": "#/$defs/ModelVariable" }
        },
        "equations": {
          "type": "array",
          "description": "Array of {lhs, rhs} equation objects.",
          "items": { "$ref": "#/$defs/Equation" }
        },
        "initialization_equations": {
          "type": "array",
          "items": { "$ref": "#/$defs/Equation" }
        },
        "guesses": {
          "type": "object",
          "additionalProperties": { "$ref": "#/$defs/Expression" }
        },
        "system_kind": {
          "type": "string",
          "enum": ["ode", "nonlinear", "sde", "pde"]
        },
        "discrete_events": {
          "type": "array",
          "items": { "$ref": "#/$defs/DiscreteEvent" }
        },
        "continuous_events": {
          "type": "array",
          "items": { "$ref": "#/$defs/ContinuousEvent" }
        },
        "subsystems": {
          "type": "object",
          "description": "Named child models (subsystems), keyed by unique identifier. Enables hierarchical model composition. Variables in subsystems are referenced via dot notation: \"ParentModel.ChildModel.var\".",
          "additionalProperties": { "$ref": "#/$defs/Model" }
        },
        "tolerance": { "$ref": "#/$defs/Tolerance" },
        "tests": {
          "type": "array",
          "items": { "$ref": "#/$defs/Test" }
        },
        "examples": {
          "type": "array",
          "items": { "$ref": "#/$defs/Example" }
        },
        "boundary_conditions": {
          "type": "object",
          "description": "Model-level boundary conditions keyed by user-supplied id (v0.2.0, RFC §9). Replaces the v0.1.0 domain-level list; old-style files emit E_DEPRECATED_DOMAIN_BC.",
          "additionalProperties": { "$ref": "#/$defs/ModelBoundaryCondition" }
        }
      }
    },

    "ModelBoundaryCondition": {
      "type": "object",
      "description": "Model-level boundary condition entry (v0.2.0, RFC §9.2).",
      "required": ["variable", "side", "kind"],
      "additionalProperties": false,
      "properties": {
        "variable": { "type": "string" },
        "side": { "type": "string" },
        "kind": {
          "type": "string",
          "enum": ["constant", "dirichlet", "neumann", "robin", "zero_gradient", "periodic", "flux_contrib"]
        },
        "value": {
          "oneOf": [
            { "type": "number" },
            { "type": "string" },
            { "$ref": "#/$defs/ExpressionNode" }
          ]
        },
        "robin_alpha": {
          "oneOf": [
            { "type": "number" },
            { "type": "string" },
            { "$ref": "#/$defs/ExpressionNode" }
          ]
        },
        "robin_beta": {
          "oneOf": [
            { "type": "number" },
            { "type": "string" },
            { "$ref": "#/$defs/ExpressionNode" }
          ]
        },
        "robin_gamma": {
          "oneOf": [
            { "type": "number" },
            { "type": "string" },
            { "$ref": "#/$defs/ExpressionNode" }
          ]
        },
        "face_coords": {
          "type": "array",
          "items": { "type": "string" }
        },
        "contributed_by": {
          "type": "object",
          "required": ["component"],
          "additionalProperties": false,
          "properties": {
            "component": { "type": "string" },
            "flux_sign": { "type": "string", "enum": ["+", "-"] }
          }
        },
        "description": { "type": "string" }
      }
    },

    "Species": {
      "type": "object",
      "description": "A reactive species in a reaction system.",
      "additionalProperties": false,
      "properties": {
        "units": { "type": "string" },
        "default": { "type": "number" },
        "description": { "type": "string" }
      }
    },

    "Parameter": {
      "type": "object",
      "description": "A parameter in a reaction system.",
      "additionalProperties": false,
      "properties": {
        "units": { "type": "string" },
        "default": { "type": "number" },
        "description": { "type": "string" }
      }
    },

    "StoichiometryEntry": {
      "type": "object",
      "description": "A species with its stoichiometric coefficient in a reaction.",
      "required": ["species", "stoichiometry"],
      "additionalProperties": false,
      "properties": {
        "species": { "type": "string" },
        "stoichiometry": {
          "type": "integer",
          "minimum": 1
        }
      }
    },

    "Reaction": {
      "type": "object",
      "description": "A single reaction in a reaction system.",
      "required": ["id", "substrates", "products", "rate"],
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique reaction identifier (e.g., \"R1\")."
        },
        "name": { "type": "string" },
        "substrates": {
          "description": "Array of {species, stoichiometry} or null for source reactions (∅ → X).",
          "oneOf": [
            { "type": "null" },
            {
              "type": "array",
              "items": { "$ref": "#/$defs/StoichiometryEntry" },
              "minItems": 1
            }
          ]
        },
        "products": {
          "description": "Array of {species, stoichiometry} or null for sink reactions (X → ∅).",
          "oneOf": [
            { "type": "null" },
            {
              "type": "array",
              "items": { "$ref": "#/$defs/StoichiometryEntry" },
              "minItems": 1
            }
          ]
        },
        "rate": {
          "$ref": "#/$defs/Expression",
          "description": "Rate expression: a parameter reference string, number, or expression AST."
        },
        "reference": { "$ref": "#/$defs/Reference" }
      }
    },

    "ReactionSystem": {
      "type": "object",
      "description": "A reaction network — declarative representation of chemical or biological reactions.",
      "required": ["species", "parameters", "reactions"],
      "additionalProperties": false,
      "properties": {
        "coupletype": {
          "description": "Coupling type name for couple dispatch.",
          "oneOf": [
            { "type": "string" },
            { "type": "null" }
          ]
        },
        "reference": { "$ref": "#/$defs/Reference" },
        "species": {
          "type": "object",
          "description": "Named reactive species.",
          "additionalProperties": { "$ref": "#/$defs/Species" }
        },
        "parameters": {
          "type": "object",
          "description": "Named parameters (rate constants, temperature, photolysis rates, etc.).",
          "additionalProperties": { "$ref": "#/$defs/Parameter" }
        },
        "reactions": {
          "type": "array",
          "description": "Array of reaction definitions.",
          "items": { "$ref": "#/$defs/Reaction" },
          "minItems": 1
        },
        "constraint_equations": {
          "type": "array",
          "description": "Additional algebraic or ODE constraints.",
          "items": { "$ref": "#/$defs/Equation" }
        },
        "discrete_events": {
          "type": "array",
          "items": { "$ref": "#/$defs/DiscreteEvent" }
        },
        "continuous_events": {
          "type": "array",
          "items": { "$ref": "#/$defs/ContinuousEvent" }
        },
        "subsystems": {
          "type": "object",
          "description": "Named child reaction systems (subsystems), keyed by unique identifier. Enables hierarchical system composition. Variables in subsystems are referenced via dot notation: \"ParentSystem.ChildSystem.species\".",
          "additionalProperties": { "$ref": "#/$defs/ReactionSystem" }
        },
        "tolerance": { "$ref": "#/$defs/Tolerance" },
        "tests": {
          "type": "array",
          "items": { "$ref": "#/$defs/Test" }
        },
        "examples": {
          "type": "array",
          "items": { "$ref": "#/$defs/Example" }
        }
      }
    },

    "DataLoaderSource": {
      "type": "object",
      "description": "File discovery configuration. Describes how to locate data files at runtime via URL templates with date/variable substitutions.",
      "required": ["url_template"],
      "additionalProperties": false,
      "properties": {
        "url_template": {
          "type": "string",
          "description": "Jinja-style URL template with substitutions. Supported: {date:<strftime>} (e.g. {date:%Y%m%d}), {var}, {sector}, {species}. Custom substitutions are allowed and the runtime must accept and pass them through."
        },
        "mirrors": {
          "type": "array",
          "description": "Ordered fallback URL templates. Runtime tries each in order, first is primary. Follows the same substitution grammar as url_template.",
          "items": { "type": "string" }
        }
      }
    },

    "DataLoaderTemporal": {
      "type": "object",
      "description": "Temporal coverage and record layout for a data source.",
      "additionalProperties": false,
      "properties": {
        "start": {
          "type": "string",
          "format": "date-time",
          "description": "ISO 8601 datetime — first timestamp available from this source."
        },
        "end": {
          "type": "string",
          "format": "date-time",
          "description": "ISO 8601 datetime — last timestamp available from this source."
        },
        "file_period": {
          "type": "string",
          "description": "ISO 8601 duration describing how much time one file covers (e.g., \"P1D\", \"P1M\", \"PT3H\")."
        },
        "frequency": {
          "type": "string",
          "description": "ISO 8601 duration describing spacing between samples within a file."
        },
        "records_per_file": {
          "oneOf": [
            { "type": "integer", "minimum": 1 },
            { "type": "string", "enum": ["auto"] }
          ],
          "description": "Number of time records per file. \"auto\" means read from file at runtime."
        },
        "time_variable": {
          "type": "string",
          "description": "Name of the time coordinate variable in the file. Used when records_per_file is absent or \"auto\". If both static declarations (records_per_file + frequency) and time_variable are present, the static declaration wins and time_variable is a fallback."
        }
      }
    },

    "DataLoaderStaggering": {
      "type": "object",
      "description": "Per-dimension grid staggering (centered or edge-aligned).",
      "additionalProperties": {
        "type": "string",
        "enum": ["center", "edge"]
      }
    },

    "DataLoaderSpatial": {
      "type": "object",
      "description": "Spatial grid description for a data source.",
      "required": ["crs", "grid_type"],
      "additionalProperties": false,
      "properties": {
        "crs": {
          "type": "string",
          "description": "Coordinate reference system as a PROJ string or EPSG code."
        },
        "grid_type": {
          "type": "string",
          "enum": [
            "latlon",
            "lambert_conformal",
            "mercator",
            "polar_stereographic",
            "rotated_pole",
            "unstructured"
          ],
          "description": "Structural grid family. Use \"unstructured\" for mesh/point datasets."
        },
        "staggering": { "$ref": "#/$defs/DataLoaderStaggering" },
        "resolution": {
          "type": "object",
          "description": "Per-dimension resolution in native CRS units. Optional; some datasets only know this at runtime.",
          "additionalProperties": { "type": "number" }
        },
        "extent": {
          "type": "object",
          "description": "Per-dimension [min, max] extent in native CRS units. Optional; runtime can infer from files.",
          "additionalProperties": {
            "type": "array",
            "items": { "type": "number" },
            "minItems": 2,
            "maxItems": 2
          }
        }
      }
    },

    "DataLoaderVariable": {
      "type": "object",
      "description": "A variable exposed by a data loader, mapped from a source-file variable.",
      "required": ["file_variable", "units"],
      "additionalProperties": false,
      "properties": {
        "file_variable": {
          "type": "string",
          "description": "Name of the variable inside the source file. May differ from the schema-level variable name."
        },
        "units": {
          "type": "string",
          "description": "Units of the variable as exposed to the schema."
        },
        "unit_conversion": {
          "oneOf": [
            { "type": "number" },
            { "$ref": "#/$defs/Expression" }
          ],
          "description": "Optional multiplicative factor or Expression AST applied to convert source-file values to the declared units."
        },
        "description": { "type": "string" },
        "reference": { "$ref": "#/$defs/Reference" }
      }
    },

    "DataLoaderRegridding": {
      "type": "object",
      "description": "Structural regridding configuration. Algorithm-specific tuning parameters are runtime-side and not in the schema.",
      "additionalProperties": false,
      "properties": {
        "fill_value": {
          "type": "number",
          "description": "Value to assign to cells with no source data."
        },
        "extrapolation": {
          "type": "string",
          "enum": ["clamp", "nan", "periodic"],
          "description": "Behavior when regridding targets fall outside the source extent. Defaults to \"clamp\"."
        }
      }
    },

    "DataLoader": {
      "type": "object",
      "description": "A generic, runtime-agnostic description of an external data source. Carries enough structural information to locate files, map timestamps to files, describe spatial/variable semantics, and regrid — rather than pointing at a runtime handler. Authentication and algorithm-specific tuning are runtime-only and not part of the schema.",
      "required": ["kind", "source", "variables"],
      "additionalProperties": false,
      "properties": {
        "kind": {
          "type": "string",
          "enum": ["grid", "points", "static"],
          "description": "Structural kind of the dataset. Scientific role (emissions, meteorology, elevation, ...) is not schema-validated and belongs in metadata.tags."
        },
        "source": { "$ref": "#/$defs/DataLoaderSource" },
        "temporal": { "$ref": "#/$defs/DataLoaderTemporal" },
        "spatial": { "$ref": "#/$defs/DataLoaderSpatial" },
        "variables": {
          "type": "object",
          "description": "Variables exposed by this loader, keyed by schema-level variable name.",
          "minProperties": 1,
          "additionalProperties": { "$ref": "#/$defs/DataLoaderVariable" }
        },
        "regridding": { "$ref": "#/$defs/DataLoaderRegridding" },
        "reference": { "$ref": "#/$defs/Reference" },
        "metadata": {
          "type": "object",
          "description": "Free-form metadata about the data source. The \"tags\" field (array of strings) is conventional for expressing scientific role (e.g. \"emissions\", \"reanalysis\") and is not schema-validated.",
          "additionalProperties": true,
          "properties": {
            "tags": {
              "type": "array",
              "items": { "type": "string" }
            }
          }
        }
      }
    },

    "Operator": {
      "type": "object",
      "description": "A registered runtime operator (e.g., dry deposition, wet scavenging).",
      "required": ["operator_id", "needed_vars"],
      "additionalProperties": false,
      "properties": {
        "operator_id": {
          "type": "string",
          "description": "Registered identifier the runtime uses to find the implementation."
        },
        "reference": { "$ref": "#/$defs/Reference" },
        "config": {
          "type": "object",
          "description": "Implementation-specific configuration.",
          "additionalProperties": true
        },
        "needed_vars": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Variables required by the operator."
        },
        "modifies": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Variables the operator modifies."
        },
        "description": { "type": "string" }
      }
    },

    "RegisteredFunction": {
      "type": "object",
      "description": "A named pure function invoked inside expressions via the 'call' op (esm-spec §9.2).",
      "required": ["id", "signature"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string" },
        "signature": {
          "type": "object",
          "required": ["arg_count"],
          "additionalProperties": false,
          "properties": {
            "arg_count": { "type": "integer", "minimum": 0 },
            "arg_types": {
              "type": "array",
              "items": { "type": "string", "enum": ["scalar", "array", "index"] }
            },
            "return_type": { "type": "string", "enum": ["scalar", "array"] }
          }
        },
        "units": { "type": "string" },
        "arg_units": {
          "type": "array",
          "items": { "oneOf": [ { "type": "string" }, { "type": "null" } ] }
        },
        "description": { "type": "string" },
        "references": {
          "type": "array",
          "items": { "$ref": "#/$defs/Reference" }
        },
        "config": {
          "type": "object",
          "additionalProperties": true
        }
      }
    },

    "TranslateTarget": {
      "description": "Translation target: a simple variable reference string or an object with var and factor.",
      "oneOf": [
        { "type": "string" },
        {
          "type": "object",
          "required": ["var"],
          "additionalProperties": false,
          "properties": {
            "var": { "type": "string" },
            "factor": { "type": "number" }
          }
        }
      ]
    },

    "ConnectorEquation": {
      "type": "object",
      "description": "A single equation in a ConnectorSystem linking two coupled systems.",
      "required": ["from", "to", "transform"],
      "additionalProperties": false,
      "properties": {
        "from": {
          "type": "string",
          "description": "Source variable (scoped reference)."
        },
        "to": {
          "type": "string",
          "description": "Target variable (scoped reference)."
        },
        "transform": {
          "type": "string",
          "enum": ["additive", "multiplicative", "replacement"],
          "description": "How the expression modifies the target."
        },
        "expression": {
          "$ref": "#/$defs/Expression",
          "description": "The coupling expression."
        }
      }
    },

    "CouplingEntry": {
      "description": "A single coupling rule connecting models, reaction systems, data loaders, or operators.",
      "oneOf": [
        { "$ref": "#/$defs/CouplingOperatorCompose" },
        { "$ref": "#/$defs/CouplingCouple" },
        { "$ref": "#/$defs/CouplingVariableMap" },
        { "$ref": "#/$defs/CouplingOperatorApply" },
        { "$ref": "#/$defs/CouplingCallback" },
        { "$ref": "#/$defs/CouplingEvent" }
      ]
    },

    "CouplingOperatorCompose": {
      "type": "object",
      "description": "Match LHS time derivatives and add RHS terms together.",
      "required": ["type", "systems"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "operator_compose" },
        "systems": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 2,
          "maxItems": 2,
          "description": "The two systems to compose."
        },
        "translate": {
          "type": "object",
          "description": "Variable mappings when LHS variables don't have matching names.",
          "additionalProperties": { "$ref": "#/$defs/TranslateTarget" }
        },
        "description": { "type": "string" }
      }
    },

    "CouplingCouple": {
      "type": "object",
      "description": "Bi-directional coupling via connector equations.",
      "required": ["type", "systems", "connector"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "couple" },
        "systems": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 2,
          "maxItems": 2
        },
        "connector": {
          "type": "object",
          "required": ["equations"],
          "additionalProperties": false,
          "properties": {
            "equations": {
              "type": "array",
              "items": { "$ref": "#/$defs/ConnectorEquation" },
              "minItems": 1
            }
          }
        },
        "description": { "type": "string" }
      }
    },

    "CouplingVariableMap": {
      "type": "object",
      "description": "Replace a parameter in one system with a variable from another.",
      "required": ["type", "from", "to", "transform"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "variable_map" },
        "from": {
          "type": "string",
          "description": "Source variable (scoped reference, e.g., \"GEOSFP.T\")."
        },
        "to": {
          "type": "string",
          "description": "Target parameter (scoped reference, e.g., \"SuperFast.T\")."
        },
        "transform": {
          "type": "string",
          "enum": ["param_to_var", "identity", "additive", "multiplicative", "conversion_factor"],
          "description": "How the mapping is applied."
        },
        "factor": {
          "type": "number",
          "description": "Conversion factor (for conversion_factor transform)."
        },
        "interface": {
          "type": "string",
          "description": "Name of the interface this mapping uses."
        },
        "lifting": {
          "type": "string",
          "description": "Lifting strategy (e.g., pointwise, interpolation)."
        },
        "description": { "type": "string" }
      }
    },

    "CouplingOperatorApply": {
      "type": "object",
      "description": "Register an Operator to run during simulation.",
      "required": ["type", "operator"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "operator_apply" },
        "operator": {
          "type": "string",
          "description": "Name of the operator (key in the operators section)."
        },
        "description": { "type": "string" }
      }
    },

    "CouplingCallback": {
      "type": "object",
      "description": "Register a callback for simulation events.",
      "required": ["type", "callback_id"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "callback" },
        "callback_id": {
          "type": "string",
          "description": "Registered identifier for the callback."
        },
        "config": {
          "type": "object",
          "additionalProperties": true
        },
        "description": { "type": "string" }
      }
    },

    "CouplingEvent": {
      "type": "object",
      "description": "Cross-system event involving variables from multiple coupled systems.",
      "required": ["type", "event_type"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "event" },
        "event_type": {
          "type": "string",
          "enum": ["continuous", "discrete"],
          "description": "Whether this is a continuous or discrete event."
        },
        "name": {
          "type": "string",
          "description": "Human-readable identifier."
        },
        "conditions": {
          "type": "array",
          "items": { "$ref": "#/$defs/Expression" },
          "description": "Condition expressions (zero-crossing for continuous, boolean for discrete)."
        },
        "trigger": {
          "$ref": "#/$defs/DiscreteEventTrigger",
          "description": "Trigger specification (for discrete events)."
        },
        "affects": {
          "type": "array",
          "items": { "$ref": "#/$defs/AffectEquation" },
          "description": "Affect equations. Required unless functional_affect is used."
        },
        "functional_affect": {
          "$ref": "#/$defs/FunctionalAffect",
          "description": "Registered functional affect handler (alternative to symbolic affects)."
        },
        "affect_neg": {
          "oneOf": [
            { "type": "null" },
            {
              "type": "array",
              "items": { "$ref": "#/$defs/AffectEquation" }
            }
          ]
        },
        "discrete_parameters": {
          "type": "array",
          "items": { "type": "string" }
        },
        "root_find": {
          "type": "string",
          "enum": ["left", "right", "all"]
        },
        "reinitialize": { "type": "boolean" },
        "description": { "type": "string" }
      },
      "oneOf": [
        { "required": ["affects"] },
        { "required": ["functional_affect"] }
      ],
      "allOf": [
        {
          "if": {
            "properties": { "event_type": { "const": "continuous" } }
          },
          "then": {
            "required": ["conditions"]
          }
        },
        {
          "if": {
            "properties": { "event_type": { "const": "discrete" } }
          },
          "then": {
            "required": ["trigger"]
          }
        }
      ]
    },

    "SpatialDimension": {
      "type": "object",
      "description": "Specification of a single spatial dimension.",
      "required": ["min", "max"],
      "additionalProperties": false,
      "properties": {
        "min": { "type": "number" },
        "max": { "type": "number" },
        "units": { "type": "string" },
        "grid_spacing": { "type": "number", "exclusiveMinimum": 0 }
      }
    },

    "CoordinateTransform": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string" },
        "description": { "type": "string" },
        "dimensions": {
          "type": "array",
          "items": { "type": "string" }
        }
      }
    },

    "InitialConditions": {
      "description": "Initial conditions for state variables.",
      "oneOf": [
        {
          "type": "object",
          "required": ["type", "value"],
          "additionalProperties": false,
          "properties": {
            "type": { "const": "constant" },
            "value": { "type": "number" }
          }
        },
        {
          "type": "object",
          "required": ["type", "values"],
          "additionalProperties": false,
          "properties": {
            "type": { "const": "per_variable" },
            "values": {
              "type": "object",
              "additionalProperties": { "type": "number" }
            }
          }
        },
        {
          "type": "object",
          "required": ["type", "path"],
          "additionalProperties": false,
          "properties": {
            "type": { "const": "from_file" },
            "path": { "type": "string" },
            "format": { "type": "string" }
          }
        }
      ]
    },

    "BoundaryCondition": {
      "type": "object",
      "description": "Boundary condition for one or more dimensions.",
      "required": ["type", "dimensions"],
      "additionalProperties": false,
      "properties": {
        "type": {
          "type": "string",
          "enum": ["constant", "zero_gradient", "periodic", "dirichlet", "neumann", "robin"],
          "description": "constant/dirichlet = fixed value; zero_gradient/neumann = ∂u/∂n = 0; periodic = wrap-around; robin = αu + β∂u/∂n = γ."
        },
        "dimensions": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 1
        },
        "value": {
          "type": "number",
          "description": "Boundary value (for constant type)."
        },
        "function": {
          "type": "string",
          "description": "Function specification for time/space-varying boundaries."
        },
        "robin_alpha": {
          "type": "number",
          "description": "Robin BC coefficient α for u term in αu + β∂u/∂n = γ."
        },
        "robin_beta": {
          "type": "number",
          "description": "Robin BC coefficient β for ∂u/∂n term in αu + β∂u/∂n = γ."
        },
        "robin_gamma": {
          "type": "number",
          "description": "Robin BC RHS value γ in αu + β∂u/∂n = γ."
        }
      }
    },

    "Interface": {
      "type": "object",
      "description": "A coupling interface between domains.",
      "additionalProperties": true,
      "properties": {
        "description": { "type": "string" },
        "domains": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Domain names this interface connects."
        },
        "dimension_mapping": {
          "type": "object",
          "description": "How dimensions map across the interface.",
          "additionalProperties": true
        },
        "regridding": {
          "type": "object",
          "description": "Regridding configuration.",
          "additionalProperties": true
        }
      }
    },

    "Domain": {
      "type": "object",
      "description": "Spatiotemporal domain specification (DomainInfo).",
      "additionalProperties": false,
      "properties": {
        "independent_variable": {
          "type": "string",
          "description": "Name of the independent (time) variable.",
          "default": "t"
        },
        "temporal": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "start": { "type": "string", "format": "date-time" },
            "end": { "type": "string", "format": "date-time" },
            "reference_time": { "type": "string", "format": "date-time" }
          }
        },
        "spatial": {
          "type": "object",
          "description": "Spatial dimensions, keyed by name (e.g., lon, lat, lev).",
          "additionalProperties": { "$ref": "#/$defs/SpatialDimension" }
        },
        "coordinate_transforms": {
          "type": "array",
          "items": { "$ref": "#/$defs/CoordinateTransform" }
        },
        "spatial_ref": {
          "type": "string",
          "description": "Coordinate reference system (e.g., \"WGS84\")."
        },
        "initial_conditions": { "$ref": "#/$defs/InitialConditions" },
        "boundary_conditions": {
          "type": "array",
          "items": { "$ref": "#/$defs/BoundaryCondition" }
        },
        "element_type": {
          "type": "string",
          "enum": ["Float32", "Float64"],
          "description": "Floating point precision.",
          "default": "Float64"
        },
        "array_type": {
          "type": "string",
          "description": "Array backend (e.g., \"Array\", \"CuArray\").",
          "default": "Array"
        }
      }
    },

    "Tolerance": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "abs": { "type": "number", "minimum": 0 },
        "rel": { "type": "number", "minimum": 0 }
      }
    },

    "Assertion": {
      "type": "object",
      "required": ["variable", "time", "expected"],
      "additionalProperties": false,
      "properties": {
        "variable": { "type": "string" },
        "time": { "type": "number" },
        "expected": { "type": "number" },
        "tolerance": { "$ref": "#/$defs/Tolerance" }
      }
    },

    "TimeSpan": {
      "type": "object",
      "required": ["start", "end"],
      "additionalProperties": false,
      "properties": {
        "start": { "type": "number" },
        "end": { "type": "number" }
      }
    },

    "Test": {
      "type": "object",
      "required": ["id", "time_span", "assertions"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string" },
        "description": { "type": "string" },
        "initial_conditions": {
          "type": "object",
          "additionalProperties": { "type": "number" }
        },
        "parameter_overrides": {
          "type": "object",
          "additionalProperties": { "type": "number" }
        },
        "time_span": { "$ref": "#/$defs/TimeSpan" },
        "tolerance": { "$ref": "#/$defs/Tolerance" },
        "assertions": {
          "type": "array",
          "items": { "$ref": "#/$defs/Assertion" },
          "minItems": 1
        }
      }
    },

    "SweepRange": {
      "type": "object",
      "required": ["start", "stop", "count"],
      "additionalProperties": false,
      "properties": {
        "start": { "type": "number" },
        "stop":  { "type": "number" },
        "count": { "type": "integer", "minimum": 2 },
        "scale": { "type": "string", "enum": ["linear", "log"], "default": "linear" }
      }
    },

    "SweepDimension": {
      "type": "object",
      "required": ["parameter"],
      "additionalProperties": false,
      "properties": {
        "parameter": { "type": "string" },
        "values": {
          "type": "array",
          "items": { "type": "number" },
          "minItems": 1
        },
        "range": { "$ref": "#/$defs/SweepRange" }
      },
      "oneOf": [
        { "required": ["values"] },
        { "required": ["range"] }
      ]
    },

    "ParameterSweep": {
      "type": "object",
      "required": ["type", "dimensions"],
      "additionalProperties": false,
      "properties": {
        "type": { "type": "string", "enum": ["cartesian"] },
        "dimensions": {
          "type": "array",
          "items": { "$ref": "#/$defs/SweepDimension" },
          "minItems": 1
        }
      }
    },

    "PlotAxis": {
      "type": "object",
      "required": ["variable"],
      "additionalProperties": false,
      "properties": {
        "variable": { "type": "string" },
        "label": { "type": "string" }
      }
    },

    "PlotValue": {
      "type": "object",
      "required": ["variable"],
      "additionalProperties": false,
      "properties": {
        "variable": { "type": "string" },
        "at_time": { "type": "number" },
        "reduce": { "type": "string", "enum": ["max", "min", "mean", "integral", "final"] }
      }
    },

    "PlotSeries": {
      "type": "object",
      "required": ["name", "variable"],
      "additionalProperties": false,
      "properties": {
        "name": { "type": "string" },
        "variable": { "type": "string" }
      }
    },

    "Plot": {
      "type": "object",
      "required": ["id", "type", "x", "y"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string" },
        "type": { "type": "string", "enum": ["line", "scatter", "heatmap"] },
        "description": { "type": "string" },
        "x": { "$ref": "#/$defs/PlotAxis" },
        "y": { "$ref": "#/$defs/PlotAxis" },
        "value": { "$ref": "#/$defs/PlotValue" },
        "series": {
          "type": "array",
          "items": { "$ref": "#/$defs/PlotSeries" }
        }
      },
      "if": {
        "properties": { "type": { "const": "heatmap" } }
      },
      "then": {
        "required": ["value"]
      }
    },

    "Example": {
      "type": "object",
      "required": ["id", "time_span"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string" },
        "description": { "type": "string" },
        "initial_state": { "$ref": "#/$defs/InitialConditions" },
        "parameters": {
          "type": "object",
          "additionalProperties": { "type": "number" }
        },
        "time_span": { "$ref": "#/$defs/TimeSpan" },
        "parameter_sweep": { "$ref": "#/$defs/ParameterSweep" },
        "plots": {
          "type": "array",
          "items": { "$ref": "#/$defs/Plot" }
        }
      }
    },

    "GridMetricGenerator": {
      "type": "object",
      "description": "Generator for a grid metric array (RFC §6.5). Exactly one kind: 'expression', 'loader', or 'builtin'.",
      "required": ["kind"],
      "additionalProperties": false,
      "properties": {
        "kind": {
          "type": "string",
          "enum": ["expression", "loader", "builtin"]
        },
        "expr": {
          "oneOf": [
            { "type": "number" },
            { "type": "string" },
            { "$ref": "#/$defs/ExpressionNode" }
          ]
        },
        "loader": { "type": "string" },
        "field": { "type": "string" },
        "name": { "type": "string" }
      },
      "allOf": [
        { "if": { "properties": { "kind": { "const": "expression" } }, "required": ["kind"] },
          "then": { "required": ["expr"] } },
        { "if": { "properties": { "kind": { "const": "loader" } }, "required": ["kind"] },
          "then": { "required": ["loader", "field"] } },
        { "if": { "properties": { "kind": { "const": "builtin" } }, "required": ["kind"] },
          "then": { "required": ["name"] } }
      ]
    },

    "GridMetricArray": {
      "type": "object",
      "description": "A named metric array declared on a grid (e.g., dx, dcEdge, areaCell). See RFC §6.5.",
      "required": ["rank", "generator"],
      "additionalProperties": false,
      "properties": {
        "rank": { "type": "integer", "minimum": 0 },
        "dim": { "type": "string" },
        "dims": {
          "type": "array",
          "items": { "type": "string" }
        },
        "shape": { "type": "array" },
        "generator": { "$ref": "#/$defs/GridMetricGenerator" }
      }
    },

    "GridConnectivity": {
      "type": "object",
      "description": "Unstructured-grid connectivity table (e.g., cellsOnEdge) or cubed-sphere panel_connectivity. See RFC §6.3 and §6.4.",
      "required": ["shape", "rank"],
      "additionalProperties": false,
      "properties": {
        "shape": { "type": "array" },
        "rank": { "type": "integer", "minimum": 1 },
        "loader": { "type": "string" },
        "field": { "type": "string" },
        "generator": { "$ref": "#/$defs/GridMetricGenerator" }
      }
    },

    "GridExtent": {
      "type": "object",
      "description": "Per-dimension extent for cartesian or cubed_sphere grids (RFC §6.2, §6.4).",
      "required": ["n"],
      "additionalProperties": false,
      "properties": {
        "n": {
          "oneOf": [
            { "type": "integer", "minimum": 1 },
            { "type": "string" }
          ]
        },
        "spacing": {
          "type": "string",
          "enum": ["uniform", "nonuniform"]
        }
      }
    },

    "Grid": {
      "type": "object",
      "description": "A named discretization grid (v0.2.0, RFC §6). Selects one of three topologies via `family`: cartesian / unstructured / cubed_sphere.",
      "required": ["family", "dimensions"],
      "additionalProperties": false,
      "properties": {
        "family": {
          "type": "string",
          "enum": ["cartesian", "unstructured", "cubed_sphere"]
        },
        "description": { "type": "string" },
        "dimensions": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 1
        },
        "locations": {
          "type": "array",
          "items": { "type": "string" }
        },
        "metric_arrays": {
          "type": "object",
          "additionalProperties": { "$ref": "#/$defs/GridMetricArray" }
        },
        "parameters": {
          "type": "object",
          "additionalProperties": { "$ref": "#/$defs/Parameter" }
        },
        "domain": { "type": "string" },
        "extents": {
          "type": "object",
          "additionalProperties": { "$ref": "#/$defs/GridExtent" }
        },
        "connectivity": {
          "type": "object",
          "additionalProperties": { "$ref": "#/$defs/GridConnectivity" }
        },
        "panel_connectivity": {
          "type": "object",
          "additionalProperties": { "$ref": "#/$defs/GridConnectivity" }
        }
      },
      "allOf": [
        { "if": { "properties": { "family": { "const": "cartesian" } }, "required": ["family"] },
          "then": { "required": ["extents"] } },
        { "if": { "properties": { "family": { "const": "unstructured" } }, "required": ["family"] },
          "then": { "required": ["connectivity"] } },
        { "if": { "properties": { "family": { "const": "cubed_sphere" } }, "required": ["family"] },
          "then": { "required": ["extents", "panel_connectivity"] } }
      ]
    }
  }
}

// Compile schema validator once at module load time
let validator: ValidateFunction

try {
  const ajv = new Ajv({
    allErrors: true,
    verbose: true,
    strict: false, // Allow unknown keywords for compatibility
    addUsedSchema: false, // Don't add the schema to cache
    validateSchema: false // Skip schema validation for now
  })
  addFormats(ajv)

  validator = ajv.compile(schema)
} catch (error) {
  throw new Error(`Failed to compile embedded ESM schema: ${error}`)
}

/**
 * Validate data against the ESM schema
 */
export function validateSchema(data: unknown): SchemaError[] {
  const isValid = validator(data)
  if (isValid || !validator.errors) {
    return []
  }

  return validator.errors.map((error: ErrorObject): SchemaError => ({
    path: error.instancePath || '/',
    message: error.message || 'Unknown validation error',
    keyword: error.keyword
  }))
}

/**
 * Parse JSON string safely
 */
function parseJson(input: string): unknown {
  try {
    return JSON.parse(input)
  } catch (error) {
    throw new ParseError(
      `Invalid JSON: ${error instanceof Error ? error.message : 'Unknown error'}`,
      error instanceof Error ? error : undefined
    )
  }
}

/**
 * Parse JSON string preserving integer-vs-float distinction via
 * `losslessJsonParse`. Numeric literals in the result are tagged
 * `NumericLiteral` leaves per RFC §5.4.1.
 */
function parseJsonLossless(input: string): unknown {
  try {
    return losslessJsonParse(input)
  } catch (error) {
    throw new ParseError(
      `Invalid JSON: ${error instanceof Error ? error.message : 'Unknown error'}`,
      error instanceof Error ? error : undefined,
    )
  }
}

/**
 * Recursively replace `NumericLiteral` leaves with their plain-number
 * value. Used to produce a plain view of a lossless-parsed document
 * for Ajv schema validation (the schema declares `type: number`, which
 * does not match tagged objects).
 *
 * Returns a new tree; input is not mutated. Non-literal objects and
 * arrays are shallow-copied only when a descendant is rewritten.
 */
function stripNumericLiterals(value: unknown): unknown {
  if (isNumericLiteral(value)) return value.value
  if (Array.isArray(value)) {
    let changed = false
    const out: unknown[] = new Array(value.length)
    for (let i = 0; i < value.length; i++) {
      const v = stripNumericLiterals(value[i])
      if (v !== value[i]) changed = true
      out[i] = v
    }
    return changed ? out : value
  }
  if (value && typeof value === 'object') {
    const src = value as Record<string, unknown>
    let changed = false
    const out: Record<string, unknown> = {}
    for (const key of Object.keys(src)) {
      const v = stripNumericLiterals(src[key])
      if (v !== src[key]) changed = true
      out[key] = v
    }
    return changed ? out : value
  }
  return value
}

/**
 * Coerce types for better TypeScript compatibility
 * Handles Expression union types and discriminated unions
 */
function coerceTypes(data: any): any {
  if (data === null || data === undefined) {
    return data
  }

  // Canonical-mode tagged leaves are opaque — never descend into them.
  if (isNumericLiteral(data)) {
    return data
  }

  if (Array.isArray(data)) {
    return data.map(coerceTypes)
  }

  if (typeof data === 'object') {
    const result: any = {}

    for (const [key, value] of Object.entries(data)) {
      // Handle Expression types - they can be number, string, or ExpressionNode
      // ExpressionNode has 'op' and 'args' properties
      if (key === 'expression' || key === 'args' || /expr/i.test(key)) {
        result[key] = coerceExpression(value)
      } else {
        result[key] = coerceTypes(value)
      }
    }

    return result
  }

  return data
}

/**
 * Coerce Expression union type (number | string | ExpressionNode).
 * `NumericLiteral` tagged leaves (canonical-mode only) pass through
 * unchanged.
 */
function coerceExpression(value: any): Expression {
  if (typeof value === 'number' || typeof value === 'string') {
    return value
  }

  // NumericLiteral — canonical-mode tagged leaf; pass through.
  if (isNumericLiteral(value)) {
    return value as unknown as Expression
  }

  // If it's an object with 'op' and 'args', treat as ExpressionNode
  if (value && typeof value === 'object' && 'op' in value && 'args' in value) {
    return {
      ...value,
      args: Array.isArray(value.args) ? value.args.map(coerceExpression) : value.args
    }
  }

  return value
}

/**
 * Parse a semantic version string and return its components
 */
function parseSemanticVersion(versionString: string): { major: number; minor: number; patch: number } | null {
  const match = versionString.match(/^(\d+)\.(\d+)\.(\d+)$/)
  if (!match) {
    return null
  }

  return {
    major: parseInt(match[1], 10),
    minor: parseInt(match[2], 10),
    patch: parseInt(match[3], 10)
  }
}

/**
 * Check version compatibility for an ESM file
 */
function checkVersionCompatibility(data: any): void {
  if (typeof data !== 'object' || data === null) {
    return // Let schema validation handle this
  }

  const version = data.esm
  if (typeof version !== 'string') {
    return // Let schema validation handle this
  }

  const versionComponents = parseSemanticVersion(version)
  if (versionComponents === null) {
    return // Let schema validation handle invalid version format
  }

  const { major } = versionComponents
  const CURRENT_MAJOR = 0 // Current supported major version

  // Reject unsupported major versions
  if (major !== CURRENT_MAJOR) {
    throw new ParseError(`Unsupported major version ${major}. This parser supports major version ${CURRENT_MAJOR}.`)
  }
}

/**
 * Version-aware schema validation that handles backward/forward compatibility
 */
function validateSchemaWithVersionCompatibility(data: any): SchemaError[] {
  if (typeof data !== 'object' || data === null) {
    return validateSchema(data)
  }

  const version = data.esm
  if (typeof version !== 'string') {
    return validateSchema(data)
  }

  const versionComponents = parseSemanticVersion(version)
  if (versionComponents === null) {
    // If version parsing fails, use normal validation
    return validateSchema(data)
  }

  const { major, minor, patch } = versionComponents
  const CURRENT_VERSION = { major: 0, minor: 1, patch: 0 }

  // If it's the exact current version, use normal validation
  if (major === CURRENT_VERSION.major && minor === CURRENT_VERSION.minor && patch === CURRENT_VERSION.patch) {
    return validateSchema(data)
  }

  // Same major version: attempt backward/forward compatibility
  if (major === CURRENT_VERSION.major) {
    // Forward compatibility: newer minor version
    if (minor > CURRENT_VERSION.minor) {
      console.warn(`Forward compatibility: Version ${version} is newer than current ${CURRENT_VERSION.major}.${CURRENT_VERSION.minor}.${CURRENT_VERSION.patch}. Some features may not be fully supported.`)

      // Validate with current version substituted to check structural validity
      const tempData = { ...data, esm: '0.1.0' }
      const errors = validateSchema(tempData)

      // Filter out additionalProperties errors (unknown fields from newer versions)
      return errors.filter(error => {
        if (error.keyword === 'additionalProperties') {
          console.warn(`Forward compatibility: Ignoring unknown field at ${error.path}`)
          return false
        }
        return true
      })
    }

    // Backward compatibility or different patch: validate with current version substituted
    const tempData = { ...data, esm: '0.1.0' }
    return validateSchema(tempData)
  }

  // This shouldn't happen due to checkVersionCompatibility, but fallback to normal validation
  return validateSchema(data)
}

/**
 * Remove unknown fields for forward compatibility
 */
function removeUnknownFields(data: any): any {
  if (typeof data !== 'object' || data === null) {
    return data
  }

  const version = data.esm
  if (typeof version !== 'string') {
    return data
  }

  const versionComponents = parseSemanticVersion(version)
  if (versionComponents === null) {
    return data
  }

  const { major, minor } = versionComponents
  const CURRENT_VERSION = { major: 0, minor: 1, patch: 0 }

  // Only clean up for forward compatible versions (newer minor versions in the same major)
  if (major === CURRENT_VERSION.major && minor > CURRENT_VERSION.minor) {
    // Create a copy of the data and remove fields that would cause schema validation errors
    const cleanedData = { ...data }

    // Remove known forward compatibility fields that aren't in the current schema
    const unknownRootFields = ['performance_hints', 'validation_metadata', 'extended_metadata']
    unknownRootFields.forEach(field => {
      if (field in cleanedData) {
        delete cleanedData[field]
      }
    })

    // Recursively clean model and reaction system objects
    if (cleanedData.models) {
      cleanedData.models = cleanModels(cleanedData.models)
    }
    if (cleanedData.reaction_systems) {
      cleanedData.reaction_systems = cleanReactionSystems(cleanedData.reaction_systems)
    }

    return cleanedData
  }

  return data
}

/**
 * Clean unknown fields from models
 */
function cleanModels(models: any): any {
  if (typeof models !== 'object' || models === null) {
    return models
  }

  const cleaned: any = {}
  for (const [key, model] of Object.entries(models)) {
    if (typeof model === 'object' && model !== null) {
      const cleanedModel: any = { ...model }
      // Remove known forward compatibility fields
      const unknownModelFields = ['solver_hints', 'optimization_flags']
      unknownModelFields.forEach(field => {
        if (field in cleanedModel) {
          delete cleanedModel[field]
        }
      })
      cleaned[key] = cleanedModel
    } else {
      cleaned[key] = model
    }
  }
  return cleaned
}

/**
 * Clean unknown fields from reaction systems
 */
function cleanReactionSystems(reactionSystems: any): any {
  if (typeof reactionSystems !== 'object' || reactionSystems === null) {
    return reactionSystems
  }

  const cleaned: any = {}
  for (const [key, system] of Object.entries(reactionSystems)) {
    if (typeof system === 'object' && system !== null) {
      const cleanedSystem: any = { ...system }

      // Clean reactions array
      if (Array.isArray(cleanedSystem.reactions)) {
        cleanedSystem.reactions = cleanedSystem.reactions.map((reaction: any) => {
          if (typeof reaction === 'object' && reaction !== null) {
            const cleanedReaction: any = { ...reaction }
            // Remove known forward compatibility fields from reactions
            const unknownReactionFields = ['kinetics_metadata', 'thermodynamic_data']
            unknownReactionFields.forEach(field => {
              if (field in cleanedReaction) {
                delete cleanedReaction[field]
              }
            })
            return cleanedReaction
          }
          return reaction
        })
      }

      cleaned[key] = cleanedSystem
    } else {
      cleaned[key] = system
    }
  }
  return cleaned
}

/**
 * Post-schema validation for grid metric/connectivity generators (RFC §6.5).
 *
 * For every `GridMetricGenerator` found under `grids.<name>.metric_arrays`,
 * `grids.<name>.connectivity`, or `grids.<name>.panel_connectivity`:
 *   - kind='loader' requires the loader name to exist in top-level
 *     `data_loaders`. Otherwise throws `E_UNKNOWN_LOADER`.
 *   - kind='builtin' requires the `name` to be in the closed
 *     `KNOWN_GRID_BUILTINS` set. Otherwise throws `E_UNKNOWN_BUILTIN`.
 */
function validateGridGenerators(data: any): void {
  if (!data || typeof data !== 'object') return
  const grids = data.grids
  if (!grids || typeof grids !== 'object') return

  const dataLoaders = (data.data_loaders && typeof data.data_loaders === 'object')
    ? data.data_loaders
    : {}

  const checkGenerator = (gen: any, where: string): void => {
    if (!gen || typeof gen !== 'object') return
    if (gen.kind === 'loader') {
      const name = gen.loader
      if (typeof name !== 'string' || !(name in dataLoaders)) {
        throw new GridValidationError(
          `[E_UNKNOWN_LOADER] ${where}: generator references data_loaders.${name} which is not defined.`,
          'E_UNKNOWN_LOADER'
        )
      }
    } else if (gen.kind === 'builtin') {
      const name = gen.name
      if (typeof name !== 'string' || !KNOWN_GRID_BUILTINS.has(name)) {
        throw new GridValidationError(
          `[E_UNKNOWN_BUILTIN] ${where}: '${name}' is not a recognized grid builtin. ` +
            `Known builtins: ${Array.from(KNOWN_GRID_BUILTINS).join(', ')}.`,
          'E_UNKNOWN_BUILTIN'
        )
      }
    }
  }

  for (const [gridName, grid] of Object.entries(grids)) {
    if (!grid || typeof grid !== 'object') continue
    const g = grid as Record<string, any>

    if (g.metric_arrays && typeof g.metric_arrays === 'object') {
      for (const [arrName, arr] of Object.entries(g.metric_arrays)) {
        if (arr && typeof arr === 'object' && 'generator' in (arr as object)) {
          checkGenerator(
            (arr as any).generator,
            `grids.${gridName}.metric_arrays.${arrName}.generator`
          )
        }
      }
    }

    for (const bucket of ['connectivity', 'panel_connectivity'] as const) {
      if (g[bucket] && typeof g[bucket] === 'object') {
        for (const [tblName, tbl] of Object.entries(g[bucket])) {
          if (!tbl || typeof tbl !== 'object') continue
          const t = tbl as Record<string, any>
          // Connectivity tables may have either a generator (cubed-sphere
          // builtin) or a loader/field pair (unstructured).
          if ('generator' in t) {
            checkGenerator(t.generator, `grids.${gridName}.${bucket}.${tblName}.generator`)
          } else if ('loader' in t) {
            const name = t.loader
            if (typeof name !== 'string' || !(name in dataLoaders)) {
              throw new GridValidationError(
                `[E_UNKNOWN_LOADER] grids.${gridName}.${bucket}.${tblName}: ` +
                  `loader '${name}' is not defined in top-level data_loaders.`,
                'E_UNKNOWN_LOADER'
              )
            }
          }
        }
      }
    }
  }
}

/**
 * Options controlling how `load()` parses and represents an ESM file.
 */
export interface LoadOptions {
  /**
   * When `true`, numeric literals at Expression-bearing positions are
   * decoded to tagged `NumericLiteral` leaves (see
   * {@link losslessJsonParse}) so downstream consumers can preserve the
   * integer-vs-float distinction required by the canonical form
   * (discretization RFC §5.4.1 / §5.4.6). When `false` or absent
   * (default), numeric literals decode to plain JS numbers for
   * backwards compatibility.
   *
   * Canonical mode only takes effect for string inputs; pre-parsed
   * objects are returned as-is (callers that want tagged leaves should
   * run `losslessJsonParse` themselves before passing the object in).
   */
  canonical?: boolean
}

/**
 * Load an ESM file from a JSON string or pre-parsed object
 *
 * @param input - JSON string or pre-parsed JavaScript object
 * @param options - Optional load-time settings (see {@link LoadOptions})
 * @returns Typed EsmFile object
 * @throws {ParseError} When JSON parsing fails or version is incompatible
 * @throws {SchemaValidationError} When schema validation fails
 */
export function load(input: string | object, options?: LoadOptions): EsmFile {
  const canonical = options?.canonical === true

  // Step 1: JSON parsing. In canonical mode, decode tagged numeric
  // literals and keep a separate plain view for Ajv schema validation
  // (the schema declares `type: number`, which does not match tagged
  // `NumericLiteral` objects).
  let data: unknown
  let validationView: unknown
  if (typeof input === 'string') {
    if (canonical) {
      data = parseJsonLossless(input)
      validationView = stripNumericLiterals(data)
    } else {
      data = parseJson(input)
      validationView = data
    }
  } else {
    data = input
    validationView = canonical ? stripNumericLiterals(input) : input
  }

  // Step 2: Version compatibility check (before schema validation)
  checkVersionCompatibility(validationView)

  // Step 3: Schema validation with version compatibility
  const schemaErrors = validateSchemaWithVersionCompatibility(validationView)
  if (schemaErrors.length > 0) {
    throw new SchemaValidationError(
      `Schema validation failed with ${schemaErrors.length} error(s)`,
      schemaErrors
    )
  }

  // Step 4: Clean up unknown fields for forward compatibility and type coercion
  const cleanedData = removeUnknownFields(data)
  const typedData = coerceTypes(cleanedData) as EsmFile

  // Step 4a: Emit E_DEPRECATED_DOMAIN_BC for any v0.1.0-style domain-level
  // boundary_conditions (v0.2.0 transitional shim per RFC §10.1 +
  // gt-2fvs mayor decision). A follow-up bead flips this to a hard error.
  if (typedData && typeof typedData === 'object' && 'domains' in typedData) {
    const domains = (typedData as Record<string, unknown>).domains
    if (domains && typeof domains === 'object') {
      for (const [domainName, domain] of Object.entries(domains)) {
        if (
          domain &&
          typeof domain === 'object' &&
          'boundary_conditions' in (domain as Record<string, unknown>)
        ) {
          // eslint-disable-next-line no-console
          console.warn(
            `[E_DEPRECATED_DOMAIN_BC] domains.${domainName}.boundary_conditions ` +
              `is deprecated in ESM v0.2.0; migrate to ` +
              `models.<M>.boundary_conditions (docs/rfcs/discretization.md §9).`
          )
        }
      }
    }
  }

  // Step 4b: Grid generator validation (RFC §6).
  //   - For kind='loader': the referenced loader name must exist in top-level data_loaders.
  //   - For kind='builtin': name must be one of the closed set of canonical builtins
  //     (currently gnomonic_c6_neighbors, gnomonic_c6_d4_action); unknown names
  //     are rejected with E_UNKNOWN_BUILTIN per §6.4.1.
  validateGridGenerators(typedData)

  // Step 5: Dimensional analysis — emit warnings but never fail the load.
  // Mirrors the Julia @warn behavior so TS callers get the same signal
  // without an API break.
  for (const warning of validateUnits(typedData)) {
    const location = warning.location ? ` [${warning.location}]` : ''
    console.warn(`ESM unit validation${location}: ${warning.message}`)
  }

  return typedData
}