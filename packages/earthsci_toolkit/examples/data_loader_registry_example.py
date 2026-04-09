"""
Example usage of the ESM Format data loader registry system.

This example demonstrates how to use the data loader registry for:
1. Automatic loader detection and creation
2. Manual loader registration
3. Loader chains and plugin discovery
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any

from esm_format import (
    DataLoader,
    DataLoaderType,
    get_registry,
    register_loader,
    create_auto_loader,
    detect_loader_type
)


def main():
    """Demonstrate data loader registry functionality."""

    # Create some sample data files for demonstration
    setup_sample_files()

    print("=== ESM Format Data Loader Registry Example ===\n")

    # 1. Show built-in loaders
    demonstrate_builtin_loaders()

    # 2. Automatic loader detection
    demonstrate_auto_detection()

    # 3. Custom loader registration
    demonstrate_custom_loader()

    # 4. Loader chains
    demonstrate_loader_chains()

    # 5. Registry inspection
    demonstrate_registry_inspection()


def setup_sample_files():
    """Create sample data files for demonstration."""

    # Create a sample JSON file
    sample_data = {
        "metadata": {
            "title": "Sample Climate Data",
            "author": "Registry Example",
            "version": "1.0"
        },
        "variables": {
            "temperature": {
                "units": "K",
                "values": [273.15, 274.15, 275.15, 276.15, 277.15]
            },
            "pressure": {
                "units": "Pa",
                "values": [101325, 101320, 101315, 101310, 101305]
            }
        }
    }

    json_file = Path("sample_climate.json")
    with open(json_file, 'w') as f:
        json.dump(sample_data, f, indent=2)

    print(f"Created sample file: {json_file}")


def demonstrate_builtin_loaders():
    """Show the built-in loaders registered by default."""
    print("1. Built-in Loaders")
    print("==================")

    registry = get_registry()
    loaders = registry.list_registered_loaders()

    for loader_type, info in loaders.items():
        print(f"Type: {loader_type.value}")
        print(f"  Class: {info['class_name']}")
        print(f"  Extensions: {info['extensions']}")
        print(f"  MIME types: {info['mime_types']}")
        print()


def demonstrate_auto_detection():
    """Demonstrate automatic loader type detection and creation."""
    print("2. Automatic Loader Detection")
    print("=============================")

    # Detect loader type by extension
    json_type = detect_loader_type("sample_climate.json")
    print(f"Detected type for 'sample_climate.json': {json_type}")

    # Create loader automatically
    try:
        auto_loader = create_auto_loader(
            name="auto_climate",
            source="sample_climate.json",
            variables=["metadata", "variables"]
        )

        print(f"Created auto loader: {type(auto_loader).__name__}")

        # Load and show some data
        data = auto_loader.load()
        print(f"Loaded data keys: {list(data.keys())}")
        print(f"Sample metadata: {data.get('metadata', {}).get('title')}")

    except FileNotFoundError:
        print("Sample file not found - skipping auto loader demo")

    print()


def demonstrate_custom_loader():
    """Show how to register a custom loader."""
    print("3. Custom Loader Registration")
    print("=============================")

    # Define a simple CSV loader class
    class SimpleCSVLoader:
        """Simple CSV loader for demonstration."""

        def __init__(self, data_loader: DataLoader):
            if data_loader.type != DataLoaderType.EMISSIONS:
                raise ValueError(f"Expected CSV type, got {data_loader.type}")
            self.config = data_loader

        def load(self):
            """Load CSV data (simplified implementation)."""
            print(f"Loading CSV from: {self.config.source}")
            # In a real implementation, this would parse CSV data
            return {
                "loader_type": "csv",
                "source": self.config.source,
                "variables": self.config.variables,
                "mock_data": [["col1", "col2"], ["val1", "val2"]]
            }

    # Register the custom loader
    register_loader(
        DataLoaderType.EMISSIONS,
        SimpleCSVLoader,
        extensions=['.csv', '.tsv'],
        mime_types=['text/csv', 'text/tab-separated-values']
    )

    print("Registered SimpleCSVLoader for CSV files")

    # Create and use the custom loader
    csv_config = DataLoader(
        name="test_csv",
        type=DataLoaderType.EMISSIONS,
        source="test.csv",
        variables=["column1", "column2"]
    )

    csv_loader = get_registry().create_loader(csv_config)
    result = csv_loader.load()
    print(f"CSV loader result: {result}")
    print()


def demonstrate_loader_chains():
    """Show loader chain functionality."""
    print("4. Loader Chains")
    print("===============")

    registry = get_registry()

    # Register a loader chain
    chain = [DataLoaderType.STATIC, DataLoaderType.EMISSIONS]
    registry.register_loader_chain("json_to_csv", chain)

    print("Registered loader chain: json_to_csv")
    print(f"Chain steps: {[step.value for step in chain]}")

    # Retrieve the chain
    retrieved_chain = registry.get_loader_chain("json_to_csv")
    print(f"Retrieved chain: {[step.value for step in retrieved_chain]}")
    print()


def demonstrate_registry_inspection():
    """Show registry inspection capabilities."""
    print("5. Registry Inspection")
    print("=====================")

    registry = get_registry()

    # List all registered loaders
    loaders = registry.list_registered_loaders()
    print(f"Total registered loaders: {len(loaders)}")

    for loader_type in loaders:
        print(f"- {loader_type.value}")

    print()

    # Test extension detection
    test_files = [
        "data.json",
        "climate.nc",
        "measurements.csv",
        "unknown.xyz"
    ]

    print("File type detection:")
    for file_name in test_files:
        detected = registry.detect_loader_type(file_name)
        status = detected.value if detected else "Unknown"
        print(f"  {file_name} -> {status}")

    print()


def cleanup():
    """Clean up sample files."""
    sample_files = ["sample_climate.json"]

    for filename in sample_files:
        path = Path(filename)
        if path.exists():
            path.unlink()
            print(f"Cleaned up: {filename}")


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup()