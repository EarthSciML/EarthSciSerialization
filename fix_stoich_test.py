#!/usr/bin/env python3
import re

# Read the file
with open('tests/stoichiometric_matrix.rs', 'r') as f:
    content = f.read()

# Replace patterns like "assert_eq!(matrix[0][0], -1," with "assert_eq!(matrix[0][0], -1.0,"
# This handles integer literals in assert_eq! macros for matrix elements
pattern = r'assert_eq!\(matrix\[(\d+)\]\[(\d+)\], (-?\d+),'
replacement = r'assert_eq!(matrix[\1][\2], \3.0,'

content = re.sub(pattern, replacement, content)

# Write back
with open('tests/stoichiometric_matrix.rs', 'w') as f:
    f.write(content)

print("Fixed stoichiometric matrix test file")