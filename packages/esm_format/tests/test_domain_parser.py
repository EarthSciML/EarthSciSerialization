"""
Tests for domain configuration parsing and validation.
"""

import pytest
from esm_format.parse import load
from esm_format.types import (
    Domain, TemporalDomain, SpatialDimension, CoordinateTransform,
    InitialCondition, InitialConditionType, BoundaryCondition, BoundaryConditionType
)
import json


class TestDomainParsing:
    """Test domain configuration parsing."""

    def test_minimal_domain_parsing(self):
        """Test parsing of minimal domain with only temporal data."""
        data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "temporal": {
                    "start": "2024-05-01T00:00:00Z",
                    "end": "2024-05-03T00:00:00Z"
                }
            }
        }

        result = load(json.dumps(data))
        assert len(result.domains) == 1

        domain = result.domains[0]
        assert domain.temporal is not None
        assert domain.temporal.start == "2024-05-01T00:00:00Z"
        assert domain.temporal.end == "2024-05-03T00:00:00Z"
        assert domain.temporal.reference_time is None

    def test_complete_domain_parsing(self):
        """Test parsing of complete domain configuration."""
        data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "independent_variable": "t",
                "temporal": {
                    "start": "2024-05-01T00:00:00Z",
                    "end": "2024-05-03T00:00:00Z",
                    "reference_time": "2024-05-01T12:00:00Z"
                },
                "spatial": {
                    "x": {"min": 0.0, "max": 100.0, "units": "m", "grid_spacing": 1.0},
                    "y": {"min": -50.0, "max": 50.0, "units": "m", "grid_spacing": 0.5}
                },
                "coordinate_transforms": [{
                    "id": "xy_to_polar",
                    "description": "Convert x,y to r,theta",
                    "dimensions": ["x", "y"]
                }],
                "spatial_ref": "EPSG:4326",
                "initial_conditions": {
                    "type": "constant",
                    "value": 1.0
                },
                "boundary_conditions": [
                    {"type": "zero_gradient", "dimensions": ["x"]},
                    {"type": "constant", "dimensions": ["y"], "value": 1.5}
                ]
            }
        }

        result = load(json.dumps(data))
        domain = result.domains[0]

        # Check all fields
        assert domain.independent_variable == "t"
        assert domain.spatial_ref == "EPSG:4326"

        # Check spatial dimensions
        assert len(domain.spatial) == 2
        assert domain.spatial["x"].min == 0.0
        assert domain.spatial["x"].max == 100.0
        assert domain.spatial["x"].units == "m"
        assert domain.spatial["x"].grid_spacing == 1.0

        # Check coordinate transforms
        assert len(domain.coordinate_transforms) == 1
        transform = domain.coordinate_transforms[0]
        assert transform.id == "xy_to_polar"
        assert transform.description == "Convert x,y to r,theta"
        assert transform.dimensions == ["x", "y"]

        # Check initial conditions
        assert domain.initial_conditions.type == InitialConditionType.CONSTANT
        assert domain.initial_conditions.value == 1.0

        # Check boundary conditions
        assert len(domain.boundary_conditions) == 2
        bc1 = domain.boundary_conditions[0]
        assert bc1.type == BoundaryConditionType.ZERO_GRADIENT
        assert bc1.dimensions == ["x"]

        bc2 = domain.boundary_conditions[1]
        assert bc2.type == BoundaryConditionType.CONSTANT
        assert bc2.dimensions == ["y"]
        assert bc2.value == 1.5


class TestDomainValidation:
    """Test domain configuration validation."""

    def test_temporal_validation_start_after_end(self):
        """Test that validation catches start time after end time."""
        data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "temporal": {
                    "start": "2024-05-03T00:00:00Z",
                    "end": "2024-05-01T00:00:00Z"  # End before start
                }
            }
        }

        with pytest.raises(ValueError, match="start time must be before end time"):
            load(json.dumps(data))

    def test_temporal_validation_reference_time_outside_range(self):
        """Test that validation catches reference time outside start-end range."""
        data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "temporal": {
                    "start": "2024-05-01T00:00:00Z",
                    "end": "2024-05-03T00:00:00Z",
                    "reference_time": "2024-05-04T00:00:00Z"  # After end
                }
            }
        }

        with pytest.raises(ValueError, match="reference time must be within start and end times"):
            load(json.dumps(data))

    def test_spatial_validation_min_greater_than_max(self):
        """Test that validation catches min >= max in spatial dimensions."""
        data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "spatial": {
                    "x": {"min": 100.0, "max": 50.0, "units": "m"}  # Min > max
                }
            }
        }

        with pytest.raises(ValueError, match="min value must be less than max value"):
            load(json.dumps(data))

    def test_coordinate_validation_longitude_out_of_range(self):
        """Test that validation catches longitude values outside valid range."""
        data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "spatial": {
                    "lon": {"min": -200.0, "max": 200.0, "units": "degrees"}  # Outside -180 to 180
                }
            }
        }

        with pytest.raises(ValueError, match="values should be between -180 and 180 degrees"):
            load(json.dumps(data))

    def test_coordinate_validation_latitude_out_of_range(self):
        """Test that validation catches latitude values outside valid range."""
        data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "spatial": {
                    "lat": {"min": -100.0, "max": 100.0, "units": "degrees"}  # Outside -90 to 90
                }
            }
        }

        with pytest.raises(ValueError, match="values should be between -90 and 90 degrees"):
            load(json.dumps(data))

    def test_coordinate_transform_validation_undefined_dimension(self):
        """Test that validation catches coordinate transforms referencing undefined dimensions."""
        data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "spatial": {
                    "x": {"min": 0.0, "max": 100.0, "units": "m"}
                },
                "coordinate_transforms": [{
                    "id": "test_transform",
                    "description": "Test",
                    "dimensions": ["x", "y"]  # 'y' not defined in spatial
                }]
            }
        }

        with pytest.raises(ValueError, match="references undefined dimension 'y'"):
            load(json.dumps(data))

    def test_boundary_condition_validation_undefined_dimension(self):
        """Test that validation catches boundary conditions referencing undefined dimensions."""
        data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "spatial": {
                    "x": {"min": 0.0, "max": 100.0, "units": "m"}
                },
                "boundary_conditions": [{
                    "type": "constant",
                    "dimensions": ["z"],  # 'z' not defined in spatial
                    "value": 0.0
                }]
            }
        }

        with pytest.raises(ValueError, match="references undefined dimension 'z'"):
            load(json.dumps(data))

    def test_initial_condition_validation_constant_missing_value(self):
        """Test that schema validation catches constant initial conditions missing value."""
        data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "spatial": {
                    "x": {"min": 0.0, "max": 100.0, "units": "m"}
                },
                "initial_conditions": {
                    "type": "constant"
                    # Missing value - this should fail schema validation first
                }
            }
        }

        # The JSON schema should catch this before our validation runs
        with pytest.raises(Exception):  # Could be ValidationError from jsonschema
            load(json.dumps(data))

    def test_boundary_condition_validation_constant_missing_value(self):
        """Test that validation catches constant boundary conditions missing value."""
        data = {
            "esm": "0.1.0",
            "metadata": {"name": "Test"},
            "models": {"test": {"variables": {}, "equations": []}},
            "domain": {
                "spatial": {
                    "x": {"min": 0.0, "max": 100.0, "units": "m"}
                },
                "boundary_conditions": [{
                    "type": "constant",
                    "dimensions": ["x"]
                    # Missing value
                }]
            }
        }

        with pytest.raises(ValueError, match="requires a value"):
            load(json.dumps(data))


class TestBackwardCompatibility:
    """Test backward compatibility with legacy Domain format."""

    def test_legacy_domain_still_works(self):
        """Test that legacy domain format still works."""
        from esm_format.types import Domain

        # This is the old format from the test_types.py
        domain = Domain(name="2D", dimensions={"x": 100, "y": 50})

        assert domain.name == "2D"
        assert domain.dimensions == {"x": 100, "y": 50}
        # New fields should be None/empty
        assert domain.temporal is None
        assert domain.spatial is None
        assert len(domain.coordinate_transforms) == 0