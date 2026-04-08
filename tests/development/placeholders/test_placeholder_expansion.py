#!/usr/bin/env python3
"""
Test script for _var placeholder expansion in operator_compose couplings.
"""

import json
import sys
sys.path.append('packages/esm_format/src')

from esm_format import (
    load, process_operator_compose_placeholders, has_var_placeholder,
    get_state_variables, expand_model_placeholders
)

def test_placeholder_expansion():
    """Test the placeholder expansion functionality."""

    # Create a test ESM file similar to the fixture
    test_esm = {
        "esm": "0.1.0",
        "metadata": {"name": "TestPlaceholderExpansion"},
        "models": {
            "ChemistrySystem": {
                "variables": {
                    "O3": {"type": "state", "units": "mol/mol", "default": 40e-9},
                    "NO": {"type": "state", "units": "mol/mol", "default": 0.1e-9},
                    "NO2": {"type": "state", "units": "mol/mol", "default": 0.2e-9}
                },
                "equations": [
                    {
                        "lhs": {"op": "D", "args": ["O3"], "wrt": "t"},
                        "rhs": {"op": "*", "args": [-1, "k1", "O3"]}
                    },
                    {
                        "lhs": {"op": "D", "args": ["NO"], "wrt": "t"},
                        "rhs": {"op": "*", "args": ["k2", "NO2"]}
                    },
                    {
                        "lhs": {"op": "D", "args": ["NO2"], "wrt": "t"},
                        "rhs": {"op": "*", "args": [-1, "k2", "NO2"]}
                    }
                ]
            },
            "AdvectionSystem": {
                "variables": {
                    "u": {"type": "parameter", "units": "m/s", "default": 3.0},
                    "v": {"type": "parameter", "units": "m/s", "default": 4.0}
                },
                "equations": [
                    {
                        "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                        "rhs": {
                            "op": "+", "args": [
                                {"op": "*", "args": [
                                    {"op": "-", "args": ["u"]},
                                    {"op": "grad", "args": ["_var"], "dim": "x"}
                                ]},
                                {"op": "*", "args": [
                                    {"op": "-", "args": ["v"]},
                                    {"op": "grad", "args": ["_var"], "dim": "y"}
                                ]}
                            ]
                        }
                    }
                ]
            }
        },
        "coupling": [
            {
                "type": "operator_compose",
                "systems": ["ChemistrySystem", "AdvectionSystem"],
                "description": "Test coupling with placeholder expansion"
            }
        ]
    }

    # Save the test ESM to a temporary file
    with open("/tmp/test_esm.json", "w") as f:
        json.dump(test_esm, f, indent=2)

    print("🧪 Testing placeholder expansion functionality...")

    # Load the ESM file
    esm_file = load("/tmp/test_esm.json")
    print("✓ ESM file loaded successfully")

    # Check if the AdvectionSystem has _var placeholders
    advection_model = esm_file.models["AdvectionSystem"]
    has_placeholder = any(
        has_var_placeholder(eq.lhs) or has_var_placeholder(eq.rhs)
        for eq in advection_model.equations
    )
    print(f"✓ AdvectionSystem has _var placeholders: {has_placeholder}")

    # Get state variables from ChemistrySystem
    chemistry_model = esm_file.models["ChemistrySystem"]
    state_vars = get_state_variables(chemistry_model)
    print(f"✓ State variables from ChemistrySystem: {state_vars}")

    # Process operator_compose placeholders
    expanded_esm = process_operator_compose_placeholders(esm_file)
    print("✓ Processed operator_compose placeholders")

    # Check the result
    expanded_advection = expanded_esm.models["AdvectionSystem"]
    print(f"✓ Original AdvectionSystem equations: {len(advection_model.equations)}")
    print(f"✓ Expanded AdvectionSystem equations: {len(expanded_advection.equations)}")

    # Verify expansion worked
    if len(expanded_advection.equations) == len(state_vars):
        print("✅ SUCCESS: Placeholder expansion created the correct number of equations!")

        # Show the expanded equations
        for i, eq in enumerate(expanded_advection.equations):
            lhs_var = eq.lhs.args[0] if hasattr(eq.lhs, 'args') else str(eq.lhs)
            print(f"   Equation {i+1}: d{lhs_var}/dt = ...")

        # Verify no more _var placeholders exist
        still_has_placeholder = any(
            has_var_placeholder(eq.lhs) or has_var_placeholder(eq.rhs)
            for eq in expanded_advection.equations
        )

        if not still_has_placeholder:
            print("✅ SUCCESS: No _var placeholders remain after expansion!")
        else:
            print("❌ ERROR: Some _var placeholders still remain")

    else:
        print(f"❌ ERROR: Expected {len(state_vars)} equations, got {len(expanded_advection.equations)}")

    return expanded_esm

if __name__ == "__main__":
    try:
        result = test_placeholder_expansion()
        print("\n🎉 Placeholder expansion test completed!")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()