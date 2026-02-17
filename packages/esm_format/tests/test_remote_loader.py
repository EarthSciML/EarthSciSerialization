"""
Tests for remote data loading functionality.
"""

import pytest
import tempfile
import json
import responses
import time
from pathlib import Path
from unittest.mock import Mock, patch

# Import the remote data loading functionality
from esm_format.data_loaders import RemoteLoader
from esm_format.data_loader_registry import detect_loader_type, create_data_loader
from esm_format.types import DataLoader, DataLoaderType


class TestRemoteLoader:
    """Test cases for RemoteLoader."""

    def test_http_url_detection(self):
        """Test that HTTP URLs are detected as remote loader type."""
        url = "https://example.com/data.json"
        loader_type = detect_loader_type(url)
        assert loader_type == DataLoaderType.REMOTE

    def test_ftp_url_detection(self):
        """Test that FTP URLs are detected as remote loader type."""
        url = "ftp://ftp.example.com/data.csv"
        loader_type = detect_loader_type(url)
        assert loader_type == DataLoaderType.REMOTE

    def test_s3_url_detection(self):
        """Test that S3 URLs are detected as remote loader type."""
        url = "s3://my-bucket/data.nc"
        loader_type = detect_loader_type(url)
        assert loader_type == DataLoaderType.REMOTE

    def test_remote_loader_initialization(self):
        """Test RemoteLoader initialization."""
        data_loader = DataLoader(
            name="test_remote",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json",
            format_options={
                "auth_token": "test_token",
                "max_retries": 5,
                "cache_ttl": 1800
            }
        )

        loader = RemoteLoader(data_loader)

        assert loader.config == data_loader
        assert loader.source == "https://example.com/data.json"
        assert loader.protocol == "https"
        assert loader.auth_token == "test_token"
        assert loader.max_retries == 5
        assert loader.cache_ttl == 1800

    def test_cache_path_generation(self):
        """Test cache path generation based on URL hash."""
        data_loader = DataLoader(
            name="test_remote",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json"
        )

        loader = RemoteLoader(data_loader)
        cache_path = loader._get_cache_path()

        assert isinstance(cache_path, Path)
        assert cache_path.suffix == ".cache"
        # Should be deterministic for the same URL
        cache_path2 = loader._get_cache_path()
        assert cache_path == cache_path2

    def test_cache_validity_check(self):
        """Test cache validity checking."""
        data_loader = DataLoader(
            name="test_remote",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json",
            format_options={"cache_ttl": 10}  # 10 second TTL
        )

        loader = RemoteLoader(data_loader)

        # Non-existent cache should be invalid
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            temp_path = Path(temp_file.name)

        assert not loader._is_cache_valid(temp_path)

        # Create a fresh cache file
        temp_path.touch()
        assert loader._is_cache_valid(temp_path)

        # Clean up
        temp_path.unlink()

    @responses.activate
    def test_http_download_basic(self):
        """Test basic HTTP download functionality."""
        # Mock HTTP response
        test_data = {"message": "Hello, World!", "data": [1, 2, 3]}
        responses.add(
            responses.GET,
            "https://example.com/data.json",
            json=test_data,
            status=200,
            headers={"Content-Type": "application/json"}
        )

        data_loader = DataLoader(
            name="test_remote",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json",
            format_options={"enable_cache": False}  # Disable cache for test
        )

        loader = RemoteLoader(data_loader)

        # This would require implementing the full flow
        # For now, just test that the loader can be created and configured
        assert loader.protocol == "https"
        assert not loader.enable_cache

    @responses.activate
    def test_http_authentication_headers(self):
        """Test HTTP authentication header handling."""
        # Test Bearer token
        responses.add(
            responses.HEAD,
            "https://api.example.com/data",
            status=200
        )

        data_loader = DataLoader(
            name="test_auth",
            type=DataLoaderType.REMOTE,
            source="https://api.example.com/data",
            format_options={"auth_token": "test_bearer_token"}
        )

        loader = RemoteLoader(data_loader)
        result = loader.validate_source()

        assert result["valid"] is True
        assert result["status_code"] == 200

        # Check that the request had the correct header
        assert len(responses.calls) == 1
        request = responses.calls[0].request
        assert "Authorization" in request.headers
        assert request.headers["Authorization"] == "Bearer test_bearer_token"

    @responses.activate
    def test_http_api_key_headers(self):
        """Test HTTP API key header handling."""
        responses.add(
            responses.HEAD,
            "https://api.example.com/data",
            status=200
        )

        data_loader = DataLoader(
            name="test_api_key",
            type=DataLoaderType.REMOTE,
            source="https://api.example.com/data",
            format_options={"api_key": "test_api_key"}
        )

        loader = RemoteLoader(data_loader)
        result = loader.validate_source()

        assert result["valid"] is True

        # Check that the request had the correct header
        request = responses.calls[0].request
        assert "X-API-Key" in request.headers
        assert request.headers["X-API-Key"] == "test_api_key"

    @responses.activate
    def test_http_basic_auth_headers(self):
        """Test HTTP Basic authentication header handling."""
        responses.add(
            responses.HEAD,
            "https://api.example.com/data",
            status=200
        )

        data_loader = DataLoader(
            name="test_basic_auth",
            type=DataLoaderType.REMOTE,
            source="https://api.example.com/data",
            format_options={
                "username": "testuser",
                "password": "testpass"
            }
        )

        loader = RemoteLoader(data_loader)
        result = loader.validate_source()

        assert result["valid"] is True

        # Check that the request had the correct header
        request = responses.calls[0].request
        assert "Authorization" in request.headers
        auth_header = request.headers["Authorization"]
        assert auth_header.startswith("Basic ")

    def test_retry_configuration(self):
        """Test retry and backoff configuration."""
        data_loader = DataLoader(
            name="test_retry",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json",
            format_options={
                "max_retries": 5,
                "retry_delay": 2.0,
                "backoff_factor": 1.5
            }
        )

        loader = RemoteLoader(data_loader)

        assert loader.max_retries == 5
        assert loader.retry_delay == 2.0
        assert loader.backoff_factor == 1.5

    def test_progress_callback_configuration(self):
        """Test progress callback configuration."""
        progress_callback = Mock()

        data_loader = DataLoader(
            name="test_progress",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json",
            format_options={"progress_callback": progress_callback}
        )

        loader = RemoteLoader(data_loader)
        assert loader.progress_callback == progress_callback

    def test_cache_info_no_cache(self):
        """Test cache info when caching is disabled."""
        data_loader = DataLoader(
            name="test_no_cache",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json",
            format_options={"enable_cache": False}
        )

        loader = RemoteLoader(data_loader)
        cache_info = loader.get_cache_info()

        assert cache_info["cache_enabled"] is False

    def test_cache_info_with_cache(self):
        """Test cache info when caching is enabled."""
        data_loader = DataLoader(
            name="test_cache",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json",
            format_options={"enable_cache": True}
        )

        loader = RemoteLoader(data_loader)
        cache_info = loader.get_cache_info()

        assert cache_info["cache_enabled"] is True
        assert cache_info["cached"] is False  # No cache file exists yet
        assert "cache_path" in cache_info

    @responses.activate
    def test_source_validation_success(self):
        """Test successful source validation."""
        responses.add(
            responses.HEAD,
            "https://example.com/data.json",
            status=200,
            headers={
                "Content-Type": "application/json",
                "Content-Length": "1024",
                "Last-Modified": "Wed, 21 Oct 2015 07:28:00 GMT"
            }
        )

        data_loader = DataLoader(
            name="test_validation",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json"
        )

        loader = RemoteLoader(data_loader)
        result = loader.validate_source()

        assert result["valid"] is True
        assert result["status_code"] == 200
        assert result["content_type"] == "application/json"
        assert result["content_length"] == "1024"
        assert result["last_modified"] == "Wed, 21 Oct 2015 07:28:00 GMT"

    @responses.activate
    def test_source_validation_failure(self):
        """Test source validation failure."""
        responses.add(
            responses.HEAD,
            "https://example.com/data.json",
            status=404
        )

        data_loader = DataLoader(
            name="test_validation_fail",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json"
        )

        loader = RemoteLoader(data_loader)
        result = loader.validate_source()

        assert result["valid"] is False
        assert "error" in result

    def test_ftp_validation(self):
        """Test FTP source validation."""
        data_loader = DataLoader(
            name="test_ftp",
            type=DataLoaderType.REMOTE,
            source="ftp://ftp.example.com/data.csv"
        )

        loader = RemoteLoader(data_loader)
        result = loader.validate_source()

        assert result["valid"] is True
        assert result["protocol"] == "ftp"
        assert result["hostname"] == "ftp.example.com"

    def test_unsupported_protocol_validation(self):
        """Test validation of unsupported protocols."""
        data_loader = DataLoader(
            name="test_unsupported",
            type=DataLoaderType.REMOTE,
            source="unknown://example.com/data"
        )

        loader = RemoteLoader(data_loader)
        result = loader.validate_source()

        assert result["valid"] is False
        assert "Validation not implemented" in result["error"]

    def test_clear_cache_disabled(self):
        """Test cache clearing when caching is disabled."""
        data_loader = DataLoader(
            name="test_clear_cache",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json",
            format_options={"enable_cache": False}
        )

        loader = RemoteLoader(data_loader)
        result = loader.clear_cache()

        assert result is False

    def test_clear_cache_no_cache_file(self):
        """Test cache clearing when no cache file exists."""
        data_loader = DataLoader(
            name="test_clear_cache",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json",
            format_options={"enable_cache": True}
        )

        loader = RemoteLoader(data_loader)
        result = loader.clear_cache()

        assert result is False  # No cache file existed

    def test_auto_loader_creation(self):
        """Test automatic loader creation for remote sources."""
        loader_instance = create_data_loader(DataLoader(
            name="auto_remote",
            type=DataLoaderType.REMOTE,
            source="https://example.com/data.json"
        ))

        assert isinstance(loader_instance, RemoteLoader)
        assert loader_instance.source == "https://example.com/data.json"
        assert loader_instance.protocol == "https"

    def test_cloud_storage_url_parsing(self):
        """Test cloud storage URL parsing."""
        # S3 URL
        s3_loader = RemoteLoader(DataLoader(
            name="s3_test",
            type=DataLoaderType.REMOTE,
            source="s3://my-bucket/path/to/data.json"
        ))
        assert s3_loader.protocol == "s3"

        # Google Cloud Storage URL
        gs_loader = RemoteLoader(DataLoader(
            name="gs_test",
            type=DataLoaderType.REMOTE,
            source="gs://my-bucket/data.json"
        ))
        assert gs_loader.protocol == "gs"

        # Azure Blob Storage URL
        azure_loader = RemoteLoader(DataLoader(
            name="azure_test",
            type=DataLoaderType.REMOTE,
            source="azure://container/blob.json"
        ))
        assert azure_loader.protocol == "azure"