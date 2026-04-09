#!/usr/bin/env python3
"""Test the Gridded data loader implementation."""

import sys
import os
import tempfile
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def test_gridded_loader_import():
    """Test that gridded loader can be imported."""
    try:
        from esm_format import GriddedDataLoader, DataLoader, DataLoaderType, GriddedValidationError
        print("✓ Gridded loader imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_gridded_loader_validation():
    """Test gridded loader validation."""
    try:
        from esm_format import GriddedDataLoader, DataLoader, DataLoaderType

        # Test wrong data type validation
        wrong_loader = DataLoader(
            name="test_wrong",
            type=DataLoaderType.EMISSIONS,  # Wrong type for gridded loader
            source="test.nc"
        )

        try:
            loader = GriddedDataLoader(wrong_loader)
            assert False, "Should have raised ValueError for wrong type"
        except ValueError as e:
            assert "Gridded loader only supports GRIDDED_DATA type" in str(e)
            print("✓ Data type validation test passed")

        # Test file not found
        missing_loader = DataLoader(
            name="test_missing",
            type=DataLoaderType.GRIDDED_DATA,
            source="nonexistent_file.nc"
        )

        loader = GriddedDataLoader(missing_loader)
        try:
            loader.load()
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            print("✓ Missing file error test passed")

        return True
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_binary_gridded_data():
    """Test loading binary gridded data."""
    try:
        from esm_format import GriddedDataLoader, DataLoader, DataLoaderType

        # Create test binary data
        test_data = np.random.random((10, 20)).astype(np.float32)

        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            test_data.tofile(f.name)
            temp_file = f.name

        try:
            # Create loader for binary data
            data_loader = DataLoader(
                name="test_binary",
                type=DataLoaderType.GRIDDED_DATA,
                source=temp_file,
                format_options={
                    'format': 'binary',
                    'dtype': np.float32,
                    'shape': (10, 20)
                }
            )

            loader = GriddedDataLoader(data_loader)
            result = loader.load()

            # Validate results
            assert 'data' in result, "Result should contain 'data' key"
            assert result['type'] == 'numpy_array', "Should be numpy_array type"
            assert result['shape'] == (10, 20), f"Expected shape (10, 20), got {result['shape']}"
            assert np.allclose(result['data'], test_data), "Data should match original"

            print("✓ Binary gridded data test passed")
            return True

        finally:
            os.unlink(temp_file)

    except Exception as e:
        print(f"✗ Binary gridded data test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_text_gridded_data():
    """Test loading text-based gridded data."""
    try:
        from esm_format import GriddedDataLoader, DataLoader, DataLoaderType

        # Create test text data
        text_content = """# Test grid data
1.0 2.0 3.0 4.0
5.0 6.0 7.0 8.0
9.0 10.0 11.0 12.0"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(text_content)
            temp_file = f.name

        try:
            # Create loader for text data
            data_loader = DataLoader(
                name="test_text",
                type=DataLoaderType.GRIDDED_DATA,
                source=temp_file,
                format_options={
                    'format': 'text',
                    'skip_lines': 1  # Skip header
                }
            )

            loader = GriddedDataLoader(data_loader)
            result = loader.load()

            # Validate results
            assert 'data' in result, "Result should contain 'data' key"
            assert result['type'] == 'numpy_array', "Should be numpy_array type"
            assert result['shape'] == (3, 4), f"Expected shape (3, 4), got {result['shape']}"

            expected_data = np.array([
                [1.0, 2.0, 3.0, 4.0],
                [5.0, 6.0, 7.0, 8.0],
                [9.0, 10.0, 11.0, 12.0]
            ])

            assert np.allclose(result['data'], expected_data), "Data should match expected values"

            print("✓ Text gridded data test passed")
            return True

        finally:
            os.unlink(temp_file)

    except Exception as e:
        print(f"✗ Text gridded data test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_convenience_function():
    """Test the convenience function."""
    try:
        from esm_format import load_gridded_data, DataLoader, DataLoaderType

        # Create test binary data
        test_data = np.random.random((5, 5)).astype(np.float64)

        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            test_data.tofile(f.name)
            temp_file = f.name

        try:
            # Create loader configuration
            data_loader = DataLoader(
                name="test_convenience",
                type=DataLoaderType.GRIDDED_DATA,
                source=temp_file,
                format_options={
                    'format': 'binary',
                    'dtype': np.float64,
                    'shape': (5, 5)
                }
            )

            # Test convenience function
            result = load_gridded_data(data_loader)

            assert 'data' in result, "Result should contain 'data' key"
            assert np.allclose(result['data'], test_data), "Data should match original"

            print("✓ Convenience function test passed")
            return True

        finally:
            os.unlink(temp_file)

    except Exception as e:
        print(f"✗ Convenience function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_tests():
    """Run all gridded loader tests."""
    tests = [
        test_gridded_loader_import,
        test_gridded_loader_validation,
        test_binary_gridded_data,
        test_text_gridded_data,
        test_convenience_function,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\nGridded Loader Tests: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)