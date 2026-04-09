/**
 * ESM Format JSON Parsing
 *
 * Provides functionality to load and validate ESM files from JSON strings or objects.
 * Separates concerns: JSON parsing → schema validation → type coercion.
 */

import Ajv, { ErrorObject, ValidateFunction } from 'ajv'
import addFormats from 'ajv-formats'
import type { EsmFile, Expression, CouplingEntry } from './types.js'

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
      "description": "Format version string (semver).",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
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
    "coupling": {
      "type": "array",
      "description": "Composition and coupling rules.",
      "items": { "$ref": "#/$defs/CouplingEntry" }
    },
    "domain": { "$ref": "#/$defs/Domain" },
    "solver": { "$ref": "#/$defs/Solver" }
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
          "format": "date-time",
          "description": "ISO 8601 creation timestamp."
        },
        "modified": {
          "type": "string",
          "format": "date-time",
          "description": "ISO 8601 last-modified timestamp."
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
        "doi": { "type": "string" },
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
            "sign"
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
        }
      },
      "additionalProperties": false
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
      "description": "A variable in an ODE model.",
      "required": ["type"],
      "additionalProperties": false,
      "properties": {
        "type": {
          "type": "string",
          "enum": ["state", "parameter", "observed"],
          "description": "state = time-dependent unknown; parameter = externally set constant; observed = derived quantity."
        },
        "units": { "type": "string" },
        "default": { "type": "number" },
        "description": { "type": "string" },
        "expression": {
          "$ref": "#/$defs/Expression",
          "description": "Defining expression for observed variables."
        }
      },
      "if": {
        "properties": { "type": { "const": "observed" } }
      },
      "then": {
        "required": ["expression"]
      }
    },

    "Model": {
      "type": "object",
      "description": "An ODE system — a fully specified set of time-dependent equations.",
      "required": ["variables", "equations"],
      "additionalProperties": false,
      "properties": {
        "coupletype": {
          "description": "Coupling type name for couple2 dispatch.",
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
        }
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
          "description": "Coupling type name for couple2 dispatch.",
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
        }
      }
    },

    "DataLoaderProvides": {
      "type": "object",
      "description": "A variable provided by a data loader.",
      "additionalProperties": false,
      "properties": {
        "units": { "type": "string" },
        "description": { "type": "string" }
      }
    },

    "DataLoader": {
      "type": "object",
      "description": "An external data source registration. Runtime-specific; registered by type and loader_id.",
      "required": ["type", "loader_id", "provides"],
      "additionalProperties": false,
      "properties": {
        "type": {
          "type": "string",
          "enum": ["gridded_data", "emissions", "timeseries", "static", "callback"],
          "description": "Data loader category."
        },
        "loader_id": {
          "type": "string",
          "description": "Registered identifier the runtime uses to find the implementation."
        },
        "config": {
          "type": "object",
          "description": "Implementation-specific configuration.",
          "additionalProperties": true
        },
        "reference": { "$ref": "#/$defs/Reference" },
        "provides": {
          "type": "object",
          "description": "Variables this loader makes available.",
          "additionalProperties": { "$ref": "#/$defs/DataLoaderProvides" }
        },
        "temporal_resolution": {
          "type": "string",
          "description": "ISO 8601 duration (e.g., \"PT3H\")."
        },
        "spatial_resolution": {
          "type": "object",
          "description": "Grid spacing per dimension.",
          "additionalProperties": { "type": "number" }
        },
        "interpolation": {
          "type": "string",
          "enum": ["linear", "nearest", "cubic"],
          "description": "Interpolation method."
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
        { "$ref": "#/$defs/CouplingCouple2" },
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

    "CouplingCouple2": {
      "type": "object",
      "description": "Bi-directional coupling via coupletype dispatch.",
      "required": ["type", "systems", "coupletype_pair", "connector"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "couple2" },
        "systems": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 2,
          "maxItems": 2
        },
        "coupletype_pair": {
          "type": "array",
          "items": { "type": "string" },
          "minItems": 2,
          "maxItems": 2,
          "description": "The coupletype names for each system."
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

    "Solver": {
      "type": "object",
      "description": "Solver strategy for time integration.",
      "required": ["strategy"],
      "additionalProperties": false,
      "properties": {
        "strategy": {
          "type": "string",
          "enum": ["strang_threads", "strang_serial", "imex"],
          "description": "Solver strategy."
        },
        "config": {
          "type": "object",
          "description": "Strategy-specific configuration.",
          "additionalProperties": true,
          "properties": {
            "threads": { "type": "integer", "minimum": 1 },
            "stiff_algorithm": { "type": "string" },
            "nonstiff_algorithm": { "type": "string" },
            "timestep": { "type": "number", "exclusiveMinimum": 0 },
            "stiff_kwargs": {
              "type": "object",
              "additionalProperties": true,
              "properties": {
                "abstol": { "type": "number" },
                "reltol": { "type": "number" }
              }
            },
            "map_algorithm": { "type": "string" }
          }
        }
      }
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
 * Coerce types for better TypeScript compatibility
 * Handles Expression union types and discriminated unions
 */
function coerceTypes(data: any): any {
  if (data === null || data === undefined) {
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
 * Coerce Expression union type (number | string | ExpressionNode)
 */
function coerceExpression(value: any): Expression {
  if (typeof value === 'number' || typeof value === 'string') {
    return value
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

  // For backward/forward compatibility within the same major version,
  // first check if there are actual compatibility issues that need to be ignored
  if (major === CURRENT_VERSION.major) {
    // Try validation with original version first to see if version is the only issue
    const originalErrors = validateSchema(data)

    // If there are no additional properties errors, then version mismatch should fail
    const hasAdditionalPropsErrors = originalErrors.some(error =>
      error.keyword === 'additionalProperties'
    )

    // If only version error and no additional properties, enforce strict version matching
    if (!hasAdditionalPropsErrors && (minor !== CURRENT_VERSION.minor || patch !== CURRENT_VERSION.patch)) {
      return originalErrors
    }

    // Generate forward compatibility warnings for actual compatibility cases
    if (minor > CURRENT_VERSION.minor) {
      console.warn(`Forward compatibility: Version ${version} is newer than current ${CURRENT_VERSION.major}.${CURRENT_VERSION.minor}.${CURRENT_VERSION.patch}. Some features may not be fully supported.`)
    }

    const tempData = { ...data, esm: '0.1.0' }
    const errors = validateSchema(tempData)

    // Filter out additionalProperties errors for forward compatibility
    const filteredErrors = errors.filter(error => {
      // Allow additional properties for newer versions (forward compatibility)
      if (error.keyword === 'additionalProperties' &&
          (minor > CURRENT_VERSION.minor || patch > CURRENT_VERSION.patch)) {
        console.warn(`Forward compatibility: Ignoring unknown field at ${error.path}`)
        return false
      }
      return true
    })

    return filteredErrors
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
 * Load an ESM file from a JSON string or pre-parsed object
 *
 * @param input - JSON string or pre-parsed JavaScript object
 * @returns Typed EsmFile object
 * @throws {ParseError} When JSON parsing fails or version is incompatible
 * @throws {SchemaValidationError} When schema validation fails
 */
export function load(input: string | object): EsmFile {
  // Step 1: JSON parsing
  let data: unknown
  if (typeof input === 'string') {
    data = parseJson(input)
  } else {
    data = input
  }

  // Step 2: Version compatibility check (before schema validation)
  checkVersionCompatibility(data)

  // Step 3: Schema validation with version compatibility
  const schemaErrors = validateSchemaWithVersionCompatibility(data)
  if (schemaErrors.length > 0) {
    throw new SchemaValidationError(
      `Schema validation failed with ${schemaErrors.length} error(s)`,
      schemaErrors
    )
  }

  // Step 4: Clean up unknown fields for forward compatibility and type coercion
  const cleanedData = removeUnknownFields(data)
  const typedData = coerceTypes(cleanedData) as EsmFile

  return typedData
}