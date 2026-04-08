#!/usr/bin/env python3

import sys
import os

# Add the source directory to the path
src_path = os.path.join(os.path.dirname(__file__), 'packages/esm_format/src')
sys.path.insert(0, src_path)

# Import modules directly without going through __init__.py
sys.path.insert(0, os.path.join(src_path, 'esm_format'))

from esm_types import (
    Metadata, Species, Reaction, ReactionSystem, CouplingEntry,
    CouplingType, EsmFile
)
from coupling_graph import construct_coupling_graph

def test_coupling_resolution():
    """Test basic coupling resolution between systems."""

    print("Testing coupling resolution logic...")

    # Create metadata
    metadata = Metadata(title='Test Coupling', version='1.0')

    # System 1: A -> B
    species_A = Species(name='A')
    species_B = Species(name='B')
    reaction1 = Reaction(
        name='r1',
        reactants={'A': 1.0},
        products={'B': 1.0},
        rate_constant=0.1
    )
    system1 = ReactionSystem(
        name='system1',
        species=[species_A, species_B],
        reactions=[reaction1]
    )

    # System 2: B -> C
    species_B2 = Species(name='B')  # Same species B shared between systems
    species_C = Species(name='C')
    reaction2 = Reaction(
        name='r2',
        reactants={'B': 1.0},
        products={'C': 1.0},
        rate_constant=0.05
    )
    system2 = ReactionSystem(
        name='system2',
        species=[species_B2, species_C],
        reactions=[reaction2]
    )

    # Create coupling rule: Variable map from system1.B to system2.B
    coupling = CouplingEntry(
        coupling_type=CouplingType.VARIABLE_MAP,
        from_var='system1.B',
        to_var='system2.B',
        transform='identity',
        factor=1.0
    )

    # Create ESM file
    esm_file = EsmFile(
        version='1.0',
        metadata=metadata,
        reaction_systems={'system1': system1, 'system2': system2},
        couplings=[coupling]
    )

    print(f"Created ESM file with {len(esm_file.reaction_systems)} reaction systems")
    print(f"System 1 species: {[s.name for s in system1.species]}")
    print(f"System 2 species: {[s.name for s in system2.species]}")
    print(f"Coupling rules: {len(esm_file.coupling)}")

    # Test coupling graph construction
    try:
        graph = construct_coupling_graph(esm_file)
        print(f"Successfully constructed coupling graph")
        print(f"Nodes: {len(graph.nodes)}")
        print(f"Edges: {len(graph.edges)}")

        # Get execution order
        execution_order = graph.get_execution_order()
        print(f"Execution order: {execution_order}")

    except Exception as e:
        print(f"Error constructing coupling graph: {e}")
        return False

    # Test coupling resolution function directly
    try:
        from simulation import _resolve_coupled_systems
        species_names, ode_exprs = _resolve_coupled_systems(esm_file, {})
        print(f"Coupling resolution successful")
        print(f"Combined species: {species_names}")
        print(f"Number of ODEs: {len(ode_exprs)}")

        # Species should be [A, B, C] with proper coupling
        expected_species = {'A', 'B', 'C'}
        actual_species = set(species_names)
        if actual_species == expected_species:
            print("✓ Species coupling resolved correctly")
            return True
        else:
            print(f"✗ Species mismatch. Expected {expected_species}, got {actual_species}")
            return False

    except Exception as e:
        print(f"Error in coupling resolution: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_coupling_resolution()
    if success:
        print("\n✓ Coupling resolution test passed!")
        sys.exit(0)
    else:
        print("\n✗ Coupling resolution test failed!")
        sys.exit(1)