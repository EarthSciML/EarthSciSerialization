#!/usr/bin/env python3
"""
Integration test for graph exports that avoids pandas dependency.
"""

import sys
import os

# Add the esm_format source directory to path
sys.path.insert(0, '/home/ctessum/EarthSciSerialization/packages/esm_format/src')

# Mock problematic imports to avoid pandas dependency
sys.modules['pandas'] = type('MockPandas', (), {})()

try:
    # This might still fail due to other dependencies
    from esm_format.graph import Graph, GraphNode, GraphEdge
    print("✓ Successfully imported graph modules")
    integration_success = True
except ImportError as e:
    print(f"✗ Import failed: {e}")
    integration_success = False

if integration_success:
    # Test basic functionality
    graph = Graph()
    graph.nodes.append(GraphNode("test", "Test Node", "test"))

    # Test exports
    dot_output = graph.to_dot()
    mermaid_output = graph.to_mermaid()
    json_output = graph.to_json_graph()

    print("✓ All export methods callable")
    print("✓ Integration test passed")
else:
    print("✗ Integration test failed due to import issues")
