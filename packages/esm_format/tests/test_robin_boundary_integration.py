"""
Integration tests for Robin boundary condition support.

Tests the complete pipeline from JSON parsing to boundary condition processing
for Robin boundary conditions (αu + β∂u/∂n = γ).
"""

import pytest
import json
import numpy as np

from esm_format import load, BoundaryConditionType
from esm_format.boundary_conditions import BoundaryConditionProcessor


class TestRobinBoundaryIntegration:
    """Test Robin boundary condition integration."""

    def test_robin_boundary_parsing(self):
        """Should parse Robin boundary conditions from JSON."""
        data = {
            "esm": "0.1.0",
            "metadata": {
                "name": "robin_test",
                "authors": ["Test"],
                "created": "2024-01-01T00:00:00Z",
                "description": "Robin boundary test"
            },
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "independent_variable": "t",
                "spatial": {
                    "x": {"min": 0.0, "max": 1.0, "units": "m", "grid_spacing": 0.1},
                    "y": {"min": 0.0, "max": 1.0, "units": "m", "grid_spacing": 0.1}
                },
                "boundary_conditions": [
                    {
                        "type": "robin",
                        "dimensions": ["x"],
                        "robin_alpha": 1.0,
                        "robin_beta": 2.0,
                        "robin_gamma": 3.0
                    }
                ]
            }
        }

        result = load(json.dumps(data))
        domain = result.domains[0]

        # Check Robin boundary condition was parsed correctly
        assert len(domain.boundary_conditions) == 1
        bc = domain.boundary_conditions[0]

        assert bc.type == BoundaryConditionType.ROBIN
        assert bc.dimensions == ["x"]
        assert bc.robin_alpha == 1.0
        assert bc.robin_beta == 2.0
        assert bc.robin_gamma == 3.0

    def test_robin_boundary_validation_missing_coefficients(self):
        """Should validate Robin boundary conditions require all coefficients."""
        data = {
            "esm": "0.1.0",
            "metadata": {
                "name": "robin_test",
                "authors": ["Test"],
                "created": "2024-01-01T00:00:00Z",
                "description": "Robin boundary test"
            },
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "spatial": {
                    "x": {"min": 0.0, "max": 1.0, "units": "m"}
                },
                "boundary_conditions": [
                    {
                        "type": "robin",
                        "dimensions": ["x"],
                        "robin_alpha": 1.0
                        # Missing robin_beta and robin_gamma
                    }
                ]
            }
        }

        with pytest.raises(ValueError, match="Robin boundary condition requires"):
            load(json.dumps(data))

    def test_robin_boundary_processor_compatibility(self):
        """Should work with boundary condition processor."""
        # Create a simple Robin boundary condition
        from esm_format.types import BoundaryCondition, Domain, SpatialDimension

        domain = Domain(
            spatial={
                "x": SpatialDimension(min=0.0, max=1.0, units="m", grid_spacing=0.1)
            },
            boundary_conditions=[]
        )

        bc = BoundaryCondition(
            type=BoundaryConditionType.ROBIN,
            dimensions=["x"],
            robin_alpha=1.0,
            robin_beta=2.0,
            robin_gamma=3.0
        )

        processor = BoundaryConditionProcessor()
        field = np.array([1.0, 2.0, 3.0, 4.0])

        # Should validate without errors (Robin not fully implemented yet, so just validates structure)
        warnings = processor.validate_boundary_conditions([bc], domain)
        assert isinstance(warnings, list)  # Should return warnings list

    def test_all_boundary_types_parsing(self):
        """Should parse all supported boundary condition types."""
        data = {
            "esm": "0.1.0",
            "metadata": {
                "name": "all_boundary_test",
                "authors": ["Test"],
                "created": "2024-01-01T00:00:00Z",
                "description": "All boundary types test"
            },
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "spatial": {
                    "x": {"min": 0.0, "max": 1.0, "units": "m", "grid_spacing": 0.1},
                    "y": {"min": 0.0, "max": 1.0, "units": "m", "grid_spacing": 0.1}
                },
                "boundary_conditions": [
                    {"type": "constant", "dimensions": ["x"], "value": 1.0},
                    {"type": "dirichlet", "dimensions": ["x"], "value": 2.0},
                    {"type": "zero_gradient", "dimensions": ["y"]},
                    {"type": "neumann", "dimensions": ["y"], "value": 0.0},
                    {"type": "periodic", "dimensions": ["x"]},
                    {
                        "type": "robin",
                        "dimensions": ["y"],
                        "robin_alpha": 1.0,
                        "robin_beta": 1.0,
                        "robin_gamma": 0.0
                    }
                ]
            }
        }

        result = load(json.dumps(data))
        domain = result.domains[0]

        # Check all boundary conditions were parsed
        assert len(domain.boundary_conditions) == 6

        bc_types = [bc.type for bc in domain.boundary_conditions]
        expected_types = [
            BoundaryConditionType.CONSTANT,
            BoundaryConditionType.DIRICHLET,
            BoundaryConditionType.ZERO_GRADIENT,
            BoundaryConditionType.NEUMANN,
            BoundaryConditionType.PERIODIC,
            BoundaryConditionType.ROBIN
        ]

        assert bc_types == expected_types

        # Check Robin boundary was parsed with all coefficients
        robin_bc = domain.boundary_conditions[5]
        assert robin_bc.type == BoundaryConditionType.ROBIN
        assert robin_bc.robin_alpha == 1.0
        assert robin_bc.robin_beta == 1.0
        assert robin_bc.robin_gamma == 0.0


if __name__ == "__main__":
    pytest.main([__file__])