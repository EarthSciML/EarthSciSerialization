#!/usr/bin/env python3
"""Test the CSV loader implementation."""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def test_csv_loader():
    """Test basic CSV loading functionality."""
    from esm_format import CSVLoader, DataLoader, DataLoaderType, CSVValidationError, load_csv_data

    # Test with the sample data file
    sample_csv = Path("test_sample_data.csv")

    # Create DataLoader configuration
    data_loader = DataLoader(
        name="test_weather",
        type=DataLoaderType.EMISSIONS,
        source=str(sample_csv),
        format_options={
            'delimiter': ',',
            'header': 0,
        },
        variables=['time', 'temperature', 'humidity']
    )

    # Test loading
    loader = CSVLoader(data_loader)
    df = loader.load()

    # Validate results
    assert not df.empty, "DataFrame should not be empty"
    assert len(df.columns) == 3, f"Expected 3 columns, got {len(df.columns)}"
    assert 'time' in df.columns, "Missing 'time' column"
    assert 'temperature' in df.columns, "Missing 'temperature' column"
    assert 'humidity' in df.columns, "Missing 'humidity' column"
    assert len(df) == 5, f"Expected 5 rows, got {len(df)}"

    print("✓ Basic CSV loading test passed")

    # Test convenience function
    df2 = load_csv_data(data_loader)
    assert df.equals(df2), "Convenience function should return same result"
    print("✓ Convenience function test passed")

def test_csv_validation():
    """Test CSV validation features."""
    from esm_format import CSVLoader, DataLoader, DataLoaderType, CSVValidationError

    sample_csv = Path("test_sample_data.csv")

    # Test with column type validation
    data_loader = DataLoader(
        name="test_weather_typed",
        type=DataLoaderType.EMISSIONS,
        source=str(sample_csv),
        format_options={
            'column_types': {
                'time': 'float',
                'temperature': 'float',
                'humidity': 'float',
                'pressure': 'float'
            }
        }
    )

    loader = CSVLoader(data_loader)
    df = loader.load()
    assert not df.empty, "DataFrame should not be empty"
    print("✓ Column type validation test passed")

    # Test missing file error
    missing_loader = DataLoader(
        name="test_missing",
        type=DataLoaderType.EMISSIONS,
        source="nonexistent_file.csv"
    )

    try:
        loader = CSVLoader(missing_loader)
        loader.load()
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        print("✓ Missing file error test passed")

def test_csv_missing_values():
    """Test missing value handling."""
    from esm_format import CSVLoader, DataLoader, DataLoaderType

    # Create a CSV with missing values
    csv_content = """time,temperature,humidity,pressure
0.0,20.5,65.2,1013.25
1.0,,64.8,1013.20
2.0,21.5,,1013.15
3.0,22.0,63.5,
4.0,22.2,63.0,1013.05"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        temp_csv = f.name

    try:
        # Test fill_zero strategy
        data_loader = DataLoader(
            name="test_missing",
            type=DataLoaderType.EMISSIONS,
            source=temp_csv,
            format_options={
                'missing_value_strategy': 'fill_zero'
            }
        )

        loader = CSVLoader(data_loader)
        df = loader.load()

        # Check that missing values were filled with 0
        assert (df.fillna(0) == df).all().all(), "Missing values should be filled with 0"
        print("✓ Missing value handling test passed")

    finally:
        os.unlink(temp_csv)

def test_wrong_data_loader_type():
    """Test error handling for wrong DataLoader type."""
    from esm_format import CSVLoader, DataLoader, DataLoaderType

    # Try to create CSV loader with wrong type
    wrong_loader = DataLoader(
        name="test_wrong",
        type=DataLoaderType.CALLBACK,
        source="test.json"
    )

    try:
        loader = CSVLoader(wrong_loader)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "CSV loader supports" in str(e)
        print("✓ Wrong data loader type test passed")

def run_tests():
    """Run all CSV loader tests."""
    tests = [
        test_csv_loader,
        test_csv_validation,
        test_csv_missing_values,
        test_wrong_data_loader_type,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\nCSV Loader Tests: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)