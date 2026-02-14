"""
Integration test demonstrating complete domain configuration parsing and validation.
"""

import json
from esm_format import load, save, Domain, TemporalDomain, SpatialDimension
from esm_format.types import InitialConditionType, BoundaryConditionType


def test_complete_domain_workflow():
    """Test complete workflow: parse, validate, and serialize domain configuration."""

    # Complete ESM file with comprehensive domain configuration
    esm_data = {
        "esm": "0.1.0",
        "metadata": {
            "name": "Atmospheric Chemistry Model",
            "description": "3D atmospheric chemistry simulation with comprehensive domain configuration",
            "authors": ["Test Author"]
        },
        "models": {
            "atmosphere": {
                "variables": {
                    "O3": {
                        "type": "state",
                        "units": "ppb",
                        "description": "Ozone concentration"
                    },
                    "NO2": {
                        "type": "state",
                        "units": "ppb",
                        "description": "Nitrogen dioxide concentration"
                    }
                },
                "equations": [
                    {"lhs": {"op": "D", "args": ["O3"], "wrt": "t"}, "rhs": {"op": "+", "args": [1.0, "NO2"]}}
                ]
            }
        },
        "domain": {
            "independent_variable": "t",
            "temporal": {
                "start": "2024-07-01T00:00:00Z",
                "end": "2024-07-02T00:00:00Z",
                "reference_time": "2024-07-01T12:00:00Z"
            },
            "spatial": {
                "lon": {
                    "min": -125.0,
                    "max": -65.0,
                    "units": "degrees",
                    "grid_spacing": 0.5
                },
                "lat": {
                    "min": 25.0,
                    "max": 50.0,
                    "units": "degrees",
                    "grid_spacing": 0.5
                },
                "lev": {
                    "min": 1.0,
                    "max": 30.0,
                    "units": "km",
                    "grid_spacing": 1.0
                }
            },
            "coordinate_transforms": [
                {
                    "id": "lonlat_to_cartesian",
                    "description": "Convert longitude/latitude to Cartesian coordinates",
                    "dimensions": ["lon", "lat"]
                }
            ],
            "spatial_ref": "WGS84",
            "initial_conditions": {
                "type": "constant",
                "value": 30.0
            },
            "boundary_conditions": [
                {
                    "type": "zero_gradient",
                    "dimensions": ["lon", "lat"]
                },
                {
                    "type": "constant",
                    "dimensions": ["lev"],
                    "value": 10.0
                }
            ]
        }
    }

    # Test loading and parsing
    esm_obj = load(json.dumps(esm_data))

    # Verify basic structure
    assert len(esm_obj.domains) == 1
    assert len(esm_obj.models) == 1
    assert esm_obj.models[0].name == "atmosphere"

    domain = esm_obj.domains[0]

    # Verify temporal domain
    assert domain.independent_variable == "t"
    assert domain.temporal is not None
    assert domain.temporal.start == "2024-07-01T00:00:00Z"
    assert domain.temporal.end == "2024-07-02T00:00:00Z"
    assert domain.temporal.reference_time == "2024-07-01T12:00:00Z"

    # Verify spatial domain
    assert domain.spatial is not None
    assert len(domain.spatial) == 3

    # Check longitude
    lon_dim = domain.spatial["lon"]
    assert lon_dim.min == -125.0
    assert lon_dim.max == -65.0
    assert lon_dim.units == "degrees"
    assert lon_dim.grid_spacing == 0.5

    # Check latitude
    lat_dim = domain.spatial["lat"]
    assert lat_dim.min == 25.0
    assert lat_dim.max == 50.0
    assert lat_dim.units == "degrees"
    assert lat_dim.grid_spacing == 0.5

    # Check vertical levels
    lev_dim = domain.spatial["lev"]
    assert lev_dim.min == 1.0
    assert lev_dim.max == 30.0
    assert lev_dim.units == "km"
    assert lev_dim.grid_spacing == 1.0

    # Verify coordinate transforms
    assert len(domain.coordinate_transforms) == 1
    transform = domain.coordinate_transforms[0]
    assert transform.id == "lonlat_to_cartesian"
    assert transform.description == "Convert longitude/latitude to Cartesian coordinates"
    assert set(transform.dimensions) == {"lon", "lat"}

    # Verify spatial reference
    assert domain.spatial_ref == "WGS84"

    # Verify initial conditions
    assert domain.initial_conditions is not None
    assert domain.initial_conditions.type == InitialConditionType.CONSTANT
    assert domain.initial_conditions.value == 30.0

    # Verify boundary conditions
    assert len(domain.boundary_conditions) == 2

    bc1 = domain.boundary_conditions[0]
    assert bc1.type == BoundaryConditionType.ZERO_GRADIENT
    assert set(bc1.dimensions) == {"lon", "lat"}

    bc2 = domain.boundary_conditions[1]
    assert bc2.type == BoundaryConditionType.CONSTANT
    assert bc2.dimensions == ["lev"]
    assert bc2.value == 10.0

    # Test serialization round-trip
    serialized = save(esm_obj)
    esm_obj2 = load(serialized)

    # Verify domain persists through serialization
    domain2 = esm_obj2.domains[0]
    assert domain2.independent_variable == domain.independent_variable
    assert domain2.temporal.start == domain.temporal.start
    assert len(domain2.spatial) == len(domain.spatial)
    assert len(domain2.coordinate_transforms) == len(domain.coordinate_transforms)
    assert len(domain2.boundary_conditions) == len(domain.boundary_conditions)

    print("✅ Complete domain workflow test passed!")
    print(f"   - Parsed {len(domain.spatial)} spatial dimensions")
    print(f"   - Validated {len(domain.coordinate_transforms)} coordinate transforms")
    print(f"   - Processed {len(domain.boundary_conditions)} boundary conditions")
    print(f"   - Verified temporal domain: {domain.temporal.start} to {domain.temporal.end}")
    print(f"   - Spatial coverage: lon=[{lon_dim.min}, {lon_dim.max}], lat=[{lat_dim.min}, {lat_dim.max}], lev=[{lev_dim.min}, {lev_dim.max}]")


if __name__ == "__main__":
    test_complete_domain_workflow()