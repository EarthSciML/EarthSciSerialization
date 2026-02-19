#!/usr/bin/env python3
"""Integration test for all data loaders (CSV, Gridded, Callback)."""

import sys
import os
import tempfile
import numpy as np
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

def test_data_loader_integration():
    """Test that all data loaders can be used together."""
    try:
        from esm_format import (
            DataLoader, DataLoaderType,
            # Try to import all available loaders
        )

        # Check what loaders are available
        available_loaders = []

        # Test CSV loader availability
        try:
            from esm_format import CSVLoader, load_csv_data
            available_loaders.append('CSV')
        except ImportError:
            print("⚠ CSV loader not available (pandas issues)")

        # Test Gridded loader availability
        try:
            from esm_format import GriddedDataLoader, load_gridded_data
            available_loaders.append('Gridded')
        except ImportError:
            print("⚠ Gridded loader not available")

        # Test Callback loader availability
        try:
            from esm_format import CallbackLoader, load_callback_data, CallbackDataSource
            available_loaders.append('Callback')
        except ImportError:
            print("⚠ Callback loader not available")

        print(f"Available loaders: {', '.join(available_loaders)}")
        assert len(available_loaders) >= 2, "At least 2 loaders should be available"

        return True

    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gridded_and_callback_combination():
    """Test using gridded and callback loaders in combination."""
    try:
        from esm_format import (
            DataLoader, DataLoaderType,
            GriddedDataLoader, CallbackLoader, CallbackDataSource,
            load_gridded_data, load_callback_data
        )

        # Create test binary gridded data
        test_gridded_data = np.random.random((4, 4)).astype(np.float32)

        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as f:
            test_gridded_data.tofile(f.name)
            temp_gridded_file = f.name

        # Create callback that processes gridded data
        def process_gridded_callback(gridded_file=None, variables=None, **kwargs):
            """Callback that loads and processes gridded data."""
            if gridded_file is None:
                return {'error': 'No gridded file specified'}

            # Load gridded data using the gridded loader
            gridded_loader_config = DataLoader(
                name="internal_gridded",
                type=DataLoaderType.GRIDDED_DATA,
                source=gridded_file,
                format_options={
                    'format': 'binary',
                    'dtype': np.float32,
                    'shape': (4, 4)
                }
            )

            gridded_result = load_gridded_data(gridded_loader_config)
            data = gridded_result['data']

            # Process the data
            result = {
                'original_data': data.tolist(),
                'mean': float(np.mean(data)),
                'max': float(np.max(data)),
                'min': float(np.min(data)),
                'shape': data.shape,
                'processed_variables': variables or ['processed_data']
            }

            return result

        try:
            # Test 1: Direct gridded data loading
            gridded_loader = DataLoader(
                name="test_gridded_direct",
                type=DataLoaderType.GRIDDED_DATA,
                source=temp_gridded_file,
                format_options={
                    'format': 'binary',
                    'dtype': np.float32,
                    'shape': (4, 4)
                }
            )

            gridded_result = load_gridded_data(gridded_loader)
            assert 'data' in gridded_result
            assert gridded_result['data'].shape == (4, 4)
            print("✓ Direct gridded data loading successful")

            # Test 2: Callback that processes gridded data
            callback_loader = DataLoader(
                name="test_callback_processing",
                type=DataLoaderType.CALLBACK,
                source=process_gridded_callback,
                variables=['mean', 'max', 'min'],
                format_options={
                    'callback_args': {
                        'gridded_file': temp_gridded_file
                    }
                }
            )

            callback_result = load_callback_data(callback_loader)
            assert 'mean' in callback_result
            assert 'max' in callback_result
            assert 'min' in callback_result
            assert 'original_data' in callback_result
            assert callback_result['shape'] == (4, 4)
            print("✓ Callback processing of gridded data successful")

            # Test 3: Multiple data sources
            loaders = [
                # Gridded data
                DataLoader(
                    name="meteorology",
                    type=DataLoaderType.GRIDDED_DATA,
                    source=temp_gridded_file,
                    format_options={'format': 'binary', 'dtype': np.float32, 'shape': (4, 4)}
                ),
                # Callback for synthetic time series
                DataLoader(
                    name="emissions",
                    type=DataLoaderType.CALLBACK,
                    source=CallbackDataSource.create_time_series_data(0.0, 24.0, 25),
                    variables=['time', 'co2_emissions', 'nox_emissions']
                ),
                # Callback for constants
                DataLoader(
                    name="parameters",
                    type=DataLoaderType.CALLBACK,
                    source=CallbackDataSource.create_constant_data({
                        'temperature_scale': 1.0,
                        'pressure_offset': 0.0,
                        'model_version': '1.0'
                    })
                )
            ]

            results = {}
            for loader in loaders:
                if loader.type == DataLoaderType.GRIDDED_DATA:
                    results[loader.name] = load_gridded_data(loader)
                elif loader.type == DataLoaderType.CALLBACK:
                    results[loader.name] = load_callback_data(loader)

            # Validate all results
            assert 'meteorology' in results
            assert 'emissions' in results
            assert 'parameters' in results
            assert results['meteorology']['data'].shape == (4, 4)
            assert 'time' in results['emissions']
            assert 'model_version' in results['parameters']

            print("✓ Multiple data source integration successful")
            return True

        finally:
            os.unlink(temp_gridded_file)

    except Exception as e:
        print(f"✗ Gridded and callback combination test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling_consistency():
    """Test that error handling is consistent across loaders."""
    try:
        from esm_format import (
            DataLoader, DataLoaderType,
            GriddedDataLoader, CallbackLoader,
            GriddedValidationError, CallbackValidationError
        )

        # Test 1: Wrong type for gridded loader
        wrong_gridded = DataLoader(
            name="wrong_type",
            type=DataLoaderType.CALLBACK,
            source="test.nc"
        )

        try:
            GriddedDataLoader(wrong_gridded)
            assert False, "Should raise ValueError"
        except ValueError:
            pass

        # Test 2: Wrong type for callback loader
        wrong_callback = DataLoader(
            name="wrong_type",
            type=DataLoaderType.GRIDDED_DATA,
            source=lambda: {}
        )

        try:
            CallbackLoader(wrong_callback)
            assert False, "Should raise ValueError"
        except ValueError:
            pass

        # Test 3: File not found for gridded loader
        missing_gridded = DataLoader(
            name="missing_file",
            type=DataLoaderType.GRIDDED_DATA,
            source="nonexistent.nc"
        )

        try:
            GriddedDataLoader(missing_gridded).load()
            assert False, "Should raise FileNotFoundError"
        except FileNotFoundError:
            pass

        print("✓ Error handling consistency test passed")
        return True

    except Exception as e:
        print(f"✗ Error handling consistency test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_tests():
    """Run all integration tests."""
    tests = [
        test_data_loader_integration,
        test_gridded_and_callback_combination,
        test_error_handling_consistency,
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

    print(f"\nData Loaders Integration Tests: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)