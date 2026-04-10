/**
 * Quick test to verify the codegen works with real schema data
 */

import { toJuliaCode } from './dist/codegen.js'

// Test with correct schema data (no name properties, uses units not unit, uses substrates not reactants)
const correctSchemaFile = {
  "esm": "0.1.0",
  "metadata": {
    "name": "TestModel"
  },
  "models": {
    "atmospheric": {
      "variables": {
        "O3": {
          "type": "state",
          "default": 50.0,
          "units": "ppb"
        },
        "k1": {
          "type": "parameter",
          "default": 1e-3
        }
      },
      "equations": [
        {
          "lhs": {
            "op": "D",
            "args": ["O3"],
            "wrt": "t"
          },
          "rhs": {
            "op": "*",
            "args": ["k1", "O3"]
          }
        }
      ]
    }
  },
  "reaction_systems": {
    "chemistry": {
      "species": {
        "NO": {
          "default": 10.0,
          "units": "ppb"
        },
        "NO2": {
          "default": 5.0,
          "units": "ppb"
        }
      },
      "parameters": {
        "k1": {
          "default": 0.01,
          "units": "1/s"
        }
      },
      "reactions": [
        {
          "id": "R1",
          "substrates": [
            { "species": "NO", "stoichiometry": 1 }
          ],
          "products": [
            { "species": "NO2", "stoichiometry": 1 }
          ],
          "rate": "k1"
        }
      ]
    }
  }
}

console.log("Testing with correct schema...")
try {
  const code = toJuliaCode(correctSchemaFile)
  console.log("SUCCESS: Code generated without errors!")
  console.log("\nGenerated Julia code:")
  console.log(code)
} catch (error) {
  console.error("ERROR:", error.message)
}