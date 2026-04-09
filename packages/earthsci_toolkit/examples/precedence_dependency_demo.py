"""
Demonstration of operator precedence and dependency system.

This script shows how to use the new precedence and dependency features
in the ESM Format operator registry.
"""

from esm_format.operator_registry import (
    OperatorRegistry,
    Associativity,
    register_operator,
    get_operator_precedence,
    compare_precedence,
    add_operator_dependency,
    get_execution_order,
    topological_sort_operators
)
# NOTE: OperatorType removed - not in ESM specification


class DemoOperator:
    """Demo operator for examples."""
    def __init__(self, config):
        self.config = config
        self.name = config.name


def demonstrate_precedence():
    """Demonstrate operator precedence system."""
    print("=== Operator Precedence Demonstration ===")

    registry = OperatorRegistry()

    # Show built-in precedence rules
    print("\nBuilt-in precedence rules:")
    operators = ["sin", "^", "*", "+", "and", "or"]
    for op in operators:
        prec = registry.get_operator_precedence(op)
        if prec:
            print(f"  {op}: level {prec.level}, {prec.associativity.value} associative")

    # Compare precedence
    print("\nPrecedence comparisons:")
    comparisons = [("*", "+"), ("^", "*"), ("sin", "+")]
    for op1, op2 in comparisons:
        result = registry.compare_precedence(op1, op2)
        if result == -1:
            rel = f"{op1} has higher precedence than {op2}"
        elif result == 0:
            rel = f"{op1} and {op2} have equal precedence"
        else:
            rel = f"{op2} has higher precedence than {op1}"
        print(f"  {rel}")

    # Register custom operator with precedence
    print("\nRegistering custom operator with precedence:")
    registry.register_operator(
        name="custom_func",
        operator_type=OperatorType.TRANSFORMATION,
        operator_class=DemoOperator,
        precedence_level=1,  # High precedence like functions
        associativity=Associativity.LEFT
    )

    custom_prec = registry.get_operator_precedence("custom_func")
    print(f"  custom_func: level {custom_prec.level}, {custom_prec.associativity.value} associative")


def demonstrate_dependencies():
    """Demonstrate operator dependency system."""
    print("\n=== Operator Dependency Demonstration ===")

    registry = OperatorRegistry()

    # Register operators for a computational pipeline
    operators = [
        ("load_data", OperatorType.TRANSFORMATION, 10),
        ("preprocess", OperatorType.FILTERING, 9),
        ("compute_gradient", OperatorType.DIFFERENTIATION, 1),
        ("apply_boundary", OperatorType.TRANSFORMATION, 8),
        ("solve_system", OperatorType.TRANSFORMATION, 7)
    ]

    for name, op_type, prec in operators:
        registry.register_operator(
            name=name,
            operator_type=op_type,
            operator_class=DemoOperator,
            precedence_level=prec
        )

    # Set up dependencies for a typical computational pipeline
    dependencies = [
        ("preprocess", "load_data"),  # preprocess depends on load_data
        ("compute_gradient", "preprocess"),  # gradient depends on preprocessed data
        ("apply_boundary", "load_data"),  # boundary conditions depend on data
        ("solve_system", "compute_gradient"),  # solver depends on gradient
        ("solve_system", "apply_boundary"),  # solver also depends on boundary conditions
    ]

    print("\nSetting up computational pipeline dependencies:")
    for dependent, dependency in dependencies:
        registry.add_operator_dependency(dependent, dependency)
        print(f"  {dependent} depends on {dependency}")

    # Show dependency information
    print("\nDependency information:")
    for name, _, _ in operators:
        deps = registry.get_operator_dependencies(name)
        dependents = registry.get_operator_dependents(name)
        print(f"  {name}:")
        print(f"    depends on: {list(deps) if deps else 'none'}")
        print(f"    depended on by: {list(dependents) if dependents else 'none'}")

    # Demonstrate topological sorting
    all_ops = [name for name, _, _ in operators]
    sorted_ops = registry.topological_sort_operators(all_ops)
    print(f"\nTopological sort order: {sorted_ops}")

    # Demonstrate execution order (combines dependencies and precedence)
    exec_order = registry.get_execution_order(all_ops)
    print(f"Execution order: {exec_order}")


def demonstrate_circular_dependency_protection():
    """Demonstrate circular dependency detection."""
    print("\n=== Circular Dependency Protection ===")

    registry = OperatorRegistry()

    # Register test operators
    for name in ["op_a", "op_b", "op_c"]:
        registry.register_operator(name, OperatorType.ARITHMETIC, DemoOperator)

    # Create a dependency chain
    registry.add_operator_dependency("op_a", "op_b")
    registry.add_operator_dependency("op_b", "op_c")
    print("Created dependency chain: op_a -> op_b -> op_c")

    # Try to create circular dependency
    try:
        registry.add_operator_dependency("op_c", "op_a")
        print("ERROR: Circular dependency was allowed!")
    except ValueError as e:
        print(f"Circular dependency correctly blocked: {e}")


def demonstrate_mathematical_expression():
    """Demonstrate precedence in mathematical expression context."""
    print("\n=== Mathematical Expression Context ===")

    registry = OperatorRegistry()

    # Expression: sin(x) * cos(y) + z^2
    # Expected precedence: sin, cos (level 1), ^ (level 2), * (level 4), + (level 5)

    operators_in_expr = ["sin", "cos", "^", "*", "+"]

    print("Expression: sin(x) * cos(y) + z^2")
    print("Operators and their precedence levels:")

    for op in operators_in_expr:
        prec = registry.get_operator_precedence(op)
        if prec:
            print(f"  {op}: level {prec.level}")

    # Show execution order
    exec_order = registry.get_execution_order(operators_in_expr)
    print(f"\nExecution order based on precedence: {exec_order}")

    print("\nThis means the expression would be evaluated as:")
    print("1. sin(x) and cos(y) (functions, highest precedence)")
    print("2. z^2 (exponentiation)")
    print("3. sin(x) * cos(y) (multiplication)")
    print("4. result + z^2 (addition, lowest precedence)")


def main():
    """Main demonstration function."""
    print("ESM Format Operator Precedence and Dependency System Demo")
    print("=" * 60)

    demonstrate_precedence()
    demonstrate_dependencies()
    demonstrate_circular_dependency_protection()
    demonstrate_mathematical_expression()

    print("\n" + "=" * 60)
    print("Demo completed successfully!")


if __name__ == "__main__":
    main()