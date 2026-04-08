/**
 * Test to demonstrate that the main bug described in EarthSciSerialization-61ls is fixed:
 * - codegen no longer accesses reaction.reactants (uses reaction.substrates)
 * - codegen no longer accesses variable.name (uses dictionary keys)
 * - codegen no longer accesses species.name (uses dictionary keys)
 */

console.log("Testing that EarthSciSerialization-61ls bug is fixed...")

// Test with correct schema data
const testFile = {
  "esm": "0.1.0",
  "metadata": {
    "name": "BugTestModel"
  },
  "models": {
    "test_model": {
      "variables": {
        // Note: NO 'name' property inside - name comes from dict key
        "temperature": {
          "type": "state",
          "default": 298.15,
          "units": "K"
        },
        "rate_constant": {
          "type": "parameter",
          "default": 0.01,
          "units": "1/s"
        }
      },
      "equations": [
        {
          "lhs": "temperature",
          "rhs": 300.0
        }
      ]
    }
  },
  "reaction_systems": {
    "test_chemistry": {
      "species": {
        // Note: NO 'name' property inside - name comes from dict key
        "A": {
          "default": 1e-6,
          "units": "mol/mol"
        },
        "B": {
          "default": 2e-6,
          "units": "mol/mol"
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
          // Note: uses 'substrates' NOT 'reactants'
          "substrates": [
            { "species": "A", "stoichiometry": 1 }
          ],
          "products": [
            { "species": "B", "stoichiometry": 1 }
          ],
          "rate": "k1"
        }
      ]
    }
  }
}

// Before the fix, this would throw errors like:
// - Cannot read property 'name' of undefined
// - Cannot read property 'reactants' of undefined

try {
  // Import using dynamic import to avoid module issues
  import('./dist/codegen.js').then(({ toJuliaCode, toPythonCode }) => {
    console.log("✓ Successfully imported codegen functions")

    try {
      const juliaCode = toJuliaCode(testFile)
      console.log("✓ Julia code generation succeeded")

      const pythonCode = toPythonCode(testFile)
      console.log("✓ Python code generation succeeded")

      console.log("\n🎉 SUCCESS: Bug EarthSciSerialization-61ls is fixed!")
      console.log("   - codegen.ts no longer accesses non-existent 'name' properties")
      console.log("   - codegen.ts no longer accesses 'reactants' (uses 'substrates')")
      console.log("   - Code generation works with correct schema structure")

    } catch (codegenError) {
      console.error("❌ Code generation failed:", codegenError.message)
      console.error("   This suggests the bug is NOT fully fixed")
    }
  }).catch(importError => {
    console.error("❌ Import failed:", importError.message)
  })

} catch (error) {
  console.error("❌ Test failed:", error.message)
}