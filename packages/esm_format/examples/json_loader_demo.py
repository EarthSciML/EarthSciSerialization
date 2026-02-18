#!/usr/bin/env python3
"""
Demonstration of JSON data loader functionality.

This example shows how to use the JSONLoader class to load JSON data with:
- Schema validation
- Type coercion
- Nested object access
- Data structure analysis
"""

import json
import tempfile
from pathlib import Path

# Import the ESM format modules
from esm_format.data_loaders import create_data_loader, JSONLoader
from esm_format.types import DataLoader, DataLoaderType


def main():
    """Demonstrate JSON loader functionality."""

    # Create sample JSON data
    sample_data = {
        "metadata": {
            "title": "Climate Model Configuration",
            "version": "2.0",
            "author": "Research Team",
            "created": "2024-02-14"
        },
        "simulation_parameters": {
            "time_step": "3600",  # String that should be coerced to int
            "simulation_duration": 86400.0,
            "output_frequency": "300",  # String that should be coerced to int
            "enable_logging": "true"  # String that should be coerced to bool
        },
        "atmospheric_data": {
            "temperature_profile": [273.15, 274.15, 275.15, 276.15, 277.15],
            "pressure_levels": [1000, 850, 700, 500, 300, 200, 100],
            "species_concentrations": {
                "CO2": 400.0,
                "CH4": 1.8,
                "N2O": 0.32
            }
        }
    }

    # Create a temporary JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
        json.dump(sample_data, tmp_file, indent=2)
        json_file_path = tmp_file.name

    try:
        print("=== JSON Data Loader Demo ===\n")

        # 1. Basic loading without filtering
        print("1. Loading complete JSON file:")
        basic_config = DataLoader(
            name="climate_config",
            type=DataLoaderType.STATIC,
            source=json_file_path
        )

        loader = create_data_loader(basic_config)
        data = loader.load()
        print(f"   Loaded {len(data)} top-level keys: {list(data.keys())}")
        print(f"   Metadata title: {data['metadata']['title']}")
        print()

        # 2. Loading with variable filtering
        print("2. Loading specific variables only:")
        filtered_config = DataLoader(
            name="filtered_data",
            type=DataLoaderType.STATIC,
            source=json_file_path,
            variables=["metadata", "simulation_parameters"]
        )

        filtered_loader = JSONLoader(filtered_config)
        filtered_data = filtered_loader.load()
        print(f"   Loaded {len(filtered_data)} filtered keys: {list(filtered_data.keys())}")
        print()

        # 3. Loading with nested variable access
        print("3. Loading nested variables with dot notation:")
        nested_config = DataLoader(
            name="nested_access",
            type=DataLoaderType.STATIC,
            source=json_file_path,
            variables=[
                "metadata.title",
                "simulation_parameters.time_step",
                "atmospheric_data.species_concentrations.CO2"
            ]
        )

        nested_loader = JSONLoader(nested_config)
        nested_data = nested_loader.load()
        for key, value in nested_data.items():
            print(f"   {key}: {value}")
        print()

        # 4. Type coercion
        print("4. Type coercion example:")
        coercion_config = DataLoader(
            name="coercion_demo",
            type=DataLoaderType.STATIC,
            source=json_file_path,
            format_options={
                "type_coercion": True,
                "coercion_rules": {
                    "simulation_parameters.time_step": "int",
                    "simulation_parameters.output_frequency": "int",
                    "simulation_parameters.enable_logging": "bool",
                    "atmospheric_data.temperature_profile": "numpy_array"
                }
            },
            variables=["simulation_parameters", "atmospheric_data"]
        )

        coercion_loader = JSONLoader(coercion_config)
        coerced_data = coercion_loader.load()

        print("   After type coercion:")
        time_step = coerced_data["simulation_parameters"]["time_step"]
        enable_logging = coerced_data["simulation_parameters"]["enable_logging"]
        temp_profile = coerced_data["atmospheric_data"]["temperature_profile"]

        print(f"   time_step: {time_step} (type: {type(time_step).__name__})")
        print(f"   enable_logging: {enable_logging} (type: {type(enable_logging).__name__})")
        print(f"   temperature_profile: {type(temp_profile).__name__} with shape {temp_profile.shape}")
        print()

        # 5. Schema validation
        print("5. Schema validation example:")
        schema = {
            "type": "object",
            "properties": {
                "metadata": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "version": {"type": "string"},
                        "author": {"type": "string"}
                    },
                    "required": ["title", "author"]
                },
                "simulation_parameters": {
                    "type": "object",
                    "properties": {
                        "simulation_duration": {"type": "number"}
                    }
                }
            },
            "required": ["metadata", "simulation_parameters"]
        }

        schema_config = DataLoader(
            name="schema_validation",
            type=DataLoaderType.STATIC,
            source=json_file_path,
            format_options={"schema": schema}
        )

        schema_loader = JSONLoader(schema_config)
        schema_data = schema_loader.load()
        validation_result = schema_loader.validate_schema()

        print(f"   Schema validation result: {'PASSED' if validation_result['valid'] else 'FAILED'}")
        if validation_result['errors']:
            print("   Errors:", validation_result['errors'])
        if validation_result['warnings']:
            print("   Warnings:", validation_result['warnings'])
        print()

        # 6. Data structure analysis
        print("6. Data structure analysis:")
        analysis_loader = JSONLoader(basic_config)
        analysis_data = analysis_loader.load()
        data_info = analysis_loader.get_data_info()

        print(f"   Data type: {data_info['type']}")
        print(f"   Memory usage: {data_info['size_info']['memory_bytes']} bytes")
        print(f"   Number of top-level keys: {data_info['size_info']['num_keys']}")
        print(f"   JSON representation length: {data_info['size_info']['json_length']} characters")
        print()

        print("=== Demo completed successfully! ===")

    finally:
        # Cleanup
        Path(json_file_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()