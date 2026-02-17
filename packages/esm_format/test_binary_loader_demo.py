#!/usr/bin/env python3
"""
Demo script showing BinaryLoader functionality for legacy scientific data formats.
"""

import tempfile
import struct
from pathlib import Path
from esm_format import DataLoader, DataLoaderType, BinaryLoader


def create_sample_weather_data():
    """Create a sample binary weather data file."""
    with tempfile.NamedTemporaryFile(suffix='.dat', delete=False) as f:
        # Header: Magic number (4 bytes) + record count (4 bytes)
        f.write(b'WXDT')  # Magic
        f.write(struct.pack('<I', 3))  # 3 records

        # Weather records: timestamp (8), temp (4), pressure (4), humidity (4)
        records = [
            (1645123200, 25.5, 1013.2, 65.0),  # 2022-02-17 12:00:00
            (1645126800, 26.1, 1012.8, 62.0),  # 2022-02-17 13:00:00
            (1645130400, 24.8, 1014.1, 68.0),  # 2022-02-17 14:00:00
        ]

        for timestamp, temp, pressure, humidity in records:
            f.write(struct.pack('<Qfff', timestamp, temp, pressure, humidity))

        return Path(f.name)


def demo_struct_format_loading():
    """Demonstrate loading with struct format."""
    print("=== Demo: Struct Format Loading ===")

    weather_file = create_sample_weather_data()

    try:
        config = DataLoader(
            name="weather_station",
            type=DataLoaderType.BINARY,
            source=str(weather_file),
            format_options={
                'header_size': 8,  # Skip magic + count
                'struct_format': 'Qfff',  # uint64, float32, float32, float32
                'field_names': ['timestamp', 'temperature', 'pressure', 'humidity'],
                'record_size': 20,  # 8 + 4 + 4 + 4 = 20 bytes per record
                'endianness': 'little'
            }
        )

        loader = BinaryLoader(config)
        data = loader.load()

        print(f"Loaded {data['record_count']} weather records:")
        for i, record in enumerate(data['records']):
            print(f"  Record {i+1}: {record}")

        # Get file info
        info = loader.get_file_info()
        print(f"\nFile info: {info['file_size_bytes']} bytes, format: {info['format_type']}")

        loader.close()

    finally:
        weather_file.unlink()  # Clean up


def demo_custom_format_loading():
    """Demonstrate loading with custom format specification."""
    print("\n=== Demo: Custom Format Loading ===")

    # Create a binary file with mixed data types
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        # Scientific instrument data: ID (2), flags (1), data_count (4), values (4*3)
        f.write(struct.pack('<HBI', 0x1234, 0xFF, 3))  # ID, flags, count
        f.write(struct.pack('<fff', 1.23, 4.56, 7.89))  # Float data

        custom_file = Path(f.name)

    try:
        config = DataLoader(
            name="instrument_data",
            type=DataLoaderType.BINARY,
            source=str(custom_file),
            format_options={
                'endianness': 'little',
                'custom_format': {
                    'instrument_id': {'type': 'uint16', 'count': 1, 'offset': 0},
                    'status_flags': {'type': 'uint8', 'count': 1, 'offset': 2},
                    'sample_count': {'type': 'uint32', 'count': 1, 'offset': 3},
                    'measurements': {'type': 'float32', 'count': 3, 'offset': 7}
                }
            }
        )

        loader = BinaryLoader(config)
        data = loader.load()

        print("Loaded instrument data:")
        print(f"  Instrument ID: 0x{data['instrument_id']:04X}")
        print(f"  Status flags: 0x{data['status_flags']:02X}")
        print(f"  Sample count: {data['sample_count']}")
        print(f"  Measurements: {data['measurements']}")

        # Validate format
        validation = loader.validate_format()
        print(f"\nFormat validation: {'PASS' if validation['valid'] else 'FAIL'}")

        # Export to numpy
        numpy_data = loader.export_to_numpy()
        print(f"NumPy export available: {list(numpy_data.keys())}")

        loader.close()

    finally:
        custom_file.unlink()


def demo_endianness_handling():
    """Demonstrate endianness handling."""
    print("\n=== Demo: Endianness Handling ===")

    # Create data with known byte pattern
    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
        # Write 0x1234 in little endian (0x34, 0x12)
        f.write(struct.pack('<H', 0x1234))
        endian_file = Path(f.name)

    try:
        # Read as little endian
        config_little = DataLoader(
            name="little_endian_test",
            type=DataLoaderType.BINARY,
            source=str(endian_file),
            format_options={
                'endianness': 'little',
                'data_types': {'value': 'uint16'}
            }
        )

        loader_little = BinaryLoader(config_little)
        data_little = loader_little.load()
        loader_little.close()

        # Read as big endian
        config_big = DataLoader(
            name="big_endian_test",
            type=DataLoaderType.BINARY,
            source=str(endian_file),
            format_options={
                'endianness': 'big',
                'data_types': {'value': 'uint16'}
            }
        )

        loader_big = BinaryLoader(config_big)
        data_big = loader_big.load()
        loader_big.close()

        print("Endianness comparison:")
        print(f"  Little endian: {data_little['value']} (0x{data_little['value']:04X})")
        print(f"  Big endian: {data_big['value']} (0x{data_big['value']:04X})")

    finally:
        endian_file.unlink()


def main():
    """Run all demos."""
    print("Binary Data Loader Demo")
    print("=======================")
    print("Demonstrating binary data loader for legacy scientific data formats...")

    demo_struct_format_loading()
    demo_custom_format_loading()
    demo_endianness_handling()

    print("\n✓ All demos completed successfully!")
    print("\nThe BinaryLoader supports:")
    print("  • Custom binary format specifications")
    print("  • Endianness handling (little/big/native)")
    print("  • Struct unpacking with field names")
    print("  • Multiple data types (int8-64, uint8-64, float32/64, bool, char)")
    print("  • Header skipping and record-based data")
    print("  • Format validation and metadata extraction")
    print("  • NumPy array export")


if __name__ == "__main__":
    main()