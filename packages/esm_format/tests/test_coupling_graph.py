"""Tests for coupling graph construction and analysis."""

import pytest
from esm_format.coupling_graph import (
    CouplingGraph, CouplingNode, CouplingEdge, NodeType, DependencyInfo,
    construct_coupling_graph, validate_coupling_graph, _resolve_component_id
)
from esm_format.types import (
    EsmFile, Model, ReactionSystem, CouplingEntry, CouplingType,
    Metadata, ModelVariable, Species, Parameter, Reaction
)


class TestCouplingNode:
    """Tests for CouplingNode class."""

    def test_coupling_node_creation(self):
        """Test creating a coupling node."""
        node = CouplingNode(
            id="test_model",
            name="TestModel",
            type=NodeType.MODEL,
            variables=["temp", "pressure"],
            metadata={"description": "test model"}
        )

        assert node.id == "test_model"
        assert node.name == "TestModel"
        assert node.type == NodeType.MODEL
        assert node.variables == ["temp", "pressure"]
        assert node.metadata["description"] == "test model"


class TestCouplingEdge:
    """Tests for CouplingEdge class."""

    def test_coupling_edge_creation(self):
        """Test creating a coupling edge."""
        edge = CouplingEdge(
            source_node="model1",
            target_node="model2",
            source_variables=["temp"],
            target_variables=["temperature"],
            coupling_type=CouplingType.DIRECT
        )

        assert edge.source_node == "model1"
        assert edge.target_node == "model2"
        assert edge.source_variables == ["temp"]
        assert edge.target_variables == ["temperature"]
        assert edge.coupling_type == CouplingType.DIRECT


class TestCouplingGraph:
    """Tests for CouplingGraph class."""

    def test_empty_graph(self):
        """Test creating an empty coupling graph."""
        graph = CouplingGraph()
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_add_node(self):
        """Test adding nodes to the graph."""
        graph = CouplingGraph()
        node = CouplingNode(
            id="test_node",
            name="TestNode",
            type=NodeType.MODEL,
            variables=["var1", "var2"]
        )

        graph.add_node(node)
        assert len(graph.nodes) == 1
        assert "test_node" in graph.nodes
        assert graph.nodes["test_node"] == node

    def test_add_duplicate_node_error(self):
        """Test that adding a node with duplicate ID raises error."""
        graph = CouplingGraph()
        node1 = CouplingNode(id="test", name="Test1", type=NodeType.MODEL)
        node2 = CouplingNode(id="test", name="Test2", type=NodeType.MODEL)

        graph.add_node(node1)
        with pytest.raises(ValueError, match="Node with ID 'test' already exists"):
            graph.add_node(node2)

    def test_add_edge(self):
        """Test adding edges to the graph."""
        graph = CouplingGraph()

        # Add nodes first
        node1 = CouplingNode(id="node1", name="Node1", type=NodeType.MODEL, variables=["var1"])
        node2 = CouplingNode(id="node2", name="Node2", type=NodeType.MODEL, variables=["var2"])
        graph.add_node(node1)
        graph.add_node(node2)

        # Add edge
        edge = CouplingEdge(
            source_node="node1",
            target_node="node2",
            source_variables=["var1"],
            target_variables=["var2"],
            coupling_type=CouplingType.DIRECT
        )
        graph.add_edge(edge)

        assert len(graph.edges) == 1
        assert graph.edges[0] == edge

    def test_add_edge_missing_nodes_error(self):
        """Test that adding edge with missing nodes raises error."""
        graph = CouplingGraph()
        edge = CouplingEdge(
            source_node="missing",
            target_node="also_missing",
            source_variables=["var1"],
            target_variables=["var2"],
            coupling_type=CouplingType.DIRECT
        )

        with pytest.raises(ValueError, match="Source node 'missing' not found"):
            graph.add_edge(edge)

    def test_get_neighbors(self):
        """Test getting neighbor nodes."""
        graph = CouplingGraph()

        # Create simple chain: node1 -> node2 -> node3
        for i in range(1, 4):
            node = CouplingNode(id=f"node{i}", name=f"Node{i}", type=NodeType.MODEL, variables=[f"var{i}"])
            graph.add_node(node)

        edge1 = CouplingEdge("node1", "node2", ["var1"], ["var2"], CouplingType.DIRECT)
        edge2 = CouplingEdge("node2", "node3", ["var2"], ["var3"], CouplingType.DIRECT)
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        assert graph.get_neighbors("node1") == {"node2"}
        assert graph.get_neighbors("node2") == {"node3"}
        assert graph.get_neighbors("node3") == set()

    def test_get_predecessors(self):
        """Test getting predecessor nodes."""
        graph = CouplingGraph()

        # Create simple chain: node1 -> node2 -> node3
        for i in range(1, 4):
            node = CouplingNode(id=f"node{i}", name=f"Node{i}", type=NodeType.MODEL, variables=[f"var{i}"])
            graph.add_node(node)

        edge1 = CouplingEdge("node1", "node2", ["var1"], ["var2"], CouplingType.DIRECT)
        edge2 = CouplingEdge("node2", "node3", ["var2"], ["var3"], CouplingType.DIRECT)
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        assert graph.get_predecessors("node1") == set()
        assert graph.get_predecessors("node2") == {"node1"}
        assert graph.get_predecessors("node3") == {"node2"}

    def test_detect_cycles_no_cycles(self):
        """Test cycle detection on acyclic graph."""
        graph = CouplingGraph()

        # Create chain: node1 -> node2 -> node3
        for i in range(1, 4):
            node = CouplingNode(id=f"node{i}", name=f"Node{i}", type=NodeType.MODEL, variables=[f"var{i}"])
            graph.add_node(node)

        edge1 = CouplingEdge("node1", "node2", ["var1"], ["var2"], CouplingType.DIRECT)
        edge2 = CouplingEdge("node2", "node3", ["var2"], ["var3"], CouplingType.DIRECT)
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        cycles = graph.detect_cycles()
        assert len(cycles) == 0

    def test_detect_cycles_simple_cycle(self):
        """Test cycle detection with a simple cycle."""
        graph = CouplingGraph()

        # Create cycle: node1 -> node2 -> node1
        for i in range(1, 3):
            node = CouplingNode(id=f"node{i}", name=f"Node{i}", type=NodeType.MODEL, variables=[f"var{i}"])
            graph.add_node(node)

        edge1 = CouplingEdge("node1", "node2", ["var1"], ["var2"], CouplingType.DIRECT)
        edge2 = CouplingEdge("node2", "node1", ["var2"], ["var1"], CouplingType.FEEDBACK)
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        cycles = graph.detect_cycles()
        assert len(cycles) == 1
        assert set(cycles[0]) == {"node1", "node2"}

    def test_analyze_dependencies(self):
        """Test dependency analysis."""
        graph = CouplingGraph()

        # Create chain: node1 -> node2 -> node3
        for i in range(1, 4):
            node = CouplingNode(id=f"node{i}", name=f"Node{i}", type=NodeType.MODEL, variables=[f"var{i}"])
            graph.add_node(node)

        edge1 = CouplingEdge("node1", "node2", ["var1"], ["var2"], CouplingType.DIRECT)
        edge2 = CouplingEdge("node2", "node3", ["var2"], ["var3"], CouplingType.DIRECT)
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        graph.analyze_dependencies()

        # Check node1 dependencies
        info1 = graph.get_dependency_info("node1")
        assert len(info1.direct_dependencies) == 0
        assert len(info1.indirect_dependencies) == 0
        assert info1.dependents == {"node2"}
        assert info1.dependency_level == 0

        # Check node2 dependencies
        info2 = graph.get_dependency_info("node2")
        assert info2.direct_dependencies == {"node1"}
        assert info2.indirect_dependencies == {"node1"}
        assert info2.dependents == {"node3"}
        assert info2.dependency_level == 1

        # Check node3 dependencies
        info3 = graph.get_dependency_info("node3")
        assert info3.direct_dependencies == {"node2"}
        assert info3.indirect_dependencies == {"node1", "node2"}
        assert len(info3.dependents) == 0
        assert info3.dependency_level == 2

    def test_get_execution_order(self):
        """Test getting execution order."""
        graph = CouplingGraph()

        # Create diamond dependency: node1 -> {node2, node3} -> node4
        for i in range(1, 5):
            node = CouplingNode(id=f"node{i}", name=f"Node{i}", type=NodeType.MODEL, variables=[f"var{i}"])
            graph.add_node(node)

        edges = [
            CouplingEdge("node1", "node2", ["var1"], ["var2"], CouplingType.DIRECT),
            CouplingEdge("node1", "node3", ["var1"], ["var3"], CouplingType.DIRECT),
            CouplingEdge("node2", "node4", ["var2"], ["var4"], CouplingType.DIRECT),
            CouplingEdge("node3", "node4", ["var3"], ["var4"], CouplingType.DIRECT)
        ]
        for edge in edges:
            graph.add_edge(edge)

        execution_order = graph.get_execution_order()

        # node1 should be first
        assert execution_order[0] == "node1"
        # node2 and node3 should be after node1 but before node4
        assert execution_order.index("node2") > execution_order.index("node1")
        assert execution_order.index("node3") > execution_order.index("node1")
        # node4 should be last
        assert execution_order[-1] == "node4"

    def test_get_execution_order_with_cycle_error(self):
        """Test that execution order raises error when cycles exist."""
        graph = CouplingGraph()

        # Create cycle
        for i in range(1, 3):
            node = CouplingNode(id=f"node{i}", name=f"Node{i}", type=NodeType.MODEL, variables=[f"var{i}"])
            graph.add_node(node)

        edge1 = CouplingEdge("node1", "node2", ["var1"], ["var2"], CouplingType.DIRECT)
        edge2 = CouplingEdge("node2", "node1", ["var2"], ["var1"], CouplingType.FEEDBACK)
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        with pytest.raises(ValueError, match="Circular dependencies detected"):
            graph.get_execution_order()

    def test_get_statistics(self):
        """Test getting graph statistics."""
        graph = CouplingGraph()

        # Create mixed graph with models and reaction systems
        model_node = CouplingNode(id="model1", name="Model1", type=NodeType.MODEL, variables=["temp"])
        reaction_node = CouplingNode(id="rxn1", name="Rxn1", type=NodeType.REACTION_SYSTEM, variables=["O3"])
        variable_node = CouplingNode(id="var1", name="Var1", type=NodeType.VARIABLE)

        graph.add_node(model_node)
        graph.add_node(reaction_node)
        graph.add_node(variable_node)

        edge1 = CouplingEdge("model1", "rxn1", ["temp"], ["O3"], CouplingType.DIRECT)
        edge2 = CouplingEdge("rxn1", "var1", ["O3"], [], CouplingType.INTERPOLATED)
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        graph.analyze_dependencies()
        stats = graph.get_statistics()

        assert stats['total_nodes'] == 3
        assert stats['total_edges'] == 2
        assert stats['model_nodes'] == 1
        assert stats['reaction_system_nodes'] == 1
        assert stats['variable_nodes'] == 1
        assert stats['direct_couplings'] == 1
        assert stats['interpolated_couplings'] == 1
        assert stats['cycles_detected'] == 0
        assert stats['max_dependency_level'] == 2


class TestConstructCouplingGraph:
    """Tests for construct_coupling_graph function."""

    def test_construct_simple_graph(self):
        """Test constructing a simple coupling graph from ESM file."""
        # Create simple ESM file with two models and one coupling
        metadata = Metadata(title="Test ESM")

        model1 = Model(
            name="AtmosphericModel",
            variables={"temperature": ModelVariable(type="state", units="K")},
            equations=[],
            metadata={}
        )

        model2 = Model(
            name="OceanModel",
            variables={"sea_surface_temp": ModelVariable(type="state", units="K")},
            equations=[],
            metadata={}
        )

        coupling = CouplingEntry(
            source_model="AtmosphericModel",
            target_model="OceanModel",
            source_variables=["temperature"],
            target_variables=["sea_surface_temp"],
            coupling_type=CouplingType.DIRECT
        )

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models=[model1, model2],
            couplings=[coupling]
        )

        graph = construct_coupling_graph(esm_file)

        # Check nodes
        assert len(graph.nodes) == 2
        assert "model:AtmosphericModel" in graph.nodes
        assert "model:OceanModel" in graph.nodes

        # Check edges
        assert len(graph.edges) == 1
        edge = graph.edges[0]
        assert edge.source_node == "model:AtmosphericModel"
        assert edge.target_node == "model:OceanModel"
        assert edge.source_variables == ["temperature"]
        assert edge.target_variables == ["sea_surface_temp"]

    def test_construct_graph_with_reaction_systems(self):
        """Test constructing graph with reaction systems."""
        metadata = Metadata(title="Test ESM")

        species = [Species(name="O3"), Species(name="NO2")]
        reaction_system = ReactionSystem(
            name="Chemistry",
            species=species,
            parameters=[],
            reactions=[]
        )

        model = Model(
            name="AtmosphericModel",
            variables={"O3_conc": ModelVariable(type="state", units="ppb")},
            equations=[],
            metadata={}
        )

        coupling = CouplingEntry(
            source_model="Chemistry",
            target_model="AtmosphericModel",
            source_variables=["O3"],
            target_variables=["O3_conc"],
            coupling_type=CouplingType.DIRECT
        )

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models=[model],
            reaction_systems=[reaction_system],
            couplings=[coupling]
        )

        graph = construct_coupling_graph(esm_file)

        # Check nodes
        assert len(graph.nodes) == 2
        assert "reaction_system:Chemistry" in graph.nodes
        assert "model:AtmosphericModel" in graph.nodes

        # Check reaction system node details
        chem_node = graph.nodes["reaction_system:Chemistry"]
        assert chem_node.type == NodeType.REACTION_SYSTEM
        assert "O3" in chem_node.variables
        assert "NO2" in chem_node.variables

    def test_construct_graph_invalid_coupling_error(self):
        """Test that invalid couplings raise errors."""
        metadata = Metadata(title="Test ESM")

        model = Model(
            name="TestModel",
            variables={"temp": ModelVariable(type="state", units="K")},
            equations=[],
            metadata={}
        )

        # Coupling references non-existent source model
        coupling = CouplingEntry(
            source_model="NonExistentModel",
            target_model="TestModel",
            source_variables=["temp"],
            target_variables=["temp"],
            coupling_type=CouplingType.DIRECT
        )

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models=[model],
            couplings=[coupling]
        )

        with pytest.raises(ValueError, match="Component 'NonExistentModel' not found in ESM file"):
            construct_coupling_graph(esm_file)

    def test_construct_graph_invalid_variable_error(self):
        """Test that coupling with invalid variables raises errors."""
        metadata = Metadata(title="Test ESM")

        model1 = Model(
            name="Model1",
            variables={"temp": ModelVariable(type="state", units="K")},
            equations=[],
            metadata={}
        )

        model2 = Model(
            name="Model2",
            variables={"pressure": ModelVariable(type="state", units="Pa")},
            equations=[],
            metadata={}
        )

        # Coupling references non-existent variable
        coupling = CouplingEntry(
            source_model="Model1",
            target_model="Model2",
            source_variables=["non_existent_var"],
            target_variables=["pressure"],
            coupling_type=CouplingType.DIRECT
        )

        esm_file = EsmFile(
            version="0.1.0",
            metadata=metadata,
            models=[model1, model2],
            couplings=[coupling]
        )

        with pytest.raises(ValueError, match="Source variable 'non_existent_var' not found"):
            construct_coupling_graph(esm_file)


class TestResolveComponentId:
    """Tests for _resolve_component_id function."""

    def test_resolve_model_id(self):
        """Test resolving model component ID."""
        metadata = Metadata(title="Test")
        model = Model(name="TestModel", variables={}, equations=[])
        esm_file = EsmFile(version="0.1.0", metadata=metadata, models=[model])

        result = _resolve_component_id("TestModel", esm_file)
        assert result == "model:TestModel"

    def test_resolve_reaction_system_id(self):
        """Test resolving reaction system component ID."""
        metadata = Metadata(title="Test")
        reaction_system = ReactionSystem(name="TestChemistry", species=[], parameters=[], reactions=[])
        esm_file = EsmFile(version="0.1.0", metadata=metadata, reaction_systems=[reaction_system])

        result = _resolve_component_id("TestChemistry", esm_file)
        assert result == "reaction_system:TestChemistry"

    def test_resolve_nonexistent_component_error(self):
        """Test that resolving non-existent component raises error."""
        metadata = Metadata(title="Test")
        esm_file = EsmFile(version="0.1.0", metadata=metadata)

        with pytest.raises(ValueError, match="Component 'NonExistent' not found"):
            _resolve_component_id("NonExistent", esm_file)


class TestValidateCouplingGraph:
    """Tests for validate_coupling_graph function."""

    def test_validate_valid_graph(self):
        """Test validating a valid graph."""
        graph = CouplingGraph()

        # Create valid graph
        node1 = CouplingNode(id="node1", name="Node1", type=NodeType.MODEL, variables=["var1"])
        node2 = CouplingNode(id="node2", name="Node2", type=NodeType.MODEL, variables=["var2"])
        graph.add_node(node1)
        graph.add_node(node2)

        edge = CouplingEdge("node1", "node2", ["var1"], ["var2"], CouplingType.DIRECT)
        graph.add_edge(edge)

        is_valid, errors = validate_coupling_graph(graph)
        assert is_valid
        assert len(errors) == 0

    def test_validate_graph_with_cycle(self):
        """Test validating graph with cycles."""
        graph = CouplingGraph()

        # Create cycle
        for i in range(1, 3):
            node = CouplingNode(id=f"node{i}", name=f"Node{i}", type=NodeType.MODEL, variables=[f"var{i}"])
            graph.add_node(node)

        edge1 = CouplingEdge("node1", "node2", ["var1"], ["var2"], CouplingType.DIRECT)
        edge2 = CouplingEdge("node2", "node1", ["var2"], ["var1"], CouplingType.FEEDBACK)
        graph.add_edge(edge1)
        graph.add_edge(edge2)

        is_valid, errors = validate_coupling_graph(graph)
        assert not is_valid
        assert len(errors) >= 1
        assert "Circular dependency detected" in errors[0]

    def test_validate_graph_with_orphaned_nodes(self):
        """Test validating graph with orphaned nodes."""
        graph = CouplingGraph()

        # Create connected nodes and one orphaned
        node1 = CouplingNode(id="node1", name="Node1", type=NodeType.MODEL, variables=["var1"])
        node2 = CouplingNode(id="node2", name="Node2", type=NodeType.MODEL, variables=["var2"])
        orphan = CouplingNode(id="orphan", name="Orphan", type=NodeType.MODEL, variables=["var3"])

        graph.add_node(node1)
        graph.add_node(node2)
        graph.add_node(orphan)

        edge = CouplingEdge("node1", "node2", ["var1"], ["var2"], CouplingType.DIRECT)
        graph.add_edge(edge)

        is_valid, errors = validate_coupling_graph(graph)
        assert not is_valid
        assert any("Orphaned node" in error for error in errors)

    def test_validate_graph_variable_mismatch(self):
        """Test validating graph with variable count mismatches."""
        graph = CouplingGraph()

        node1 = CouplingNode(id="node1", name="Node1", type=NodeType.MODEL, variables=["var1", "var2"])
        node2 = CouplingNode(id="node2", name="Node2", type=NodeType.MODEL, variables=["var3"])
        graph.add_node(node1)
        graph.add_node(node2)

        # Edge with mismatched variable counts
        edge = CouplingEdge("node1", "node2", ["var1", "var2"], ["var3"], CouplingType.DIRECT)
        graph.add_edge(edge)

        is_valid, errors = validate_coupling_graph(graph)
        assert not is_valid
        assert any("Variable count mismatch" in error for error in errors)