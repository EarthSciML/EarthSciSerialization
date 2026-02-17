#!/usr/bin/env python3
"""
Example of using the RemoteLoader for accessing remote data sources.

This example demonstrates:
- Loading data from HTTP/HTTPS URLs
- Using authentication
- Caching configuration
- Progress tracking
- Error handling and retries
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from esm_format.types import DataLoader, DataLoaderType
from esm_format.data_loaders import RemoteLoader
from esm_format.data_loader_registry import create_data_loader, detect_loader_type


def progress_callback(progress, downloaded, total):
    """Progress callback for download tracking."""
    if total:
        percent = progress * 100
        mb_downloaded = downloaded / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        print(f"\rDownloading: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="")
    else:
        kb_downloaded = downloaded / 1024
        print(f"\rDownloading: {kb_downloaded:.1f} KB", end="")


def example_basic_http():
    """Example: Basic HTTP data loading."""
    print("=== Basic HTTP Data Loading ===")

    # Example with a public JSON API (httpbin.org provides testing endpoints)
    url = "https://httpbin.org/json"

    # Auto-detect loader type from URL
    loader_type = detect_loader_type(url)
    print(f"Detected loader type: {loader_type}")

    # Create data loader configuration
    data_loader = DataLoader(
        name="httpbin_test",
        type=DataLoaderType.REMOTE,
        source=url,
        format_options={
            "enable_cache": True,
            "cache_ttl": 300,  # 5 minutes
            "max_retries": 3,
            "retry_delay": 1.0
        }
    )

    # Create loader instance
    loader = RemoteLoader(data_loader)

    # Validate source before loading
    print("Validating source...")
    validation = loader.validate_source()
    if validation["valid"]:
        print(f"✓ Source is valid (status: {validation['status_code']})")
        print(f"  Content-Type: {validation['content_type']}")
    else:
        print(f"✗ Source validation failed: {validation['error']}")
        return

    # Load data
    print("Loading data...")
    try:
        data = loader.load_data()
        print(f"✓ Data loaded successfully")
        print(f"  Data type: {type(data)}")
        if isinstance(data, dict):
            print(f"  Keys: {list(data.keys())}")

            # Print remote metadata if available
            if '_remote_metadata' in data:
                metadata = data['_remote_metadata']
                print(f"  Original source: {metadata['original_source']}")
                print(f"  Protocol: {metadata['protocol']}")
                print(f"  File type: {metadata['file_type']}")

    except Exception as e:
        print(f"✗ Failed to load data: {e}")

    # Show cache information
    cache_info = loader.get_cache_info()
    if cache_info["cache_enabled"]:
        print(f"Cache status: {'cached' if cache_info['cached'] else 'not cached'}")
        if cache_info["cached"]:
            print(f"  Cache size: {cache_info['cache_size']} bytes")
            print(f"  Valid: {cache_info['cache_valid']}")


def example_authenticated_api():
    """Example: Authenticated API access."""
    print("\n=== Authenticated API Access ===")

    # Example with Bearer token authentication
    url = "https://httpbin.org/bearer"

    data_loader = DataLoader(
        name="authenticated_test",
        type=DataLoaderType.REMOTE,
        source=url,
        format_options={
            "auth_token": "test_token_123",
            "enable_cache": False,  # Don't cache authenticated requests
            "max_retries": 2
        }
    )

    loader = RemoteLoader(data_loader)

    # Validate with authentication
    print("Validating authenticated source...")
    validation = loader.validate_source()
    if validation["valid"]:
        print(f"✓ Authenticated source is valid")
    else:
        print(f"✗ Authentication failed: {validation['error']}")
        # Note: httpbin.org/bearer requires a specific token, so this may fail
        print("  (This is expected for the demo - httpbin requires specific token)")


def example_basic_auth():
    """Example: Basic authentication."""
    print("\n=== Basic Authentication ===")

    url = "https://httpbin.org/basic-auth/user/pass"

    data_loader = DataLoader(
        name="basic_auth_test",
        type=DataLoaderType.REMOTE,
        source=url,
        format_options={
            "username": "user",
            "password": "pass",
            "enable_cache": False
        }
    )

    loader = RemoteLoader(data_loader)

    print("Validating basic auth source...")
    validation = loader.validate_source()
    if validation["valid"]:
        print(f"✓ Basic auth successful")
    else:
        print(f"✗ Basic auth failed: {validation['error']}")


def example_progress_tracking():
    """Example: Download with progress tracking."""
    print("\n=== Progress Tracking Example ===")

    # Use a larger file for progress demonstration
    url = "https://httpbin.org/bytes/1048576"  # 1MB of random data

    data_loader = DataLoader(
        name="progress_test",
        type=DataLoaderType.REMOTE,
        source=url,
        format_options={
            "progress_callback": progress_callback,
            "enable_cache": False
        }
    )

    loader = RemoteLoader(data_loader)

    print("Downloading with progress tracking...")
    try:
        data = loader.load_data()
        print(f"\n✓ Downloaded {len(data.get('data', [])) if isinstance(data, dict) else len(str(data))} bytes")
    except Exception as e:
        print(f"\n✗ Download failed: {e}")


def example_cache_management():
    """Example: Cache management."""
    print("\n=== Cache Management ===")

    url = "https://httpbin.org/json"

    data_loader = DataLoader(
        name="cache_test",
        type=DataLoaderType.REMOTE,
        source=url,
        format_options={
            "enable_cache": True,
            "cache_ttl": 10  # Very short TTL for demo
        }
    )

    loader = RemoteLoader(data_loader)

    # First load - should download and cache
    print("First load (will cache)...")
    loader.load_data()

    cache_info = loader.get_cache_info()
    print(f"Cache info after first load:")
    print(f"  Cached: {cache_info['cached']}")
    print(f"  Valid: {cache_info['cache_valid']}")

    # Second load - should use cache
    print("Second load (should use cache)...")
    loader.load_data()

    # Clear cache
    print("Clearing cache...")
    cleared = loader.clear_cache()
    print(f"Cache cleared: {cleared}")

    cache_info = loader.get_cache_info()
    print(f"Cache info after clearing:")
    print(f"  Cached: {cache_info['cached']}")


def example_error_handling():
    """Example: Error handling and retries."""
    print("\n=== Error Handling and Retries ===")

    # Use a non-existent URL to demonstrate error handling
    url = "https://httpbin.org/status/404"

    data_loader = DataLoader(
        name="error_test",
        type=DataLoaderType.REMOTE,
        source=url,
        format_options={
            "max_retries": 2,
            "retry_delay": 0.5,
            "backoff_factor": 2.0
        }
    )

    loader = RemoteLoader(data_loader)

    print("Testing error handling with 404 URL...")
    try:
        validation = loader.validate_source()
        print(f"Validation result: {validation}")
    except Exception as e:
        print(f"Exception during validation: {e}")


def example_cloud_storage_urls():
    """Example: Cloud storage URL detection."""
    print("\n=== Cloud Storage URL Detection ===")

    cloud_urls = [
        "s3://my-bucket/data.json",
        "gs://my-bucket/data.csv",
        "azure://container/data.nc",
        "https://mybucket.s3.amazonaws.com/data.json"
    ]

    for url in cloud_urls:
        loader_type = detect_loader_type(url)
        print(f"{url} -> {loader_type}")

        # Create loader to show protocol detection
        if loader_type == DataLoaderType.REMOTE:
            data_loader = DataLoader(
                name="cloud_test",
                type=DataLoaderType.REMOTE,
                source=url
            )
            loader = RemoteLoader(data_loader)
            print(f"  Protocol: {loader.protocol}")


def main():
    """Run all examples."""
    print("Remote Data Loader Examples")
    print("=" * 40)

    try:
        example_basic_http()
        example_authenticated_api()
        example_basic_auth()
        example_progress_tracking()
        example_cache_management()
        example_error_handling()
        example_cloud_storage_urls()

    except KeyboardInterrupt:
        print("\nExamples interrupted by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 40)
    print("Examples completed!")


if __name__ == "__main__":
    main()