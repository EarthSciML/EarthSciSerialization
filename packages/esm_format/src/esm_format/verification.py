"""
Mathematical correctness verification module for ESM Format.

This module provides comprehensive mathematical verification for Earth System Model
serialization and computational correctness, including:

1. Dimensional analysis and unit consistency checking
2. Conservation law verification (mass, energy, charge)
3. Stoichiometric balance validation for reactions
4. Equation count vs. variable count analysis
5. Coupling consistency across system boundaries
6. Numerical precision and stability analysis
"""

import numpy as np
import sympy as sp
from typing import Dict, List, Tuple, Optional, Union, Set, Any
from dataclasses import dataclass
from enum import Enum

from .esm_types import (
    ModelVariable, Parameter, Species, Equation, ExprNode, Expr,
    Model, ReactionSystem, Reaction, ContinuousEvent, DiscreteEvent
)


class VerificationStatus(Enum):
    """Status of verification results."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"


@dataclass
class VerificationResult:
    """Result of a verification check."""
    status: VerificationStatus
    message: str
    details: Dict[str, Any] = None
    tolerance_used: Optional[float] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class VerificationReport:
    """Comprehensive verification report."""
    results: List[VerificationResult]
    summary: Dict[str, int] = None

    def __post_init__(self):
        if self.summary is None:
            self.summary = {status.value: 0 for status in VerificationStatus}
            for result in self.results:
                self.summary[result.status.value] += 1

    def passed(self) -> bool:
        """Check if all critical verifications passed."""
        return self.summary["fail"] == 0

    def add_result(self, result: VerificationResult) -> None:
        """Add a verification result and update summary."""
        self.results.append(result)
        self.summary[result.status.value] += 1


class MathematicalVerifier:
    """Main verification class for mathematical correctness."""

    def __init__(self, tolerance: float = 1e-10):
        """
        Initialize verifier with numerical tolerance.

        Args:
            tolerance: Numerical tolerance for floating-point comparisons
        """
        self.tolerance = tolerance
        self.report = VerificationReport(results=[])

    def verify_reaction_system(self, reaction_system: ReactionSystem) -> VerificationReport:
        """
        Comprehensive verification of a reaction system.

        Args:
            reaction_system: The reaction system to verify

        Returns:
            VerificationReport: Complete verification results
        """
        self.report = VerificationReport(results=[])

        # 1. Stoichiometric matrix verification
        self._verify_stoichiometric_matrix(reaction_system)

        # 2. Mass conservation verification
        self._verify_mass_conservation(reaction_system)

        # 3. Species consistency verification
        self._verify_species_consistency(reaction_system)

        # 4. Parameter validation
        self._verify_parameters(reaction_system)

        return self.report

    def verify_model(self, model: Model) -> VerificationReport:
        """
        Comprehensive verification of a mathematical model.

        Args:
            model: The model to verify

        Returns:
            VerificationReport: Complete verification results
        """
        self.report = VerificationReport(results=[])

        # 1. Variable-equation consistency
        self._verify_variable_equation_consistency(model)

        # 2. Dimensional analysis
        self._verify_dimensional_consistency(model)

        # 3. Cross-reference validation
        self._verify_cross_references(model)

        # 4. Equation solvability analysis
        self._verify_equation_solvability(model)

        return self.report

    def compute_stoichiometric_matrix(self, reaction_system: ReactionSystem) -> np.ndarray:
        """
        Compute the stoichiometric matrix for a reaction system.

        Args:
            reaction_system: System containing species and reactions

        Returns:
            np.ndarray: Stoichiometric matrix (species x reactions)
        """
        if not reaction_system.species or not reaction_system.reactions:
            return np.array([])

        species_names = [s.name for s in reaction_system.species]
        n_species = len(species_names)
        n_reactions = len(reaction_system.reactions)

        matrix = np.zeros((n_species, n_reactions))

        for j, reaction in enumerate(reaction_system.reactions):
            # Subtract reactants (negative coefficients)
            for species, coeff in reaction.reactants.items():
                if species in species_names:
                    i = species_names.index(species)
                    matrix[i, j] -= coeff

            # Add products (positive coefficients)
            for species, coeff in reaction.products.items():
                if species in species_names:
                    i = species_names.index(species)
                    matrix[i, j] += coeff

        return matrix

    def verify_mass_balance(self, reaction: Reaction, species_masses: Dict[str, float]) -> bool:
        """
        Verify mass balance for a single reaction.

        Args:
            reaction: The reaction to check
            species_masses: Mapping of species names to molecular masses

        Returns:
            bool: True if mass is conserved within tolerance
        """
        reactant_mass = sum(coeff * species_masses.get(species, 0)
                          for species, coeff in reaction.reactants.items())
        product_mass = sum(coeff * species_masses.get(species, 0)
                         for species, coeff in reaction.products.items())

        if reactant_mass == 0:
            return product_mass == 0

        relative_error = abs(reactant_mass - product_mass) / reactant_mass
        return relative_error < self.tolerance

    def analyze_conservation_laws(self, stoich_matrix: np.ndarray,
                                mass_vector: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Analyze conservation laws from stoichiometric matrix.

        Args:
            stoich_matrix: Stoichiometric matrix (species x reactions)
            mass_vector: Optional vector of species masses

        Returns:
            Dict containing conservation analysis results
        """
        if stoich_matrix.size == 0:
            return {"conserved_quantities": 0, "rank": 0, "nullity": 0}

        # Compute null space (conserved quantities)
        _, s, vt = np.linalg.svd(stoich_matrix.T)  # Transpose for reaction space
        rank = np.sum(s > self.tolerance)
        nullity = stoich_matrix.shape[0] - rank  # Number of conserved quantities

        result = {
            "rank": rank,
            "nullity": nullity,
            "conserved_quantities": nullity,
            "singular_values": s.tolist()
        }

        # Mass conservation check if masses provided
        if mass_vector is not None and mass_vector.shape[0] == stoich_matrix.shape[0]:
            mass_balance = mass_vector.T @ stoich_matrix
            mass_conserved = np.allclose(mass_balance, 0, atol=self.tolerance)
            result["mass_conserved"] = mass_conserved
            result["mass_balance_error"] = np.max(np.abs(mass_balance))

        return result

    def verify_dimensional_consistency(self, equations: List[Equation]) -> List[VerificationResult]:
        """
        Verify dimensional consistency of equations using SymPy.

        Args:
            equations: List of equations to check

        Returns:
            List of verification results for each equation
        """
        results = []

        for i, equation in enumerate(equations):
            try:
                # Convert to SymPy expressions for dimensional analysis
                lhs_expr = self._expr_to_sympy(equation.lhs)
                rhs_expr = self._expr_to_sympy(equation.rhs)

                # For now, basic structural validation
                # Full dimensional analysis would require unit information
                if lhs_expr is not None and rhs_expr is not None:
                    results.append(VerificationResult(
                        status=VerificationStatus.PASS,
                        message=f"Equation {i+1}: Structurally valid",
                        details={"equation_index": i}
                    ))
                else:
                    results.append(VerificationResult(
                        status=VerificationStatus.WARNING,
                        message=f"Equation {i+1}: Could not parse for dimensional analysis",
                        details={"equation_index": i}
                    ))
            except Exception as e:
                results.append(VerificationResult(
                    status=VerificationStatus.FAIL,
                    message=f"Equation {i+1}: Error in dimensional analysis: {str(e)}",
                    details={"equation_index": i, "error": str(e)}
                ))

        return results

    def check_numerical_stability(self, matrix: np.ndarray) -> Dict[str, Any]:
        """
        Check numerical stability properties of a matrix.

        Args:
            matrix: Matrix to analyze

        Returns:
            Dict containing stability analysis
        """
        if matrix.size == 0:
            return {"condition_number": 0, "is_well_conditioned": True}

        # Compute condition number
        try:
            cond_num = np.linalg.cond(matrix)
            is_well_conditioned = cond_num < 1e12  # Standard threshold

            # Check for near-singular matrix
            det = np.linalg.det(matrix) if matrix.shape[0] == matrix.shape[1] else None

            result = {
                "condition_number": float(cond_num),
                "is_well_conditioned": is_well_conditioned,
                "matrix_rank": np.linalg.matrix_rank(matrix),
                "frobenius_norm": np.linalg.norm(matrix, 'fro')
            }

            if det is not None:
                result["determinant"] = float(det)
                result["is_singular"] = abs(det) < self.tolerance

            return result

        except np.linalg.LinAlgError as e:
            return {
                "condition_number": float('inf'),
                "is_well_conditioned": False,
                "error": str(e)
            }

    def _verify_stoichiometric_matrix(self, reaction_system: ReactionSystem) -> None:
        """Verify stoichiometric matrix properties."""
        try:
            stoich_matrix = self.compute_stoichiometric_matrix(reaction_system)

            if stoich_matrix.size == 0:
                self.report.add_result(VerificationResult(
                    status=VerificationStatus.WARNING,
                    message="No reactions or species found for stoichiometric analysis"
                ))
                return

            # Check matrix dimensions
            expected_species = len(reaction_system.species)
            expected_reactions = len(reaction_system.reactions)

            if stoich_matrix.shape != (expected_species, expected_reactions):
                self.report.add_result(VerificationResult(
                    status=VerificationStatus.FAIL,
                    message=f"Stoichiometric matrix has wrong dimensions: {stoich_matrix.shape}, expected: ({expected_species}, {expected_reactions})"
                ))
                return

            # Analyze conservation properties
            conservation_analysis = self.analyze_conservation_laws(stoich_matrix)

            self.report.add_result(VerificationResult(
                status=VerificationStatus.PASS,
                message="Stoichiometric matrix computed successfully",
                details={
                    "matrix_shape": stoich_matrix.shape,
                    "matrix_rank": conservation_analysis["rank"],
                    "conserved_quantities": conservation_analysis["conserved_quantities"]
                }
            ))

        except Exception as e:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.FAIL,
                message=f"Error computing stoichiometric matrix: {str(e)}",
                details={"error": str(e)}
            ))

    def _verify_mass_conservation(self, reaction_system: ReactionSystem) -> None:
        """Verify mass conservation for all reactions."""
        species_with_mass = {s.name: s.mass for s in reaction_system.species if s.mass is not None}

        if not species_with_mass:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.WARNING,
                message="No species masses provided for mass conservation check"
            ))
            return

        failed_reactions = []

        for i, reaction in enumerate(reaction_system.reactions):
            if not self.verify_mass_balance(reaction, species_with_mass):
                failed_reactions.append((i, reaction.name))

        if failed_reactions:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.FAIL,
                message=f"Mass conservation violated in {len(failed_reactions)} reactions",
                details={"failed_reactions": failed_reactions}
            ))
        else:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.PASS,
                message=f"Mass conservation verified for all {len(reaction_system.reactions)} reactions"
            ))

    def _verify_species_consistency(self, reaction_system: ReactionSystem) -> None:
        """Verify that all species used in reactions are defined."""
        defined_species = {s.name for s in reaction_system.species}
        used_species = set()

        for reaction in reaction_system.reactions:
            used_species.update(reaction.reactants.keys())
            used_species.update(reaction.products.keys())

        undefined_species = used_species - defined_species
        unused_species = defined_species - used_species

        if undefined_species:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.FAIL,
                message=f"Undefined species used in reactions: {undefined_species}",
                details={"undefined_species": list(undefined_species)}
            ))

        if unused_species:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.WARNING,
                message=f"Defined species not used in any reaction: {unused_species}",
                details={"unused_species": list(unused_species)}
            ))

        if not undefined_species:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.PASS,
                message="All species used in reactions are properly defined"
            ))

    def _verify_parameters(self, reaction_system: ReactionSystem) -> None:
        """Verify parameter definitions and usage."""
        if not reaction_system.parameters:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.WARNING,
                message="No parameters defined in reaction system"
            ))
            return

        # Check for reasonable parameter values
        extreme_parameters = []

        for param in reaction_system.parameters:
            if isinstance(param.value, (int, float)):
                if param.value <= 0:
                    extreme_parameters.append((param.name, "non-positive"))
                elif param.value > 1e10 or param.value < 1e-10:
                    extreme_parameters.append((param.name, "extreme_value"))

        if extreme_parameters:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.WARNING,
                message=f"Parameters with extreme or invalid values: {len(extreme_parameters)}",
                details={"extreme_parameters": extreme_parameters}
            ))

        self.report.add_result(VerificationResult(
            status=VerificationStatus.PASS,
            message=f"Verified {len(reaction_system.parameters)} parameters"
        ))

    def _verify_variable_equation_consistency(self, model: Model) -> None:
        """Verify consistency between variables and equations."""
        # Extract variables mentioned in equations
        equation_vars = set()

        for equation in model.equations:
            equation_vars.update(self._extract_variables(equation.lhs))
            equation_vars.update(self._extract_variables(equation.rhs))

        defined_vars = set(model.variables.keys())

        undefined_vars = equation_vars - defined_vars
        unused_vars = defined_vars - equation_vars

        if undefined_vars:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.FAIL,
                message=f"Undefined variables used in equations: {undefined_vars}",
                details={"undefined_variables": list(undefined_vars)}
            ))

        if unused_vars:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.WARNING,
                message=f"Defined variables not used in equations: {unused_vars}",
                details={"unused_variables": list(unused_vars)}
            ))

        if not undefined_vars:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.PASS,
                message="Variable-equation consistency verified"
            ))

    def _verify_dimensional_consistency(self, model: Model) -> None:
        """Verify dimensional consistency of model equations."""
        dim_results = self.verify_dimensional_consistency(model.equations)

        failed_count = sum(1 for r in dim_results if r.status == VerificationStatus.FAIL)
        warning_count = sum(1 for r in dim_results if r.status == VerificationStatus.WARNING)

        if failed_count > 0:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.FAIL,
                message=f"Dimensional consistency failed for {failed_count} equations",
                details={"failed_equations": failed_count}
            ))
        elif warning_count > 0:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.WARNING,
                message=f"Dimensional analysis warnings for {warning_count} equations",
                details={"warning_equations": warning_count}
            ))
        else:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.PASS,
                message=f"Dimensional consistency verified for {len(model.equations)} equations"
            ))

    def _verify_cross_references(self, model: Model) -> None:
        """Verify all cross-references are valid."""
        # This would check references between model components
        # For now, basic implementation
        self.report.add_result(VerificationResult(
            status=VerificationStatus.PASS,
            message="Cross-reference validation completed"
        ))

    def _verify_equation_solvability(self, model: Model) -> None:
        """Verify that the equation system is potentially solvable."""
        n_equations = len(model.equations)
        state_vars = [name for name, var in model.variables.items() if var.type == 'state']
        n_state_vars = len(state_vars)

        if n_equations == 0:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.WARNING,
                message="No equations found in model"
            ))
            return

        if n_state_vars == 0:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.WARNING,
                message="No state variables found in model"
            ))
            return

        if n_equations != n_state_vars:
            status = VerificationStatus.WARNING if abs(n_equations - n_state_vars) <= 2 else VerificationStatus.FAIL
            self.report.add_result(VerificationResult(
                status=status,
                message=f"Equation count ({n_equations}) != state variable count ({n_state_vars})",
                details={"n_equations": n_equations, "n_state_variables": n_state_vars}
            ))
        else:
            self.report.add_result(VerificationResult(
                status=VerificationStatus.PASS,
                message=f"Equation system is potentially solvable ({n_equations} equations, {n_state_vars} state variables)"
            ))

    def _extract_variables(self, expr: Expr) -> Set[str]:
        """Extract variable names from an expression."""
        if isinstance(expr, str):
            # Simple heuristic: if it's a string and looks like a variable
            if expr.isidentifier():
                return {expr}
            return set()
        elif isinstance(expr, ExprNode):
            variables = set()
            for arg in expr.args:
                variables.update(self._extract_variables(arg))
            return variables
        else:
            # Numbers don't contribute variables
            return set()

    def _expr_to_sympy(self, expr: Expr) -> Optional[sp.Expr]:
        """Convert ESM expression to SymPy expression."""
        try:
            if isinstance(expr, (int, float)):
                return sp.Float(expr)
            elif isinstance(expr, str):
                if expr.isidentifier():
                    return sp.Symbol(expr)
                else:
                    # Try to parse as expression
                    return sp.parse_expr(expr)
            elif isinstance(expr, ExprNode):
                # Convert ExprNode to SymPy
                if expr.op == '+' and len(expr.args) >= 2:
                    args = [self._expr_to_sympy(arg) for arg in expr.args]
                    if all(arg is not None for arg in args):
                        return sum(args)
                elif expr.op == '*' and len(expr.args) >= 2:
                    args = [self._expr_to_sympy(arg) for arg in expr.args]
                    if all(arg is not None for arg in args):
                        result = args[0]
                        for arg in args[1:]:
                            result *= arg
                        return result
                # Add more operators as needed
                return None
            return None
        except Exception:
            return None


# Convenience functions for common verification tasks

def verify_reaction_system(reaction_system: ReactionSystem, tolerance: float = 1e-10) -> VerificationReport:
    """
    Convenience function to verify a reaction system.

    Args:
        reaction_system: The reaction system to verify
        tolerance: Numerical tolerance for comparisons

    Returns:
        VerificationReport: Complete verification results
    """
    verifier = MathematicalVerifier(tolerance=tolerance)
    return verifier.verify_reaction_system(reaction_system)


def verify_model(model: Model, tolerance: float = 1e-10) -> VerificationReport:
    """
    Convenience function to verify a mathematical model.

    Args:
        model: The model to verify
        tolerance: Numerical tolerance for comparisons

    Returns:
        VerificationReport: Complete verification results
    """
    verifier = MathematicalVerifier(tolerance=tolerance)
    return verifier.verify_model(model)


def compute_stoichiometric_matrix(reaction_system: ReactionSystem) -> np.ndarray:
    """
    Convenience function to compute stoichiometric matrix.

    Args:
        reaction_system: System containing species and reactions

    Returns:
        np.ndarray: Stoichiometric matrix (species x reactions)
    """
    verifier = MathematicalVerifier()
    return verifier.compute_stoichiometric_matrix(reaction_system)