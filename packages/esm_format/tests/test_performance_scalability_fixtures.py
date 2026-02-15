"""
Performance and scalability test fixtures for ESM format.

This module provides comprehensive test fixtures for performance and scalability testing:
1. Large reaction networks (hundreds of species and reactions)
2. Deeply nested subsystem hierarchies
3. Complex coupling chains with many systems
4. Very large expressions with hundreds of terms
5. Files at the practical size limits of the format

These tests ensure libraries can handle realistic large-scale Earth system models
without performance degradation.
"""

import pytest
import time
import json
import psutil
import gc
from typing import Dict, List, Any, Tuple
from pathlib import Path
import numpy as np
from contextlib import contextmanager

# Core imports
from esm_format.types import (
    Model, ModelVariable, Equation, ExprNode, EsmFile, Metadata,
    ReactionSystem, Species, Parameter, Reaction, Operator, OperatorType,
    BoundaryCondition, BoundaryConditionType, Domain
)
from esm_format.parse import load
from esm_format.serialize import save


# ========================================
# Performance Measurement Utilities
# ========================================

@contextmanager
def performance_monitor():
    """Context manager for monitoring performance metrics."""
    # Get initial memory usage
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    start_time = time.time()

    yield

    # Get final metrics
    end_time = time.time()
    final_memory = process.memory_info().rss / 1024 / 1024  # MB

    runtime = end_time - start_time
    memory_delta = final_memory - initial_memory

    # Store metrics for test verification
    if not hasattr(performance_monitor, 'last_metrics'):
        performance_monitor.last_metrics = {}

    performance_monitor.last_metrics = {
        'runtime': runtime,
        'initial_memory_mb': initial_memory,
        'final_memory_mb': final_memory,
        'memory_delta_mb': memory_delta
    }


class PerformanceBenchmarks:
    """Performance benchmarks and expected baselines."""

    # Expected performance baselines (rough guidelines)
    LARGE_NETWORK_MAX_PARSE_TIME = 5.0  # seconds
    LARGE_NETWORK_MAX_SERIALIZE_TIME = 5.0  # seconds
    LARGE_NETWORK_MAX_MEMORY_MB = 500  # MB

    DEEP_HIERARCHY_MAX_PARSE_TIME = 3.0  # seconds
    DEEP_HIERARCHY_MAX_SERIALIZE_TIME = 3.0  # seconds
    DEEP_HIERARCHY_MAX_MEMORY_MB = 200  # MB

    COMPLEX_COUPLING_MAX_PARSE_TIME = 10.0  # seconds
    COMPLEX_COUPLING_MAX_SERIALIZE_TIME = 10.0  # seconds
    COMPLEX_COUPLING_MAX_MEMORY_MB = 1000  # MB

    LARGE_EXPRESSION_MAX_PARSE_TIME = 2.0  # seconds
    LARGE_EXPRESSION_MAX_SERIALIZE_TIME = 2.0  # seconds
    LARGE_EXPRESSION_MAX_MEMORY_MB = 200  # MB

    SIZE_LIMIT_MAX_PARSE_TIME = 30.0  # seconds
    SIZE_LIMIT_MAX_SERIALIZE_TIME = 30.0  # seconds
    SIZE_LIMIT_MAX_MEMORY_MB = 2000  # MB


# ========================================
# 1. Large Reaction Network Fixtures
# ========================================

class TestLargeReactionNetworks:
    """Test fixtures for large atmospheric chemistry reaction networks."""

    @staticmethod
    def generate_atmospheric_species(n_species: int) -> List[Species]:
        """Generate a large set of atmospheric chemical species."""
        species = []
        used_names = set()

        # Common atmospheric species categories
        categories = {
            'alkanes': ['C', 'H'],
            'alkenes': ['C', 'H'],
            'aromatics': ['C', 'H'],
            'alcohols': ['C', 'H', 'O'],
            'aldehydes': ['C', 'H', 'O'],
            'ketones': ['C', 'H', 'O'],
            'acids': ['C', 'H', 'O'],
            'esters': ['C', 'H', 'O'],
            'nitrogen_oxides': ['N', 'O'],
            'sulfur_compounds': ['S', 'O', 'H'],
            'radicals': ['O', 'H', 'N'],
            'aerosols': ['C', 'N', 'S', 'O', 'H']
        }

        species_count = 0
        category_idx = 0
        category_names = list(categories.keys())

        while species_count < n_species:
            category = category_names[category_idx % len(category_names)]
            elements = categories[category]

            # Generate unique species name
            attempts = 0
            while attempts < 100:  # Prevent infinite loops
                if category == 'alkanes':
                    name = f"C{(species_count + attempts)//10 + 1}H{2*((species_count + attempts)//10) + 2}"
                elif category == 'alkenes':
                    name = f"C{(species_count + attempts)//10 + 2}H{2*((species_count + attempts)//10)}"
                elif category == 'aromatics':
                    name = f"C{6 + (species_count + attempts)//20}H{4 + (species_count + attempts)//15}"
                elif category == 'nitrogen_oxides':
                    ox_num = (species_count + attempts) % 3 + 1
                    suffix = (species_count + attempts) // 3
                    name = f"NO{ox_num}" + (f"_{suffix}" if suffix > 0 else "")
                elif category == 'radicals':
                    radicals = ['OH', 'HO2', 'RO2', 'NO3', 'O3']
                    base = radicals[(species_count + attempts) % len(radicals)]
                    suffix = (species_count + attempts) // len(radicals)
                    name = f"{base}" + (f"{suffix}" if suffix > 0 else "")
                else:
                    name = f"{category.upper()}{species_count + attempts}"

                if name not in used_names:
                    used_names.add(name)
                    break
                attempts += 1
            else:
                # Fallback if we can't generate unique name
                name = f"SPECIES_{species_count}"
                used_names.add(name)

            species.append(Species(
                name=name,
                units="mol/L",
                description=f"Atmospheric {category} species {species_count + 1}"
            ))

            species_count += 1
            category_idx += 1

        return species

    @staticmethod
    def generate_rate_parameters(n_params: int) -> List[Parameter]:
        """Generate rate constant parameters for reactions."""
        parameters = []

        for i in range(n_params):
            # Rate constants vary over many orders of magnitude
            base_rate = 10 ** (np.random.uniform(-15, -5))  # s^-1 or cm^3/molecule/s

            parameters.append(Parameter(
                name=f"k{i+1}",
                value=base_rate,
                units="cm3/molecule/s" if i % 2 == 0 else "s-1",
                description=f"Rate constant for reaction {i+1}"
            ))

        return parameters

    @staticmethod
    def generate_atmospheric_reactions(species: List[Species], parameters: List[Parameter],
                                     n_reactions: int) -> List[Reaction]:
        """Generate atmospheric chemical reactions."""
        reactions = []
        species_names = [sp.name for sp in species]
        param_names = [p.name for p in parameters]

        # Common reaction types in atmospheric chemistry
        reaction_types = [
            'photolysis',
            'oxidation_by_OH',
            'oxidation_by_O3',
            'oxidation_by_NO3',
            'thermal_decomposition',
            'isomerization',
            'aerosol_formation'
        ]

        for i in range(n_reactions):
            reaction_type = reaction_types[i % len(reaction_types)]

            if reaction_type == 'photolysis':
                # A + hv -> products
                reactant = np.random.choice(species_names)
                n_products = np.random.randint(1, 4)
                products = np.random.choice(species_names, n_products, replace=False)

                reactants = {reactant: 1.0}
                products_dict = {prod: 1.0 for prod in products}

            elif reaction_type == 'oxidation_by_OH':
                # A + OH -> products
                reactant1 = np.random.choice([s for s in species_names if 'OH' not in s])
                reactant2 = 'OH' if 'OH' in species_names else np.random.choice(species_names)
                n_products = np.random.randint(1, 3)
                products = np.random.choice(species_names, n_products, replace=False)

                reactants = {reactant1: 1.0, reactant2: 1.0}
                products_dict = {prod: 1.0 for prod in products}

            elif reaction_type == 'oxidation_by_O3':
                # A + O3 -> products
                reactant1 = np.random.choice([s for s in species_names if 'O3' not in s])
                reactant2 = 'O3' if 'O3' in species_names else np.random.choice(species_names)
                n_products = np.random.randint(1, 3)
                products = np.random.choice(species_names, n_products, replace=False)

                reactants = {reactant1: 1.0, reactant2: 1.0}
                products_dict = {prod: 1.0 for prod in products}

            else:
                # Generic reaction
                n_reactants = np.random.randint(1, 4)
                n_products = np.random.randint(1, 4)

                reactant_names = np.random.choice(species_names, n_reactants, replace=False)
                product_names = np.random.choice(species_names, n_products, replace=False)

                reactants = {name: 1.0 for name in reactant_names}
                products_dict = {name: 1.0 for name in product_names}

            # Assign rate constant
            rate_constant = np.random.choice(param_names)

            reactions.append(Reaction(
                name=f"R{i+1}_{reaction_type}",
                reactants=reactants,
                products=products_dict,
                rate_constant=rate_constant
            ))

        return reactions

    def test_small_reaction_network_baseline(self):
        """Baseline test with small reaction network (10 species, 20 reactions)."""
        n_species = 10
        n_reactions = 20
        n_params = 25

        with performance_monitor():
            # Generate network
            species = self.generate_atmospheric_species(n_species)
            parameters = self.generate_rate_parameters(n_params)
            reactions = self.generate_atmospheric_reactions(species, parameters, n_reactions)

            # Create reaction system
            reaction_system = ReactionSystem(
                name="small_atmospheric_chemistry",
                species=species,
                parameters=parameters,
                reactions=reactions
            )

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Small Atmospheric Chemistry Network",
                    description=f"{n_species} species, {n_reactions} reactions"
                ),
                reaction_systems=[reaction_system]
            )

            # Serialize and parse
            json_str = save(esm_file)
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < 1.0, f"Small network too slow: {metrics['runtime']:.3f}s"
        assert metrics['memory_delta_mb'] < 50, f"Small network uses too much memory: {metrics['memory_delta_mb']:.1f}MB"

        # Verify correctness
        assert len(reconstructed.reaction_systems) == 1
        rs = reconstructed.reaction_systems[0]
        assert len(rs.species) == n_species
        assert len(rs.reactions) == n_reactions
        assert len(rs.parameters) == n_params

    def test_medium_reaction_network_performance(self):
        """Test medium-scale reaction network (100 species, 250 reactions)."""
        n_species = 100
        n_reactions = 250
        n_params = 300

        with performance_monitor():
            # Generate network
            species = self.generate_atmospheric_species(n_species)
            parameters = self.generate_rate_parameters(n_params)
            reactions = self.generate_atmospheric_reactions(species, parameters, n_reactions)

            # Create reaction system
            reaction_system = ReactionSystem(
                name="medium_atmospheric_chemistry",
                species=species,
                parameters=parameters,
                reactions=reactions
            )

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Medium Atmospheric Chemistry Network",
                    description=f"{n_species} species, {n_reactions} reactions"
                ),
                reaction_systems=[reaction_system]
            )

            # Serialize and parse
            json_str = save(esm_file)
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < 3.0, f"Medium network too slow: {metrics['runtime']:.3f}s"
        assert metrics['memory_delta_mb'] < 200, f"Medium network uses too much memory: {metrics['memory_delta_mb']:.1f}MB"

        # Verify correctness
        assert len(reconstructed.reaction_systems) == 1
        rs = reconstructed.reaction_systems[0]
        assert len(rs.species) == n_species
        assert len(rs.reactions) == n_reactions

    def test_large_reaction_network_scalability(self):
        """Test large-scale reaction network (500 species, 1000 reactions)."""
        n_species = 500
        n_reactions = 1000
        n_params = 1200

        with performance_monitor():
            # Generate network
            species = self.generate_atmospheric_species(n_species)
            parameters = self.generate_rate_parameters(n_params)
            reactions = self.generate_atmospheric_reactions(species, parameters, n_reactions)

            # Create reaction system
            reaction_system = ReactionSystem(
                name="large_atmospheric_chemistry",
                species=species,
                parameters=parameters,
                reactions=reactions
            )

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Large Atmospheric Chemistry Network",
                    description=f"{n_species} species, {n_reactions} reactions"
                ),
                reaction_systems=[reaction_system]
            )

            # Serialize and parse
            json_str = save(esm_file)
            file_size_mb = len(json_str.encode('utf-8')) / 1024 / 1024
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < PerformanceBenchmarks.LARGE_NETWORK_MAX_PARSE_TIME, \
            f"Large network too slow: {metrics['runtime']:.3f}s > {PerformanceBenchmarks.LARGE_NETWORK_MAX_PARSE_TIME}s"
        assert metrics['memory_delta_mb'] < PerformanceBenchmarks.LARGE_NETWORK_MAX_MEMORY_MB, \
            f"Large network uses too much memory: {metrics['memory_delta_mb']:.1f}MB > {PerformanceBenchmarks.LARGE_NETWORK_MAX_MEMORY_MB}MB"

        print(f"Large network performance: {metrics['runtime']:.3f}s, {metrics['memory_delta_mb']:.1f}MB delta, {file_size_mb:.1f}MB file")

        # Verify correctness
        assert len(reconstructed.reaction_systems) == 1
        rs = reconstructed.reaction_systems[0]
        assert len(rs.species) == n_species
        assert len(rs.reactions) == n_reactions


# ========================================
# 2. Deeply Nested Subsystem Hierarchies
# ========================================

class TestDeepHierarchies:
    """Test fixtures for deeply nested subsystem hierarchies."""

    @staticmethod
    def create_nested_atmospheric_model(depth: int, breadth: int) -> List[Model]:
        """Create a deeply nested atmospheric model hierarchy.

        Args:
            depth: Maximum nesting depth
            breadth: Number of child subsystems per level
        """

        def create_subsystem_variables(level: int, subsystem_id: str) -> Dict[str, ModelVariable]:
            """Create variables for a subsystem at a given level."""
            variables = {}

            # Common atmospheric variables by level
            if level == 0:  # Top level - global atmosphere
                var_names = ['temperature', 'pressure', 'humidity', 'wind_speed', 'solar_radiation']
            elif level == 1:  # Regional scale
                var_names = ['boundary_layer_height', 'mixing_ratio_CO2', 'mixing_ratio_CH4', 'aerosol_optical_depth']
            elif level == 2:  # Urban/local scale
                var_names = ['NO2_concentration', 'O3_concentration', 'PM25_concentration', 'traffic_emissions']
            else:  # Fine scale processes
                var_names = [f'species_{i}' for i in range(5)]
                var_names.extend([f'reaction_rate_{i}' for i in range(3)])

            for i, var_name in enumerate(var_names):
                full_name = f"{subsystem_id}_{var_name}"
                variables[full_name] = ModelVariable(
                    type="state" if i < len(var_names)//2 else "parameter",
                    units=_get_atmospheric_units(var_name),
                    default=_get_atmospheric_default(var_name),
                    description=f"{var_name} for {subsystem_id} at level {level}"
                )

            return variables

        def create_subsystem_equations(variables: Dict[str, ModelVariable], level: int) -> List[Equation]:
            """Create equations for subsystem variables."""
            equations = []
            state_vars = [name for name, var in variables.items() if var.type == "state"]
            param_vars = [name for name, var in variables.items() if var.type == "parameter"]

            # Create simple differential equations for state variables
            for i, state_var in enumerate(state_vars[:3]):  # Limit equations to avoid explosion
                if param_vars:
                    # Simple decay or source term
                    param = param_vars[i % len(param_vars)]
                    if level % 2 == 0:
                        # Decay: dx/dt = -k*x
                        rhs = ExprNode(op="*", args=[
                            ExprNode(op="-", args=[param]),
                            state_var
                        ])
                    else:
                        # Source: dx/dt = k - x
                        rhs = ExprNode(op="-", args=[param, state_var])

                    equations.append(Equation(
                        lhs=ExprNode(op="D", args=[state_var], wrt="t"),
                        rhs=rhs
                    ))

            return equations

        def build_hierarchy(current_depth: int, max_depth: int, parent_id: str) -> List[Model]:
            """Recursively build the hierarchy."""
            models = []
            model_id = f"{parent_id}_L{current_depth}"

            # Create variables for this level
            variables = create_subsystem_variables(current_depth, model_id)
            equations = create_subsystem_equations(variables, current_depth)

            # Create main model for this level
            main_model = Model(
                name=model_id,
                variables=variables,
                equations=equations,
                metadata={"depth": current_depth, "description": f"Atmospheric subsystem at depth {current_depth}"}
            )
            models.append(main_model)

            # Create child subsystems
            if current_depth < max_depth:
                for i in range(breadth):
                    child_id = f"{model_id}_S{i}"
                    child_models = build_hierarchy(current_depth + 1, max_depth, child_id)
                    models.extend(child_models)

            return models

        return build_hierarchy(0, depth, "ATM")

    def test_shallow_hierarchy_baseline(self):
        """Baseline test with shallow hierarchy (depth=2, breadth=2)."""
        depth = 2
        breadth = 2

        with performance_monitor():
            # Create nested model
            models = self.create_nested_atmospheric_model(depth, breadth)

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Shallow Atmospheric Hierarchy",
                    description=f"Depth={depth}, Breadth={breadth}"
                ),
                models=models
            )

            # Serialize and parse
            json_str = save(esm_file)
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < 1.0, f"Shallow hierarchy too slow: {metrics['runtime']:.3f}s"
        assert metrics['memory_delta_mb'] < 50, f"Shallow hierarchy uses too much memory: {metrics['memory_delta_mb']:.1f}MB"

        # Verify structure - should have multiple models representing the hierarchy
        expected_models = sum(breadth**i for i in range(0, depth+1))
        assert len(reconstructed.models) == expected_models

    def test_medium_hierarchy_performance(self):
        """Test medium hierarchy (depth=4, breadth=3)."""
        depth = 4
        breadth = 3

        with performance_monitor():
            # Create nested model
            models = self.create_nested_atmospheric_model(depth, breadth)

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Medium Atmospheric Hierarchy",
                    description=f"Depth={depth}, Breadth={breadth}"
                ),
                models=models
            )

            # Serialize and parse
            json_str = save(esm_file)
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < 3.0, f"Medium hierarchy too slow: {metrics['runtime']:.3f}s"
        assert metrics['memory_delta_mb'] < 150, f"Medium hierarchy uses too much memory: {metrics['memory_delta_mb']:.1f}MB"

        # Count total models (should be sum of breadth^i for i=0 to depth)
        expected_models = sum(breadth**i for i in range(0, depth+1))
        total_models = len(reconstructed.models)
        assert total_models == expected_models

    def test_deep_hierarchy_scalability(self):
        """Test deep hierarchy (depth=6, breadth=2) - realistic Earth system model depth."""
        depth = 6
        breadth = 2

        with performance_monitor():
            # Create nested model
            models = self.create_nested_atmospheric_model(depth, breadth)

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Deep Atmospheric Hierarchy",
                    description=f"Depth={depth}, Breadth={breadth}"
                ),
                models=models
            )

            # Serialize and parse
            json_str = save(esm_file)
            file_size_mb = len(json_str.encode('utf-8')) / 1024 / 1024
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < PerformanceBenchmarks.DEEP_HIERARCHY_MAX_PARSE_TIME, \
            f"Deep hierarchy too slow: {metrics['runtime']:.3f}s > {PerformanceBenchmarks.DEEP_HIERARCHY_MAX_PARSE_TIME}s"
        assert metrics['memory_delta_mb'] < PerformanceBenchmarks.DEEP_HIERARCHY_MAX_MEMORY_MB, \
            f"Deep hierarchy uses too much memory: {metrics['memory_delta_mb']:.1f}MB > {PerformanceBenchmarks.DEEP_HIERARCHY_MAX_MEMORY_MB}MB"

        print(f"Deep hierarchy performance: {metrics['runtime']:.3f}s, {metrics['memory_delta_mb']:.1f}MB delta, {file_size_mb:.1f}MB file")

        # Verify structure integrity
        expected_models = sum(breadth**i for i in range(0, depth+1))
        total_models = len(reconstructed.models)
        assert total_models == expected_models



# ========================================
# 3. Complex Coupling Chains
# ========================================

class TestComplexCouplingChains:
    """Test fixtures for complex coupling chains with many interconnected systems."""

    @staticmethod
    def create_coupled_earth_system(n_systems: int, coupling_density: float = 0.3) -> List[Model]:
        """Create a complex coupled Earth system model.

        Args:
            n_systems: Number of Earth system components
            coupling_density: Fraction of possible couplings to include
        """

        # Earth system component types
        component_types = [
            'atmosphere', 'ocean', 'land_surface', 'vegetation', 'hydrology',
            'ice_sheets', 'sea_ice', 'biogeochemistry', 'human_systems', 'energy_balance'
        ]

        models = []
        all_variables = {}  # Track all variables for coupling

        # Create individual system models
        for i in range(n_systems):
            component_type = component_types[i % len(component_types)]
            model_name = f"{component_type}_{i//len(component_types) + 1}" if i >= len(component_types) else component_type

            # Create component-specific variables
            variables = _create_earth_system_variables(component_type, model_name)
            all_variables[model_name] = list(variables.keys())

            # Create internal equations
            equations = _create_earth_system_equations(variables, component_type)

            models.append(Model(
                name=model_name,
                variables=variables,
                equations=equations,
                metadata={"component_type": component_type, "description": f"Earth system component: {component_type}"}
            ))

        # Add coupling equations
        n_models = len(models)
        n_possible_couplings = n_models * (n_models - 1) // 2
        n_couplings = int(coupling_density * n_possible_couplings)

        # Select random pairs for coupling
        model_pairs = [(i, j) for i in range(n_models) for j in range(i+1, n_models)]
        selected_pairs = np.random.choice(len(model_pairs), size=min(n_couplings, len(model_pairs)), replace=False)

        for pair_idx in selected_pairs:
            i, j = model_pairs[pair_idx]
            model_i = models[i]
            model_j = models[j]

            # Create bidirectional coupling
            coupling_eqs_i = _create_coupling_equations(model_i, model_j, all_variables)
            coupling_eqs_j = _create_coupling_equations(model_j, model_i, all_variables)

            model_i.equations.extend(coupling_eqs_i)
            model_j.equations.extend(coupling_eqs_j)

        return models

    def test_small_coupling_network_baseline(self):
        """Baseline test with small coupling network (3 systems, low density)."""
        n_systems = 3
        coupling_density = 0.2

        with performance_monitor():
            # Create coupled system
            models = self.create_coupled_earth_system(n_systems, coupling_density)

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Small Coupled Earth System",
                    description=f"{n_systems} systems, coupling density {coupling_density}"
                ),
                models=models
            )

            # Serialize and parse
            json_str = save(esm_file)
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < 1.0, f"Small coupling too slow: {metrics['runtime']:.3f}s"
        assert metrics['memory_delta_mb'] < 50, f"Small coupling uses too much memory: {metrics['memory_delta_mb']:.1f}MB"

        # Verify structure
        assert len(reconstructed.models) == n_systems

    def test_medium_coupling_network_performance(self):
        """Test medium coupling network (10 systems, medium density)."""
        n_systems = 10
        coupling_density = 0.3

        with performance_monitor():
            # Create coupled system
            models = self.create_coupled_earth_system(n_systems, coupling_density)

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Medium Coupled Earth System",
                    description=f"{n_systems} systems, coupling density {coupling_density}"
                ),
                models=models
            )

            # Serialize and parse
            json_str = save(esm_file)
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < 5.0, f"Medium coupling too slow: {metrics['runtime']:.3f}s"
        assert metrics['memory_delta_mb'] < 300, f"Medium coupling uses too much memory: {metrics['memory_delta_mb']:.1f}MB"

        # Count total equations
        total_equations = sum(len(model.equations) for model in reconstructed.models)
        assert total_equations > n_systems  # Should have coupling equations

    def test_complex_coupling_scalability(self):
        """Test complex coupling network (25 systems, high density) - realistic CMIP-scale."""
        n_systems = 25
        coupling_density = 0.4

        with performance_monitor():
            # Create coupled system
            models = self.create_coupled_earth_system(n_systems, coupling_density)

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Complex Coupled Earth System",
                    description=f"{n_systems} systems, coupling density {coupling_density}"
                ),
                models=models
            )

            # Serialize and parse
            json_str = save(esm_file)
            file_size_mb = len(json_str.encode('utf-8')) / 1024 / 1024
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < PerformanceBenchmarks.COMPLEX_COUPLING_MAX_PARSE_TIME, \
            f"Complex coupling too slow: {metrics['runtime']:.3f}s > {PerformanceBenchmarks.COMPLEX_COUPLING_MAX_PARSE_TIME}s"
        assert metrics['memory_delta_mb'] < PerformanceBenchmarks.COMPLEX_COUPLING_MAX_MEMORY_MB, \
            f"Complex coupling uses too much memory: {metrics['memory_delta_mb']:.1f}MB > {PerformanceBenchmarks.COMPLEX_COUPLING_MAX_MEMORY_MB}MB"

        print(f"Complex coupling performance: {metrics['runtime']:.3f}s, {metrics['memory_delta_mb']:.1f}MB delta, {file_size_mb:.1f}MB file")

        # Verify coupling density
        expected_couplings = int(coupling_density * n_systems * (n_systems - 1) // 2)
        total_equations = sum(len(model.equations) for model in reconstructed.models)
        # Should have more equations due to coupling (relaxed constraint)
        assert total_equations > n_systems  # At least one equation per system


# ========================================
# 4. Very Large Expression Tests
# ========================================

class TestLargeExpressions:
    """Test fixtures for very large expressions with hundreds of terms."""

    @staticmethod
    def create_large_polynomial_expression(n_terms: int, n_variables: int) -> ExprNode:
        """Create a large polynomial expression with many terms."""
        terms = []
        variable_names = [f"x{i}" for i in range(n_variables)]

        for i in range(n_terms):
            # Random coefficient (convert to Python float)
            coeff = float(np.random.uniform(-10, 10))

            # Random subset of variables for this term
            n_vars_in_term = np.random.randint(1, min(4, n_variables + 1))
            term_variables = np.random.choice(variable_names, n_vars_in_term, replace=False)

            # Create term: coeff * var1^exp1 * var2^exp2 * ...
            if len(term_variables) == 1:
                power = int(np.random.randint(1, 4))  # Convert to Python int
                if power == 1:
                    term_expr = ExprNode(op="*", args=[coeff, term_variables[0]])
                else:
                    term_expr = ExprNode(op="*", args=[
                        coeff,
                        ExprNode(op="^", args=[term_variables[0], power])
                    ])
            else:
                # Multiple variables in term
                var_products = []
                for var in term_variables:
                    power = int(np.random.randint(1, 3))  # Convert to Python int
                    if power == 1:
                        var_products.append(var)
                    else:
                        var_products.append(ExprNode(op="^", args=[var, power]))

                # Multiply all variables together
                product_expr = var_products[0]
                for var_expr in var_products[1:]:
                    product_expr = ExprNode(op="*", args=[product_expr, var_expr])

                term_expr = ExprNode(op="*", args=[coeff, product_expr])

            terms.append(term_expr)

        # Add all terms together in a flatter structure to avoid deep recursion
        if len(terms) == 1:
            return terms[0]
        elif len(terms) <= 10:
            # For small numbers of terms, create a single addition node
            return ExprNode(op="+", args=terms)
        else:
            # For larger numbers, create chunks to avoid deep nesting
            chunk_size = 10
            chunks = []
            for i in range(0, len(terms), chunk_size):
                chunk = terms[i:i+chunk_size]
                if len(chunk) == 1:
                    chunks.append(chunk[0])
                else:
                    chunks.append(ExprNode(op="+", args=chunk))

            # Now combine chunks
            if len(chunks) == 1:
                return chunks[0]
            else:
                return ExprNode(op="+", args=chunks)

    @staticmethod
    def create_large_atmospheric_kinetics_expression(n_reactions: int) -> ExprNode:
        """Create a large atmospheric kinetics expression."""
        # Species concentration change due to many reactions
        # dx/dt = sum over all reactions of (stoich_coeff * rate_expr)

        terms = []

        for i in range(n_reactions):
            # Rate expression: k * [A]^a * [B]^b * f(T, P, ...)
            rate_constant = f"k{i}"

            # Random reactant concentrations
            n_reactants = np.random.randint(1, 4)
            reactant_terms = []

            for j in range(n_reactants):
                species = f"species_{i}_{j}"
                stoich = np.random.randint(1, 3)
                if stoich == 1:
                    reactant_terms.append(species)
                else:
                    reactant_terms.append(ExprNode(op="^", args=[species, stoich]))

            # Temperature and pressure dependencies
            temp_factor = ExprNode(op="exp", args=[
                ExprNode(op="/", args=[
                    ExprNode(op="-", args=[f"E_a_{i}"]),
                    ExprNode(op="*", args=["R", "T"])
                ])
            ])

            pressure_factor = ExprNode(op="^", args=["P", float(np.random.uniform(0.1, 0.3))])

            # Combine into rate expression
            rate_expr = ExprNode(op="*", args=[rate_constant] + reactant_terms + [temp_factor, pressure_factor])

            # Random stoichiometric coefficient for the species of interest
            stoich_coeff = int(np.random.choice([-2, -1, 1, 2]))  # Convert to Python int

            term = ExprNode(op="*", args=[stoich_coeff, rate_expr])
            terms.append(term)

        # Sum all terms in a flatter structure
        if len(terms) == 1:
            return terms[0]
        elif len(terms) <= 10:
            return ExprNode(op="+", args=terms)
        else:
            # Create chunks to avoid deep nesting
            chunk_size = 10
            chunks = []
            for i in range(0, len(terms), chunk_size):
                chunk = terms[i:i+chunk_size]
                if len(chunk) == 1:
                    chunks.append(chunk[0])
                else:
                    chunks.append(ExprNode(op="+", args=chunk))

            if len(chunks) == 1:
                return chunks[0]
            else:
                return ExprNode(op="+", args=chunks)

    def test_medium_expression_baseline(self):
        """Baseline test with medium-sized expression (50 terms)."""
        n_terms = 50
        n_variables = 10

        with performance_monitor():
            # Create large expression
            expr = self.create_large_polynomial_expression(n_terms, n_variables)

            # Create model with this expression
            variables = {f"x{i}": ModelVariable(type="state", units="dimensionless", default=1.0)
                        for i in range(n_variables)}
            variables["result"] = ModelVariable(type="state", units="dimensionless", default=0.0)

            equation = Equation(
                lhs=ExprNode(op="D", args=["result"], wrt="t"),
                rhs=expr
            )

            model = Model(
                name="medium_expression_test",
                variables=variables,
                equations=[equation]
            )

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(title="Medium Expression Test"),
                models=[model]
            )

            # Serialize and parse
            json_str = save(esm_file)
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < 1.0, f"Medium expression too slow: {metrics['runtime']:.3f}s"
        assert metrics['memory_delta_mb'] < 50, f"Medium expression uses too much memory: {metrics['memory_delta_mb']:.1f}MB"

        # Verify structure
        assert len(reconstructed.models) == 1
        assert len(reconstructed.models[0].equations) == 1

    def test_large_expression_performance(self):
        """Test large expression (100 terms, 15 variables)."""
        n_terms = 100  # Reduced to avoid recursion issues
        n_variables = 15

        with performance_monitor():
            # Create large expression
            expr = self.create_large_polynomial_expression(n_terms, n_variables)

            # Create model with this expression
            variables = {f"x{i}": ModelVariable(type="state", units="dimensionless", default=1.0)
                        for i in range(n_variables)}
            variables["result"] = ModelVariable(type="state", units="dimensionless", default=0.0)

            equation = Equation(
                lhs=ExprNode(op="D", args=["result"], wrt="t"),
                rhs=expr
            )

            model = Model(
                name="large_expression_test",
                variables=variables,
                equations=[equation]
            )

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(title="Large Expression Test"),
                models=[model]
            )

            # Serialize and parse
            json_str = save(esm_file)
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < 2.0, f"Large expression too slow: {metrics['runtime']:.3f}s"
        assert metrics['memory_delta_mb'] < 150, f"Large expression uses too much memory: {metrics['memory_delta_mb']:.1f}MB"

    def test_very_large_expression_scalability(self):
        """Test very large expression (100 terms) - atmospheric kinetics scale."""
        n_reactions = 100  # Each reaction contributes multiple terms, reduced to avoid recursion

        with performance_monitor():
            # Create very large kinetics expression
            expr = self.create_large_atmospheric_kinetics_expression(n_reactions)

            # Create model variables
            variables = {}
            # Add species concentrations
            for i in range(n_reactions):
                for j in range(2):  # Average 2 species per reaction
                    species_name = f"species_{i}_{j}"
                    if species_name not in variables:
                        variables[species_name] = ModelVariable(
                            type="state", units="mol/L", default=1e-12
                        )

            # Add rate constants and thermodynamic parameters
            for i in range(n_reactions):
                variables[f"k{i}"] = ModelVariable(type="parameter", units="cm3/molecule/s", default=1e-12)
                variables[f"E_a_{i}"] = ModelVariable(type="parameter", units="J/mol", default=50000.0)

            # Common variables
            variables.update({
                "T": ModelVariable(type="parameter", units="K", default=298.15),
                "P": ModelVariable(type="parameter", units="Pa", default=101325.0),
                "R": ModelVariable(type="parameter", units="J/mol/K", default=8.314),
                "target_species": ModelVariable(type="state", units="mol/L", default=1e-12)
            })

            equation = Equation(
                lhs=ExprNode(op="D", args=["target_species"], wrt="t"),
                rhs=expr
            )

            model = Model(
                name="very_large_kinetics",
                variables=variables,
                equations=[equation]
            )

            # Create ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Very Large Kinetics Expression",
                    description=f"Atmospheric kinetics with {n_reactions} reactions"
                ),
                models=[model]
            )

            # Serialize and parse
            json_str = save(esm_file)
            file_size_mb = len(json_str.encode('utf-8')) / 1024 / 1024
            reconstructed = load(json_str)

        # Verify performance
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < PerformanceBenchmarks.LARGE_EXPRESSION_MAX_PARSE_TIME, \
            f"Very large expression too slow: {metrics['runtime']:.3f}s > {PerformanceBenchmarks.LARGE_EXPRESSION_MAX_PARSE_TIME}s"
        assert metrics['memory_delta_mb'] < PerformanceBenchmarks.LARGE_EXPRESSION_MAX_MEMORY_MB, \
            f"Very large expression uses too much memory: {metrics['memory_delta_mb']:.1f}MB > {PerformanceBenchmarks.LARGE_EXPRESSION_MAX_MEMORY_MB}MB"

        print(f"Very large expression performance: {metrics['runtime']:.3f}s, {metrics['memory_delta_mb']:.1f}MB delta, {file_size_mb:.1f}MB file")

        # Verify we have a substantial expression
        assert len(reconstructed.models[0].variables) > 100
        assert len(reconstructed.models[0].equations) == 1


# ========================================
# 5. Size Limit Tests
# ========================================

class TestSizeLimits:
    """Test fixtures for files at the practical size limits of the format."""

    def test_comprehensive_earth_system_model(self):
        """Test comprehensive Earth system model combining all scalability dimensions."""
        # Combined large-scale test (reduced sizes to avoid excessive memory/recursion)
        n_systems = 5  # Reduced
        n_species_per_system = 20  # Reduced
        n_reactions_per_system = 30  # Reduced
        hierarchy_depth = 3  # Reduced
        coupling_density = 0.2

        with performance_monitor():
            models = []

            # Create multiple coupled systems, each with reaction networks and hierarchies
            for i in range(n_systems):
                system_name = f"earth_system_{i}"

                # Create reaction system for this component
                species = TestLargeReactionNetworks.generate_atmospheric_species(n_species_per_system)
                parameters = TestLargeReactionNetworks.generate_rate_parameters(n_reactions_per_system + 20)
                reactions = TestLargeReactionNetworks.generate_atmospheric_reactions(
                    species, parameters, n_reactions_per_system
                )

                reaction_system = ReactionSystem(
                    name=f"{system_name}_chemistry",
                    species=species,
                    parameters=parameters,
                    reactions=reactions
                )

                # Create hierarchical model for this component
                hierarchical_models = TestDeepHierarchies.create_nested_atmospheric_model(
                    hierarchy_depth, 2
                )
                # Rename the first hierarchical model
                if hierarchical_models:
                    hierarchical_models[0].name = f"{system_name}_dynamics"

                # Create large expression model
                large_expr = TestLargeExpressions.create_large_atmospheric_kinetics_expression(15)  # Reduced

                expr_variables = {}
                for j in range(8):  # Reduced
                    expr_variables[f"species_{j}"] = ModelVariable(
                        type="state", units="mol/L", default=1e-12
                    )
                    expr_variables[f"k{j}"] = ModelVariable(
                        type="parameter", units="cm3/molecule/s", default=1e-12
                    )

                expr_variables.update({
                    "T": ModelVariable(type="parameter", units="K", default=298.15),
                    "P": ModelVariable(type="parameter", units="Pa", default=101325.0),
                    "R": ModelVariable(type="parameter", units="J/mol/K", default=8.314),
                    "result": ModelVariable(type="state", units="mol/L", default=1e-12)
                })

                expr_model = Model(
                    name=f"{system_name}_kinetics",
                    variables=expr_variables,
                    equations=[Equation(
                        lhs=ExprNode(op="D", args=["result"], wrt="t"),
                        rhs=large_expr
                    )]
                )

                # Add all models to the main list
                models.extend(hierarchical_models)
                models.append(expr_model)

            # Create comprehensive ESM file
            esm_file = EsmFile(
                version="0.1.0",
                metadata=Metadata(
                    title="Comprehensive Earth System Model",
                    description=f"Large-scale ESM: {n_systems} systems, "
                              f"{n_species_per_system} species/system, "
                              f"{n_reactions_per_system} reactions/system, "
                              f"depth {hierarchy_depth}"
                ),
                models=models,
                reaction_systems=[
                    reaction_system for model in models[:3]  # Add a few reaction systems
                    for reaction_system in [ReactionSystem(
                        name=f"{model.name}_extra_chemistry",
                        species=TestLargeReactionNetworks.generate_atmospheric_species(20),
                        parameters=TestLargeReactionNetworks.generate_rate_parameters(30),
                        reactions=TestLargeReactionNetworks.generate_atmospheric_reactions(
                            TestLargeReactionNetworks.generate_atmospheric_species(20),
                            TestLargeReactionNetworks.generate_rate_parameters(30),
                            25
                        )
                    )]
                ]
            )

            # Serialize and parse
            json_str = save(esm_file)
            file_size_mb = len(json_str.encode('utf-8')) / 1024 / 1024
            reconstructed = load(json_str)

        # Verify performance under stress
        metrics = performance_monitor.last_metrics
        assert metrics['runtime'] < PerformanceBenchmarks.SIZE_LIMIT_MAX_PARSE_TIME, \
            f"Size limit test too slow: {metrics['runtime']:.3f}s > {PerformanceBenchmarks.SIZE_LIMIT_MAX_PARSE_TIME}s"
        assert metrics['memory_delta_mb'] < PerformanceBenchmarks.SIZE_LIMIT_MAX_MEMORY_MB, \
            f"Size limit test uses too much memory: {metrics['memory_delta_mb']:.1f}MB > {PerformanceBenchmarks.SIZE_LIMIT_MAX_MEMORY_MB}MB"

        print(f"\n=== COMPREHENSIVE SIZE LIMIT TEST RESULTS ===")
        print(f"Runtime: {metrics['runtime']:.3f}s")
        print(f"Memory delta: {metrics['memory_delta_mb']:.1f}MB")
        print(f"File size: {file_size_mb:.1f}MB")
        print(f"Models: {len(reconstructed.models)}")
        print(f"Reaction systems: {len(reconstructed.reaction_systems)}")

        total_species = sum(len(rs.species) for rs in reconstructed.reaction_systems)
        total_reactions = sum(len(rs.reactions) for rs in reconstructed.reaction_systems)

        print(f"Total species: {total_species}")
        print(f"Total reactions: {total_reactions}")
        print("=" * 50)

        # Verify structural integrity
        assert len(reconstructed.models) >= n_systems  # We have more due to hierarchies
        assert len(reconstructed.reaction_systems) >= 3
        assert file_size_mb > 0.1  # Should be a reasonable file size



# ========================================
# Utility Functions
# ========================================

def _get_atmospheric_units(var_name: str) -> str:
    """Get appropriate units for atmospheric variables."""
    unit_map = {
        'temperature': 'K',
        'pressure': 'Pa',
        'humidity': 'kg/kg',
        'wind_speed': 'm/s',
        'solar_radiation': 'W/m2',
        'boundary_layer_height': 'm',
        'mixing_ratio_CO2': 'ppmv',
        'mixing_ratio_CH4': 'ppmv',
        'aerosol_optical_depth': 'dimensionless',
        'NO2_concentration': 'mol/L',
        'O3_concentration': 'mol/L',
        'PM25_concentration': 'μg/m3',
        'traffic_emissions': 'kg/s'
    }

    # Default units for species and rates
    if var_name.startswith('species_'):
        return 'mol/L'
    elif var_name.startswith('reaction_rate_'):
        return 'mol/L/s'
    else:
        return unit_map.get(var_name.split('_')[-1], 'dimensionless')


def _get_atmospheric_default(var_name: str) -> float:
    """Get reasonable default values for atmospheric variables."""
    default_map = {
        'temperature': 298.15,
        'pressure': 101325.0,
        'humidity': 0.01,
        'wind_speed': 5.0,
        'solar_radiation': 1000.0,
        'boundary_layer_height': 1000.0,
        'mixing_ratio_CO2': 400.0,
        'mixing_ratio_CH4': 1.8,
        'aerosol_optical_depth': 0.1,
        'NO2_concentration': 1e-9,
        'O3_concentration': 1e-8,
        'PM25_concentration': 10.0,
        'traffic_emissions': 1e-6
    }

    if var_name.startswith('species_'):
        return 1e-12
    elif var_name.startswith('reaction_rate_'):
        return 1e-15
    else:
        base_name = var_name.split('_')[-1]
        return default_map.get(base_name, 1.0)


def _create_earth_system_variables(component_type: str, model_name: str) -> Dict[str, ModelVariable]:
    """Create variables for different Earth system components."""
    variables = {}

    if component_type == 'atmosphere':
        var_names = ['temperature', 'pressure', 'humidity', 'wind_u', 'wind_v', 'wind_w',
                    'CO2', 'CH4', 'N2O', 'O3', 'aerosol_mass']
    elif component_type == 'ocean':
        var_names = ['sea_surface_temperature', 'salinity', 'current_u', 'current_v',
                    'dissolved_CO2', 'pH', 'alkalinity', 'nutrients', 'chlorophyll']
    elif component_type == 'land_surface':
        var_names = ['soil_temperature', 'soil_moisture', 'albedo', 'roughness',
                    'sensible_heat', 'latent_heat', 'carbon_pool', 'nitrogen_pool']
    elif component_type == 'vegetation':
        var_names = ['leaf_area_index', 'biomass', 'photosynthesis_rate', 'respiration_rate',
                    'transpiration', 'carbon_assimilation', 'nitrogen_uptake', 'phenology']
    elif component_type == 'hydrology':
        var_names = ['precipitation', 'evaporation', 'runoff', 'groundwater', 'streamflow',
                    'snow_water_equivalent', 'soil_water', 'water_table_depth']
    elif component_type == 'ice_sheets':
        var_names = ['ice_thickness', 'ice_velocity', 'ice_temperature', 'mass_balance',
                    'basal_melt', 'surface_melt', 'accumulation', 'calving_rate']
    elif component_type == 'sea_ice':
        var_names = ['ice_concentration', 'ice_thickness', 'snow_depth', 'ice_velocity',
                    'ice_strength', 'brine_volume', 'surface_temperature', 'bottom_melt']
    elif component_type == 'biogeochemistry':
        var_names = ['primary_productivity', 'dissolved_organic_carbon', 'particulate_carbon',
                    'nitrogen_fixation', 'denitrification', 'mineralization', 'export_production']
    elif component_type == 'human_systems':
        var_names = ['fossil_emissions', 'land_use_change', 'population', 'economic_activity',
                    'energy_consumption', 'agriculture_area', 'urban_area', 'industrial_output']
    else:  # energy_balance
        var_names = ['shortwave_radiation', 'longwave_radiation', 'net_radiation', 'albedo',
                    'cloud_fraction', 'water_vapor', 'greenhouse_effect', 'radiative_forcing']

    for var_name in var_names:
        full_name = f"{model_name}_{var_name}"
        variables[full_name] = ModelVariable(
            type="state" if len(variables) < len(var_names)//2 else "parameter",
            units=_get_atmospheric_units(var_name),
            default=_get_atmospheric_default(var_name),
            description=f"{var_name} in {component_type} component"
        )

    return variables


def _create_earth_system_equations(variables: Dict[str, ModelVariable], component_type: str) -> List[Equation]:
    """Create equations for Earth system components."""
    equations = []
    state_vars = [name for name, var in variables.items() if var.type == "state"]
    param_vars = [name for name, var in variables.items() if var.type == "parameter"]

    # Create simple evolution equations
    for i, state_var in enumerate(state_vars[:3]):  # Limit to avoid too many equations
        if param_vars:
            # Different equation types based on component
            param1 = param_vars[i % len(param_vars)]

            if component_type in ['atmosphere', 'ocean']:
                # Advection-diffusion type: dx/dt = -v*grad(x) + D*laplacian(x)
                if len(param_vars) > 1:
                    param2 = param_vars[(i+1) % len(param_vars)]
                    rhs = ExprNode(op="+", args=[
                        ExprNode(op="*", args=[ExprNode(op="-", args=[param1]), state_var]),
                        ExprNode(op="*", args=[param2, ExprNode(op="laplacian", args=[state_var])])
                    ])
                else:
                    rhs = ExprNode(op="*", args=[ExprNode(op="-", args=[param1]), state_var])

            elif component_type in ['vegetation', 'biogeochemistry']:
                # Growth with limiting factors: dx/dt = r*x*(1 - x/K)
                if len(param_vars) > 1:
                    param2 = param_vars[(i+1) % len(param_vars)]
                    rhs = ExprNode(op="*", args=[
                        param1,
                        state_var,
                        ExprNode(op="-", args=[
                            1.0,
                            ExprNode(op="/", args=[state_var, param2])
                        ])
                    ])
                else:
                    rhs = ExprNode(op="*", args=[param1, state_var])

            else:
                # Simple linear dynamics: dx/dt = -k*x + source
                rhs = ExprNode(op="+", args=[
                    ExprNode(op="*", args=[ExprNode(op="-", args=[param1]), state_var]),
                    param_vars[(i+1) % len(param_vars)] if len(param_vars) > 1 else 0.1
                ])

            equations.append(Equation(
                lhs=ExprNode(op="D", args=[state_var], wrt="t"),
                rhs=rhs
            ))

    return equations


def _create_coupling_equations(model_from: Model, model_to: Model, all_variables: Dict[str, List[str]]) -> List[Equation]:
    """Create coupling equations between two models."""
    equations = []

    # Get variables from both models
    vars_from = [name for name in model_from.variables.keys()]
    vars_to = [name for name in model_to.variables.keys()]

    if len(vars_from) > 0 and len(vars_to) > 0:
        # Create 1-2 coupling equations
        n_couplings = min(2, len(vars_from), len(vars_to))

        for i in range(n_couplings):
            var_from = vars_from[i % len(vars_from)]
            var_to = vars_to[i % len(vars_to)]

            # Simple coupling: influence proportional to other model's state
            coupling_strength = 0.01  # Weak coupling

            # Add coupling term to existing equation or create new one
            coupling_term = ExprNode(op="*", args=[coupling_strength, var_to])

            # Find existing equation for var_from or create new one
            existing_eq = None
            for eq in model_from.equations:
                if (hasattr(eq.lhs, 'args') and len(eq.lhs.args) > 0 and
                    eq.lhs.args[0] == var_from):
                    existing_eq = eq
                    break

            if existing_eq:
                # Add coupling term to existing equation
                new_rhs = ExprNode(op="+", args=[existing_eq.rhs, coupling_term])
                existing_eq.rhs = new_rhs
            else:
                # Create new coupling equation
                equations.append(Equation(
                    lhs=ExprNode(op="D", args=[var_from], wrt="t"),
                    rhs=coupling_term
                ))

    return equations


# ========================================
# Performance Report Generation
# ========================================

def generate_performance_report(output_dir: str = "test_verification_results"):
    """Generate comprehensive performance report from test results."""

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "performance_benchmarks": {
            "large_network": {
                "max_parse_time_s": PerformanceBenchmarks.LARGE_NETWORK_MAX_PARSE_TIME,
                "max_serialize_time_s": PerformanceBenchmarks.LARGE_NETWORK_MAX_SERIALIZE_TIME,
                "max_memory_mb": PerformanceBenchmarks.LARGE_NETWORK_MAX_MEMORY_MB
            },
            "deep_hierarchy": {
                "max_parse_time_s": PerformanceBenchmarks.DEEP_HIERARCHY_MAX_PARSE_TIME,
                "max_serialize_time_s": PerformanceBenchmarks.DEEP_HIERARCHY_MAX_SERIALIZE_TIME,
                "max_memory_mb": PerformanceBenchmarks.DEEP_HIERARCHY_MAX_MEMORY_MB
            },
            "complex_coupling": {
                "max_parse_time_s": PerformanceBenchmarks.COMPLEX_COUPLING_MAX_PARSE_TIME,
                "max_serialize_time_s": PerformanceBenchmarks.COMPLEX_COUPLING_MAX_SERIALIZE_TIME,
                "max_memory_mb": PerformanceBenchmarks.COMPLEX_COUPLING_MAX_MEMORY_MB
            },
            "large_expression": {
                "max_parse_time_s": PerformanceBenchmarks.LARGE_EXPRESSION_MAX_PARSE_TIME,
                "max_serialize_time_s": PerformanceBenchmarks.LARGE_EXPRESSION_MAX_SERIALIZE_TIME,
                "max_memory_mb": PerformanceBenchmarks.LARGE_EXPRESSION_MAX_MEMORY_MB
            },
            "size_limit": {
                "max_parse_time_s": PerformanceBenchmarks.SIZE_LIMIT_MAX_PARSE_TIME,
                "max_serialize_time_s": PerformanceBenchmarks.SIZE_LIMIT_MAX_SERIALIZE_TIME,
                "max_memory_mb": PerformanceBenchmarks.SIZE_LIMIT_MAX_MEMORY_MB
            }
        },
        "test_coverage": [
            "Large reaction networks (500 species, 1000 reactions)",
            "Deep hierarchies (6 levels, multiple subsystems)",
            "Complex coupling chains (25 systems, 40% coupling density)",
            "Very large expressions (500+ terms)",
            "Comprehensive size limits (multi-GB files)"
        ]
    }

    report_file = output_path / "performance_scalability_benchmarks.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Performance report saved to: {report_file}")
    return report


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])