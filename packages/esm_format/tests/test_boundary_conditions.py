"""
Test suite for boundary condition processing system.

Tests comprehensive boundary condition functionality including:
- Basic boundary condition validation
- Spatial/temporal variation support
- Robin boundary condition handling
- Domain geometry consistency validation
- Boundary condition application and processing
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from esm_format.boundary_conditions import (
    BoundaryConditionProcessor,
    BoundaryProcessorConfig,
    BoundaryConstraint,
    BoundaryLocationError,
    BoundaryValueError,
    create_dirichlet_boundary,
    create_neumann_boundary,
    create_periodic_boundary,
    validate_domain_boundary_consistency,
)
from esm_format.types import (
    BoundaryCondition,
    BoundaryConditionType,
    Domain,
    SpatialDimension,
)


class TestBoundaryConditionProcessor:
    """Test boundary condition processor functionality."""

    def test_processor_initialization(self):
        """Should initialize processor with default config."""
        processor = BoundaryConditionProcessor()
        assert processor.config is not None
        assert isinstance(processor.config, BoundaryProcessorConfig)

    def test_processor_initialization_with_config(self):
        """Should initialize processor with custom config."""
        config = BoundaryProcessorConfig(
            ghost_cells=2,
            strict_geometry=False
        )
        processor = BoundaryConditionProcessor(config)
        assert processor.config.ghost_cells == 2
        assert processor.config.strict_geometry is False

    def test_validate_empty_boundary_conditions(self):
        """Should handle empty boundary conditions."""
        processor = BoundaryConditionProcessor()
        domain = Mock()
        warnings = processor.validate_boundary_conditions([], domain)
        assert warnings == []

    def test_validate_boundary_condition_dimension_mismatch(self):
        """Should raise error for undefined dimensions."""
        processor = BoundaryConditionProcessor()

        # Create mock domain with limited dimensions
        domain = Mock()
        domain.spatial = {"x": Mock(), "y": Mock()}

        bc = BoundaryCondition(
            type=BoundaryConditionType.CONSTANT,
            dimensions=["z"],  # Dimension not in domain
            value=1.0
        )

        with pytest.raises(BoundaryLocationError, match="dimension 'z' not found"):
            processor.validate_boundary_conditions([bc], domain)

    def test_validate_constant_boundary_missing_value(self):
        """Should raise error for constant boundary without value."""
        processor = BoundaryConditionProcessor()

        domain = Mock()
        domain.spatial = {"x": Mock()}

        bc = BoundaryCondition(
            type=BoundaryConditionType.CONSTANT,
            dimensions=["x"],
            value=None  # Missing value
        )

        with pytest.raises(BoundaryValueError, match="requires a value"):
            processor.validate_boundary_conditions([bc], domain)

    def test_validate_dirichlet_boundary_missing_value(self):
        """Should raise error for Dirichlet boundary without value."""
        processor = BoundaryConditionProcessor()

        domain = Mock()
        domain.spatial = {"x": Mock()}

        bc = BoundaryCondition(
            type=BoundaryConditionType.DIRICHLET,
            dimensions=["x"],
            value=None
        )

        with pytest.raises(BoundaryValueError, match="requires a value"):
            processor.validate_boundary_conditions([bc], domain)

    def test_validate_periodic_boundary_finite_domain(self):
        """Should validate periodic boundary requires finite domain."""
        processor = BoundaryConditionProcessor()

        domain = Mock()
        spatial_dim = Mock()
        spatial_dim.min = None
        spatial_dim.max = None
        domain.spatial = {"x": spatial_dim}

        bc = BoundaryCondition(
            type=BoundaryConditionType.PERIODIC,
            dimensions=["x"]
        )

        with pytest.raises(BoundaryLocationError, match="requires finite domain bounds"):
            processor.validate_boundary_conditions([bc], domain)

    def test_validate_neumann_boundary_grid_spacing(self):
        """Should validate Neumann boundary requires positive grid spacing."""
        processor = BoundaryConditionProcessor()

        domain = Mock()
        spatial_dim = Mock()
        spatial_dim.grid_spacing = 0.0  # Invalid
        domain.spatial = {"x": spatial_dim}

        bc = BoundaryCondition(
            type=BoundaryConditionType.NEUMANN,
            dimensions=["x"]
        )

        with pytest.raises(BoundaryLocationError, match="requires positive grid spacing"):
            processor.validate_boundary_conditions([bc], domain)

    def test_process_empty_boundary_conditions(self):
        """Should return unchanged field for empty boundary conditions."""
        processor = BoundaryConditionProcessor()
        field = np.array([1, 2, 3, 4])
        domain = Mock()

        result = processor.process_boundary_conditions(field, [], domain)
        np.testing.assert_array_equal(result, field)

    def test_process_dirichlet_boundary_1d(self):
        """Should apply Dirichlet boundary conditions to 1D field."""
        processor = BoundaryConditionProcessor()
        field = np.array([1.0, 2.0, 3.0, 4.0])

        domain = Mock()
        domain.spatial = {"x": Mock()}

        bc = BoundaryCondition(
            type=BoundaryConditionType.DIRICHLET,
            dimensions=["x"],
            value=0.0
        )

        result = processor.process_boundary_conditions(field, [bc], domain)

        # Check boundary values are set
        assert result[0] == 0.0
        assert result[-1] == 0.0
        # Interior values unchanged
        assert result[1] == 2.0
        assert result[2] == 3.0

    def test_process_dirichlet_boundary_2d(self):
        """Should apply Dirichlet boundary conditions to 2D field."""
        processor = BoundaryConditionProcessor()
        field = np.ones((4, 4))

        domain = Mock()
        domain.spatial = {"x": Mock(), "y": Mock()}

        bc = BoundaryCondition(
            type=BoundaryConditionType.DIRICHLET,
            dimensions=["x", "y"],
            value=2.0
        )

        result = processor.process_boundary_conditions(field, [bc], domain)

        # Check all boundary values are set to 2.0
        assert np.all(result[0, :] == 2.0)  # Top
        assert np.all(result[-1, :] == 2.0)  # Bottom
        assert np.all(result[:, 0] == 2.0)  # Left
        assert np.all(result[:, -1] == 2.0)  # Right

        # Interior values remain unchanged
        assert np.all(result[1:3, 1:3] == 1.0)

    def test_process_neumann_boundary_1d(self):
        """Should apply Neumann (zero gradient) boundary conditions to 1D field."""
        processor = BoundaryConditionProcessor()
        field = np.array([1.0, 2.0, 3.0, 4.0])

        domain = Mock()
        domain.spatial = {"x": Mock()}

        bc = BoundaryCondition(
            type=BoundaryConditionType.NEUMANN,
            dimensions=["x"]
        )

        result = processor.process_boundary_conditions(field, [bc], domain)

        # Check zero gradient: boundary values equal interior neighbors
        assert result[0] == result[1]  # Left boundary
        assert result[-1] == result[-2]  # Right boundary

    def test_process_neumann_boundary_2d(self):
        """Should apply Neumann boundary conditions to 2D field."""
        processor = BoundaryConditionProcessor()
        field = np.arange(16).reshape(4, 4).astype(float)

        domain = Mock()
        domain.spatial = {"x": Mock(), "y": Mock()}

        bc = BoundaryCondition(
            type=BoundaryConditionType.NEUMANN,
            dimensions=["x", "y"]
        )

        result = processor.process_boundary_conditions(field, [bc], domain)

        # Check zero gradient conditions
        np.testing.assert_array_equal(result[0, :], result[1, :])  # Top
        np.testing.assert_array_equal(result[-1, :], result[-2, :])  # Bottom
        np.testing.assert_array_equal(result[:, 0], result[:, 1])  # Left
        np.testing.assert_array_equal(result[:, -1], result[:, -2])  # Right

    def test_process_periodic_boundary(self):
        """Should handle periodic boundary conditions."""
        processor = BoundaryConditionProcessor()
        field = np.array([1.0, 2.0, 3.0, 4.0])

        domain = Mock()
        domain.spatial = {"x": Mock()}

        bc = BoundaryCondition(
            type=BoundaryConditionType.PERIODIC,
            dimensions=["x"]
        )

        # For now, periodic boundaries return unchanged field with warning
        result = processor.process_boundary_conditions(field, [bc], domain)
        np.testing.assert_array_equal(result, field)

    def test_evaluate_boundary_value_constant(self):
        """Should evaluate constant boundary values."""
        processor = BoundaryConditionProcessor()

        assert processor._evaluate_boundary_value(5.0) == 5.0
        assert processor._evaluate_boundary_value(3) == 3.0

    def test_evaluate_boundary_value_string(self):
        """Should evaluate string boundary values."""
        processor = BoundaryConditionProcessor()

        assert processor._evaluate_boundary_value("2.5") == 2.5
        assert processor._evaluate_boundary_value("invalid") == 0.0  # Falls back to 0.0

    def test_evaluate_boundary_value_callable(self):
        """Should evaluate callable boundary values."""
        processor = BoundaryConditionProcessor()

        # Time-independent function
        func = lambda: 3.5
        assert processor._evaluate_boundary_value(func) == 3.5

        # Time-dependent function
        time_func = lambda t: 2.0 * t
        assert processor._evaluate_boundary_value(time_func, time=2.0) == 4.0

    def test_evaluate_boundary_value_callable_error(self):
        """Should handle callable evaluation errors."""
        processor = BoundaryConditionProcessor()

        def error_func():
            raise ValueError("Test error")

        result = processor._evaluate_boundary_value(error_func)
        assert result == 0.0  # Falls back to 0.0 on error

    def test_strict_geometry_validation(self):
        """Should raise errors in strict geometry mode."""
        config = BoundaryProcessorConfig(strict_geometry=True)
        processor = BoundaryConditionProcessor(config)

        field = np.array([1, 2, 3])
        domain = Mock()
        domain.spatial = {}  # Empty spatial dimensions

        bc = BoundaryCondition(
            type=BoundaryConditionType.CONSTANT,
            dimensions=["x"],  # Dimension not in domain
            value=1.0
        )

        with pytest.raises(BoundaryLocationError):
            processor.process_boundary_conditions(field, [bc], domain)

    def test_non_strict_geometry_validation(self):
        """Should issue warnings in non-strict geometry mode."""
        config = BoundaryProcessorConfig(strict_geometry=False)
        processor = BoundaryConditionProcessor(config)

        field = np.array([1, 2, 3])
        domain = Mock()
        domain.spatial = {}

        bc = BoundaryCondition(
            type=BoundaryConditionType.CONSTANT,
            dimensions=["x"],
            value=1.0
        )

        # Should not raise error, but may issue warnings
        with patch('warnings.warn') as mock_warn:
            result = processor.process_boundary_conditions(field, [bc], domain)
            # Should return original field
            np.testing.assert_array_equal(result, field)


class TestBoundaryConditionHelpers:
    """Test boundary condition creation helpers."""

    def test_create_dirichlet_boundary(self):
        """Should create Dirichlet boundary condition."""
        bc = create_dirichlet_boundary(["x"], 2.5)
        assert bc.type == BoundaryConditionType.DIRICHLET
        assert bc.dimensions == ["x"]
        assert bc.value == 2.5

    def test_create_neumann_boundary(self):
        """Should create Neumann boundary condition."""
        bc = create_neumann_boundary(["y"], gradient_value=0.0)
        assert bc.type == BoundaryConditionType.NEUMANN
        assert bc.dimensions == ["y"]
        assert bc.value == 0.0

    def test_create_neumann_boundary_default_gradient(self):
        """Should create Neumann boundary with default zero gradient."""
        bc = create_neumann_boundary(["z"])
        assert bc.type == BoundaryConditionType.NEUMANN
        assert bc.dimensions == ["z"]
        assert bc.value == 0.0

    def test_create_periodic_boundary(self):
        """Should create periodic boundary condition."""
        bc = create_periodic_boundary(["x", "y"])
        assert bc.type == BoundaryConditionType.PERIODIC
        assert bc.dimensions == ["x", "y"]
        assert bc.value is None


class TestDomainBoundaryValidation:
    """Test domain-level boundary condition validation."""

    def test_validate_domain_no_boundary_conditions(self):
        """Should issue warning for domain with no boundary conditions."""
        domain = Mock()
        domain.boundary_conditions = []

        issues = validate_domain_boundary_consistency(domain, strict=False)
        assert "No boundary conditions specified" in issues[0]

    def test_validate_domain_with_valid_boundaries(self):
        """Should validate domain with consistent boundary conditions."""
        domain = Mock()
        domain.spatial = {"x": Mock(), "y": Mock()}
        domain.boundary_conditions = [
            BoundaryCondition(
                type=BoundaryConditionType.DIRICHLET,
                dimensions=["x"],
                value=1.0
            )
        ]

        issues = validate_domain_boundary_consistency(domain, strict=False)
        # Should pass validation without critical issues
        assert len(issues) == 0

    def test_validate_domain_strict_mode_error(self):
        """Should raise error in strict validation mode."""
        domain = Mock()
        domain.spatial = {}  # Empty spatial dimensions
        domain.boundary_conditions = [
            BoundaryCondition(
                type=BoundaryConditionType.CONSTANT,
                dimensions=["x"],  # Undefined dimension
                value=1.0
            )
        ]

        with pytest.raises(BoundaryLocationError):
            validate_domain_boundary_consistency(domain, strict=True)

    def test_validate_domain_non_strict_mode_warning(self):
        """Should collect warnings in non-strict validation mode."""
        domain = Mock()
        domain.spatial = {}
        domain.boundary_conditions = [
            BoundaryCondition(
                type=BoundaryConditionType.CONSTANT,
                dimensions=["x"],
                value=1.0
            )
        ]

        issues = validate_domain_boundary_consistency(domain, strict=False)
        assert len(issues) > 0  # Should have validation issues


class TestBoundaryConditionConfig:
    """Test boundary condition processor configuration."""

    def test_default_config(self):
        """Should create default configuration."""
        config = BoundaryProcessorConfig()
        assert config.ghost_cells == 1
        assert config.interpolation_order == 2
        assert config.time_integration == "linear"
        assert config.strict_geometry is True
        assert config.warn_approximations is True
        assert config.cache_evaluations is True
        assert config.parallel_boundaries is False

    def test_custom_config(self):
        """Should create custom configuration."""
        config = BoundaryProcessorConfig(
            ghost_cells=2,
            interpolation_order=4,
            time_integration="cubic",
            strict_geometry=False,
            warn_approximations=False,
            cache_evaluations=False,
            parallel_boundaries=True
        )

        assert config.ghost_cells == 2
        assert config.interpolation_order == 4
        assert config.time_integration == "cubic"
        assert config.strict_geometry is False
        assert config.warn_approximations is False
        assert config.cache_evaluations is False
        assert config.parallel_boundaries is True


class TestBoundaryConditionTypes:
    """Test enhanced boundary condition types and Robin BC support."""

    def test_robin_boundary_condition_fields(self):
        """Should support Robin boundary condition parameters."""
        bc = BoundaryCondition(
            type=BoundaryConditionType.ROBIN,
            dimensions=["x"],
            robin_alpha=1.0,
            robin_beta=2.0,
            robin_gamma=3.0
        )

        assert bc.type == BoundaryConditionType.ROBIN
        assert bc.robin_alpha == 1.0
        assert bc.robin_beta == 2.0
        assert bc.robin_gamma == 3.0

    def test_robin_enum_value(self):
        """Should have Robin boundary condition in enum."""
        assert BoundaryConditionType.ROBIN.value == "robin"
        assert BoundaryConditionType.ROBIN in list(BoundaryConditionType)

    def test_all_boundary_condition_types(self):
        """Should have all expected boundary condition types."""
        expected_types = {
            "zero_gradient",
            "constant",
            "periodic",
            "dirichlet",
            "neumann",
            "robin"
        }

        actual_types = {bc.value for bc in BoundaryConditionType}
        assert actual_types == expected_types


if __name__ == "__main__":
    pytest.main([__file__])