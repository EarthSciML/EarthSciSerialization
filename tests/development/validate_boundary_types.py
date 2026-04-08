#!/usr/bin/env python3
import json
import re

# Read schema
with open('esm-schema.json', 'r') as f:
    schema = f.read()

# Extract boundary condition types from schema
boundary_types = []
lines = schema.split('\n')
for i, line in enumerate(lines):
    if 'BoundaryCondition' in line:
        # Find the enum line within the next 20 lines
        for j in range(i, min(i+20, len(lines))):
            if '"enum":' in lines[j] and any(t in lines[j] for t in ['constant', 'periodic']):
                enum_line = lines[j]
                # Extract the types
                match = re.search(r'\[([^\]]+)\]', enum_line)
                if match:
                    types_str = match.group(1)
                    types = [t.strip().strip('"') for t in types_str.split(',')]
                    boundary_types = types
                    break
        break

print('Boundary condition types found in schema:', boundary_types)

# Read spec file
with open('esm-spec.md', 'r') as f:
    spec = f.read()

# Check if all types are documented
documented_types = []
spec_lines = spec.split('\n')
for line in spec_lines:
    if '| `' in line and any(t in line for t in boundary_types):
        match = re.search(r'\| `([^`]+)`', line)
        if match:
            documented_types.append(match.group(1))

print('Boundary condition types documented in spec:', documented_types)

missing_in_spec = set(boundary_types) - set(documented_types)
if missing_in_spec:
    print('ERROR: Types in schema but not in spec:', missing_in_spec)
    exit(1)
else:
    print('SUCCESS: All schema types are documented in spec')