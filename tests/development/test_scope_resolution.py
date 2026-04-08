#!/usr/bin/env python3
"""
Test script for hierarchical scope resolution to verify the multi-level subsystem issue.
"""

import sys
import os
import json
import importlib.util

# Import modules directly
base_path = os.path.join(os.path.dirname(__file__), 'packages', 'esm_format', 'src', 'esm_format')

# Load hierarchical_scope_resolution module
spec = importlib.util.spec_from_file_location("hierarchical_scope_resolution", os.path.join(base_path, "hierarchical_scope_resolution.py"))
hierarchical_scope_resolution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hierarchical_scope_resolution)

# Load esm_types module
spec = importlib.util.spec_from_file_location("esm_types", os.path.join(base_path, "esm_types.py"))
esm_types = importlib.util.module_from_spec(spec)
spec.loader.exec_module(esm_types)

# Load parse module - this might be complex, let's try a simple approach
# First, let's just create a simple parser for JSON
def simple_parse_model(data):
    """Simple parser for Model data"""
    from dataclasses import field
    from typing import Dict

    model = esm_types.Model(
        name=data['name'] if 'name' in data else 'Unknown',
        variables={},
        equations=[],
        subsystems={}
    )

    # Parse variables
    if 'variables' in data:
        for var_name, var_data in data['variables'].items():
            model.variables[var_name] = esm_types.ModelVariable(
                type=var_data.get('type', 'parameter'),
                units=var_data.get('units', None),
                default=var_data.get('default', None),
                description=var_data.get('description', None)
            )

    # Parse subsystems recursively
    if 'subsystems' in data:
        for subsys_name, subsys_data in data['subsystems'].items():
            subsys_data['name'] = subsys_name  # Ensure name is set
            model.subsystems[subsys_name] = simple_parse_model(subsys_data)

    return model

# Load the test file with hierarchical scoped references
test_file_path = "tests/scoping/hierarchical_scoped_references.esm"
print(f"Loading test file: {test_file_path}")

with open(test_file_path) as f:
    data = json.load(f)

# Create EsmFile manually
esm_file = esm_types.EsmFile(
    models={},
    reaction_systems={},
    coupling=[],
    events=[],
    operators={},
    data_loaders={},
    domain=None,
    solver=None,
    metadata={}
)

# Parse models
if 'models' in data:
    for model_name, model_data in data['models'].items():
        model_data['name'] = model_name  # Ensure name is set
        esm_file.models[model_name] = simple_parse_model(model_data)

# Create the resolver
HierarchicalScopeResolver = hierarchical_scope_resolution.HierarchicalScopeResolver
resolver = HierarchicalScopeResolver(esm_file)

# Test cases that should work but currently fail
test_cases = [
    "ParentSystem.SubsystemA.DeepSubA.deep_variable",
    "ParentSystem.SubsystemB.DeepSubB1.oscillator",
    "ParentSystem.SubsystemB.DeepSubB2.feedback_state",
    "ParentSystem.SubsystemA.local_state",  # Single level should work
    "ParentSystem.global_parameter",  # Top level should work
]

print("\n=== Testing current scope resolution behavior ===")
for test_case in test_cases:
    print(f"\nTesting: {test_case}")
    try:
        result = resolver.resolve_variable(test_case)
        print(f"  Found: {result.found}")
        print(f"  System: {result.system_name}")
        print(f"  Variable: {result.variable_name}")
        print(f"  Full Path: {result.full_path}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n=== System Structure Analysis ===")
# Let's also analyze the system structure
for model_name, model in esm_file.models.items():
    print(f"\nModel: {model_name}")
    print(f"  Variables: {list(model.variables.keys()) if model.variables else []}")
    if hasattr(model, 'subsystems') and model.subsystems:
        print(f"  Subsystems: {list(model.subsystems.keys())}")
        for subsys_name, subsys in model.subsystems.items():
            print(f"    {subsys_name}:")
            print(f"      Variables: {list(subsys.variables.keys()) if subsys.variables else []}")
            if hasattr(subsys, 'subsystems') and subsys.subsystems:
                print(f"      Sub-subsystems: {list(subsys.subsystems.keys())}")
                for sub_subsys_name, sub_subsys in subsys.subsystems.items():
                    print(f"        {sub_subsys_name}:")
                    print(f"          Variables: {list(sub_subsys.variables.keys()) if sub_subsys.variables else []}")