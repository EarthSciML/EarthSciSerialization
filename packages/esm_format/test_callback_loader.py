#!/usr/bin/env python3
"""Test the Callback data loader implementation."""

import sys
import os
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, 'src')

def sample_callback_function(variables=None, **kwargs):
    """Sample callback function for testing."""
    if variables is None:
        variables = ['temperature', 'pressure']

    result = {}
    for var in variables:
        if var == 'temperature':
            result[var] = [20.0, 21.0, 22.0, 23.0]
        elif var == 'pressure':
            result[var] = [1013.0, 1014.0, 1015.0, 1016.0]
        else:
            result[var] = [0.0, 1.0, 2.0, 3.0]

    return result

def test_callback_loader_import():
    """Test that callback loader can be imported."""
    try:
        from esm_format import CallbackLoader, DataLoader, DataLoaderType, CallbackValidationError, CallbackDataSource
        print("✓ Callback loader imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_callback_loader_validation():
    """Test callback loader validation."""
    try:
        from esm_format import CallbackLoader, DataLoader, DataLoaderType

        # Test wrong data type validation
        wrong_loader = DataLoader(
            name="test_wrong",
            type=DataLoaderType.EMISSIONS,  # Wrong type for callback loader
            source=lambda: {}
        )

        try:
            loader = CallbackLoader(wrong_loader)
            assert False, "Should have raised ValueError for wrong type"
        except ValueError as e:
            assert "Callback loader only supports CALLBACK type" in str(e)
            print("✓ Data type validation test passed")

        return True
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_callable_source():
    """Test loading data from callable source."""
    try:
        from esm_format import CallbackLoader, DataLoader, DataLoaderType

        # Create loader with callable source
        data_loader = DataLoader(
            name="test_callable",
            type=DataLoaderType.CALLBACK,
            source=sample_callback_function,
            variables=['temperature', 'pressure']
        )

        loader = CallbackLoader(data_loader)
        result = loader.load()

        # Validate results
        assert isinstance(result, dict), "Result should be a dictionary"
        assert 'temperature' in result, "Result should contain temperature"
        assert 'pressure' in result, "Result should contain pressure"
        assert result['temperature'] == [20.0, 21.0, 22.0, 23.0], "Temperature data should match"
        assert result['pressure'] == [1013.0, 1014.0, 1015.0, 1016.0], "Pressure data should match"

        print("✓ Callable source test passed")
        return True

    except Exception as e:
        print(f"✗ Callable source test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_callback_with_args():
    """Test callback with custom arguments."""
    try:
        from esm_format import CallbackLoader, DataLoader, DataLoaderType

        def custom_callback(multiplier=1, offset=0, variables=None, **kwargs):
            """Custom callback that accepts arguments."""
            base_values = [1.0, 2.0, 3.0, 4.0]
            result = {}
            for var in variables or ['data']:
                result[var] = [val * multiplier + offset for val in base_values]
            return result

        # Create loader with custom arguments
        data_loader = DataLoader(
            name="test_args",
            type=DataLoaderType.CALLBACK,
            source=custom_callback,
            variables=['data'],
            format_options={
                'callback_args': {
                    'multiplier': 2,
                    'offset': 10
                }
            }
        )

        loader = CallbackLoader(data_loader)
        result = loader.load()

        # Validate results
        expected_values = [12.0, 14.0, 16.0, 18.0]  # (1*2+10, 2*2+10, 3*2+10, 4*2+10)
        assert result['data'] == expected_values, f"Expected {expected_values}, got {result['data']}"

        print("✓ Callback with arguments test passed")
        return True

    except Exception as e:
        print(f"✗ Callback with arguments test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_callback_data_source_helpers():
    """Test CallbackDataSource helper methods."""
    try:
        from esm_format import CallbackLoader, CallbackDataSource, DataLoader, DataLoaderType

        # Test constant data source
        constant_callback = CallbackDataSource.create_constant_data({'value': 42})

        data_loader = DataLoader(
            name="test_constant",
            type=DataLoaderType.CALLBACK,
            source=constant_callback
        )

        loader = CallbackLoader(data_loader)
        result = loader.load()
        assert result == {'value': 42}, "Constant callback should return expected value"

        print("✓ Constant data source test passed")

        # Test random data source (if numpy available)
        try:
            import numpy as np
            random_callback = CallbackDataSource.create_random_data((3, 3))

            random_loader = DataLoader(
                name="test_random",
                type=DataLoaderType.CALLBACK,
                source=random_callback
            )

            random_loader_obj = CallbackLoader(random_loader)
            random_result = random_loader_obj.load()

            assert random_result.shape == (3, 3), "Random data should have correct shape"
            print("✓ Random data source test passed")

            # Test time series data source
            timeseries_callback = CallbackDataSource.create_time_series_data(0.0, 10.0, 11)

            ts_loader = DataLoader(
                name="test_timeseries",
                type=DataLoaderType.CALLBACK,
                source=timeseries_callback,
                variables=['time', 'data1', 'data2']
            )

            ts_loader_obj = CallbackLoader(ts_loader)
            ts_result = ts_loader_obj.load()

            assert 'time' in ts_result, "Time series should contain time"
            assert 'data1' in ts_result, "Time series should contain data1"
            assert 'data2' in ts_result, "Time series should contain data2"
            assert len(ts_result['time']) == 11, "Time series should have correct length"

            print("✓ Time series data source test passed")

        except ImportError:
            print("⚠ Numpy not available, skipping numpy-dependent tests")

        return True

    except Exception as e:
        print(f"✗ CallbackDataSource helpers test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_string_callback_resolution():
    """Test resolving callbacks from strings."""
    try:
        from esm_format import CallbackLoader, DataLoader, DataLoaderType

        # Test resolving builtin function
        data_loader = DataLoader(
            name="test_builtin",
            type=DataLoaderType.CALLBACK,
            source="len",  # builtin function
            format_options={
                'callback_args': {'obj': [1, 2, 3, 4, 5]},
                'globals': {'len': len}  # Provide len in globals
            }
        )

        loader = CallbackLoader(data_loader)
        result = loader.load()
        assert result == 5, "len([1,2,3,4,5]) should return 5"

        print("✓ String callback resolution test passed")
        return True

    except Exception as e:
        print(f"✗ String callback resolution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_convenience_function():
    """Test the convenience function."""
    try:
        from esm_format import load_callback_data, DataLoader, DataLoaderType

        # Create simple callback
        def simple_callback(**kwargs):
            return {'result': 'success'}

        data_loader = DataLoader(
            name="test_convenience",
            type=DataLoaderType.CALLBACK,
            source=simple_callback
        )

        # Test convenience function
        result = load_callback_data(data_loader)
        assert result == {'result': 'success'}, "Convenience function should return expected result"

        print("✓ Convenience function test passed")
        return True

    except Exception as e:
        print(f"✗ Convenience function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_tests():
    """Run all callback loader tests."""
    tests = [
        test_callback_loader_import,
        test_callback_loader_validation,
        test_callable_source,
        test_callback_with_args,
        test_callback_data_source_helpers,
        test_string_callback_resolution,
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

    print(f"\nCallback Loader Tests: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)