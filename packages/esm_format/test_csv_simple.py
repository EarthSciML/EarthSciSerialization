#!/usr/bin/env python3
"""Simple integration test for CSV loader."""

import sys
import tempfile
import os

# Add src to path
sys.path.insert(0, 'src')

def test_csv_simple():
    """Simple test of CSV loader integration."""
    # Test imports work correctly from main package
    from esm_format import (
        CSVLoader, CSVValidationError, load_csv_data,
        DataLoader, DataLoaderType
    )

    print("✓ CSV imports successful")

    # Create test CSV
    csv_content = """time,NO2,O3,temperature
0.0,15.2,35.8,298.15
3600.0,18.5,42.1,299.20
7200.0,22.1,38.9,301.50"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        temp_csv = f.name

    try:
        # Create and test DataLoader
        data_loader = DataLoader(
            name="test_data",
            type=DataLoaderType.EMISSIONS,
            source=temp_csv,
            format_options={
                'column_types': {
                    'time': 'float',
                    'NO2': 'float',
                    'O3': 'float',
                    'temperature': 'float'
                }
            }
        )

        # Test loading
        df = load_csv_data(data_loader)

        assert not df.empty, "DataFrame should not be empty"
        assert len(df) == 3, f"Expected 3 rows, got {len(df)}"
        assert len(df.columns) == 4, f"Expected 4 columns, got {len(df.columns)}"
        assert 'time' in df.columns
        assert 'NO2' in df.columns
        assert 'O3' in df.columns
        assert 'temperature' in df.columns

        # Check data types and values
        assert df.dtypes['time'] in ['float64', 'Float64'], f"time column type: {df.dtypes['time']}"
        assert df.iloc[0]['time'] == 0.0
        assert df.iloc[0]['NO2'] == 15.2
        assert df.iloc[1]['time'] == 3600.0

        print("✓ CSV data loading and validation successful")

        # Test error handling
        try:
            bad_loader = DataLoader(
                name="bad_data",
                type=DataLoaderType.EMISSIONS,
                source="nonexistent_file.csv"
            )
            load_csv_data(bad_loader)
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            print("✓ Error handling works correctly")

        print("\n✅ All CSV functionality tests passed!")
        return True

    finally:
        os.unlink(temp_csv)

if __name__ == "__main__":
    try:
        test_csv_simple()
    except Exception as e:
        print(f"\n❌ CSV test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)