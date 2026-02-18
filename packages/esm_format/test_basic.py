#!/usr/bin/env python3
"""Basic test script to validate the package works."""

import sys
import traceback

# Add src to path
sys.path.insert(0, 'src')

def run_tests():
    """Run basic tests to validate the package."""
    tests_passed = 0
    tests_failed = 0

    def test(name, func):
        nonlocal tests_passed, tests_failed
        try:
            func()
            print(f"✓ {name}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ {name}: {e}")
            traceback.print_exc()
            tests_failed += 1

    # Test imports
    def test_imports():
        from esm_format.types import (
            ExprNode, Expr, Equation, AffectEquation, ModelVariable, Model,
            Species, Parameter, Reaction, ReactionSystem,
            ContinuousEvent, DiscreteEvent, FunctionalAffect, DiscreteEventTrigger,
            DataLoader, DataLoaderType, Operator,
            CouplingEntry, CouplingType, Domain, Solver, SolverType,
            Reference, Metadata, EsmFile
        )

        # Test basic imports from __init__.py
        from esm_format import ExprNode, Model, EsmFile

    def test_expr_node():
        from esm_format.types import ExprNode
        node = ExprNode(op="+", args=[1, 2])
        assert node.op == "+"
        assert node.args == [1, 2]
        assert node.wrt is None
        assert node.dim is None

    def test_model_variable():
        from esm_format.types import ModelVariable
        var = ModelVariable(
            type="state",
            units="kg/m^3",
            default=0.0,
            description="Concentration"
        )
        assert var.type == "state"
        assert var.units == "kg/m^3"
        assert var.default == 0.0

    def test_model():
        from esm_format.types import Model
        model = Model(name="TestModel")
        assert model.name == "TestModel"
        assert len(model.variables) == 0
        assert len(model.equations) == 0

    def test_species():
        from esm_format.types import Species
        species = Species(name="CO2", formula="CO2", units="gram/mole", default=44.01)
        assert species.name == "CO2"
        assert species.formula == "CO2"
        assert species.units == "gram/mole"
        assert species.default == 44.01

    def test_esm_file():
        from esm_format.types import EsmFile, Metadata
        metadata = Metadata(title="Test Model", version="1.0")
        esm_file = EsmFile(version="1.0", metadata=metadata)
        assert esm_file.version == "1.0"
        assert esm_file.metadata.title == "Test Model"

    def test_complex_expression():
        from esm_format.types import ExprNode
        # Create expression: (x + y) * 2
        add_expr = ExprNode(op="+", args=["x", "y"])
        mult_expr = ExprNode(op="*", args=[add_expr, 2])

        assert mult_expr.op == "*"
        assert len(mult_expr.args) == 2
        assert mult_expr.args[1] == 2
        assert isinstance(mult_expr.args[0], ExprNode)
        assert mult_expr.args[0].op == "+"

    # Run all tests
    test("Package imports", test_imports)
    test("ExprNode creation", test_expr_node)
    test("ModelVariable creation", test_model_variable)
    test("Model creation", test_model)
    test("Species creation", test_species)
    test("EsmFile creation", test_esm_file)
    test("Complex expression", test_complex_expression)

    print(f"\n{tests_passed} tests passed, {tests_failed} tests failed")
    return tests_failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)