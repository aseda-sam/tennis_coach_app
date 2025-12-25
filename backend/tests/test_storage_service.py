"""Tests for storage service."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.core.config import settings
from app.services.storage_service import StorageService


class TestStorageServiceLocal:
    """Test local storage operations."""

    def test_upload_to_local(
        self, temp_upload_dir: Path, sample_video_content: bytes
    ) -> None:
        """Test uploading file to local filesystem."""
        # Override UPLOAD_DIR for this test
        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()
            file_path = "test_video.mp4"

            result_path = service.upload_file(sample_video_content, file_path)

            # Verify file was created
            full_path = temp_upload_dir / file_path
            assert full_path.exists()
            assert full_path.read_bytes() == sample_video_content
            assert result_path == str(full_path)

    def test_download_from_local(
        self, temp_upload_dir: Path, sample_video_content: bytes
    ) -> None:
        """Test downloading file from local storage."""
        # Create a file first
        file_path = "test_video.mp4"
        full_path = temp_upload_dir / file_path
        full_path.write_bytes(sample_video_content)

        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()
            downloaded_content = service.download_file(file_path)

            assert downloaded_content == sample_video_content

    def test_delete_from_local(
        self, temp_upload_dir: Path, sample_video_content: bytes
    ) -> None:
        """Test deleting file from local storage."""
        # Create a file first
        file_path = "test_video.mp4"
        full_path = temp_upload_dir / file_path
        full_path.write_bytes(sample_video_content)
        assert full_path.exists()

        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()
            service.delete_file(file_path)

            assert not full_path.exists()

    def test_get_file_url_local(self) -> None:
        """Test getting file URL for local storage."""
        with patch.object(settings, "STORAGE_TYPE", "local"):
            service = StorageService()
            file_path = "test_video.mp4"

            result = service.get_file_url(file_path)

            # Local storage returns the path as-is
            assert result == file_path

    def test_upload_local_creates_directories(
        self, temp_upload_dir: Path, sample_video_content: bytes
    ) -> None:
        """Test that upload creates parent directories if missing."""
        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()
            file_path = "subdir/nested/test_video.mp4"

            result_path = service.upload_file(sample_video_content, file_path)

            # Verify nested directories were created
            full_path = temp_upload_dir / file_path
            assert full_path.exists()
            assert full_path.parent.exists()
            assert full_path.parent.parent.exists()
            assert result_path == str(full_path)

    def test_resolve_local_path_absolute(
        self, temp_upload_dir: Path, sample_video_content: bytes
    ) -> None:
        """Test that absolute paths are handled correctly."""
        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()
            absolute_path = str(temp_upload_dir / "absolute_video.mp4")

            result_path = service.upload_file(sample_video_content, absolute_path)

            # Should use absolute path as-is
            assert result_path == absolute_path
            assert Path(absolute_path).exists()

    def test_resolve_local_path_relative(
        self, temp_upload_dir: Path, sample_video_content: bytes
    ) -> None:
        """Test that relative paths are resolved correctly."""
        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()
            relative_path = "relative_video.mp4"

            result_path = service.upload_file(sample_video_content, relative_path)

            # Should resolve relative to UPLOAD_DIR
            expected_path = temp_upload_dir / relative_path
            assert result_path == str(expected_path)
            assert expected_path.exists()

    def test_download_local_file_not_found(self, temp_upload_dir: Path) -> None:
        """Test that downloading non-existent file raises error."""
        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()

            with pytest.raises(FileNotFoundError):
                service.download_file("nonexistent.mp4")

    def test_delete_local_file_not_found(self, temp_upload_dir: Path) -> None:
        """Test that deleting non-existent file logs warning but doesn't raise."""
        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()

            # Should not raise, just log warning
            service.delete_file("nonexistent.mp4")


@pytest.fixture
def mock_supabase_client() -> Mock:
    """Create a mock Supabase client."""
    mock_client = Mock()
    mock_bucket = Mock()

    mock_client.storage.from_.return_value = mock_bucket
    mock_bucket.upload.return_value = None
    mock_bucket.download.return_value = b"test content"
    mock_bucket.remove.return_value = None
    mock_bucket.get_public_url.return_value = "https://example.com/file.mp4"

    return mock_client


class TestStorageServiceSupabase:
    """Test Supabase storage operations (mocked)."""

    def test_upload_to_supabase(
        self, mock_supabase_client: Mock, sample_video_content: bytes
    ) -> None:
        """Test uploading file to Supabase."""
        # Create mock supabase module
        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock(return_value=mock_supabase_client)
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_URL", "https://test.supabase.co"
        ), patch.object(settings, "SUPABASE_KEY", "test-key"), patch.object(
            settings, "SUPABASE_STORAGE_BUCKET", "test-bucket"
        ), patch.dict("sys.modules", {"supabase": mock_supabase_module}):
            service = StorageService()
            service._supabase_client = mock_supabase_client

            file_path = "test_video.mp4"
            result = service.upload_file(sample_video_content, file_path, "video/mp4")

            # Verify Supabase client was called correctly
            mock_supabase_client.storage.from_.assert_called_once_with("test-bucket")
            mock_bucket = mock_supabase_client.storage.from_.return_value
            mock_bucket.upload.assert_called_once_with(
                file_path,
                sample_video_content,
                file_options={"content-type": "video/mp4"},
            )
            assert result == file_path

    def test_download_from_supabase(
        self, mock_supabase_client: Mock, sample_video_content: bytes
    ) -> None:
        """Test downloading file from Supabase."""
        mock_bucket = mock_supabase_client.storage.from_.return_value
        mock_bucket.download.return_value = sample_video_content

        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock(return_value=mock_supabase_client)
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_STORAGE_BUCKET", "test-bucket"
        ), patch.dict("sys.modules", {"supabase": mock_supabase_module}):
            service = StorageService()
            service._supabase_client = mock_supabase_client

            file_path = "test_video.mp4"
            result = service.download_file(file_path)

            mock_supabase_client.storage.from_.assert_called_once_with("test-bucket")
            mock_bucket.download.assert_called_once_with(file_path)
            assert result == sample_video_content

    def test_delete_from_supabase(self, mock_supabase_client: Mock) -> None:
        """Test deleting file from Supabase."""
        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock(return_value=mock_supabase_client)
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_STORAGE_BUCKET", "test-bucket"
        ), patch.dict("sys.modules", {"supabase": mock_supabase_module}):
            service = StorageService()
            service._supabase_client = mock_supabase_client

            file_path = "test_video.mp4"
            service.delete_file(file_path)

            mock_supabase_client.storage.from_.assert_called_once_with("test-bucket")
            mock_bucket = mock_supabase_client.storage.from_.return_value
            mock_bucket.remove.assert_called_once_with([file_path])

    def test_get_supabase_url(self, mock_supabase_client: Mock) -> None:
        """Test getting public URL from Supabase."""
        mock_bucket = mock_supabase_client.storage.from_.return_value
        mock_bucket.get_public_url.return_value = "https://example.com/test_video.mp4"

        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock(return_value=mock_supabase_client)
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_STORAGE_BUCKET", "test-bucket"
        ), patch.dict("sys.modules", {"supabase": mock_supabase_module}):
            service = StorageService()
            service._supabase_client = mock_supabase_client

            file_path = "test_video.mp4"
            result = service.get_file_url(file_path)

            mock_supabase_client.storage.from_.assert_called_once_with("test-bucket")
            mock_bucket.get_public_url.assert_called_once_with(file_path)
            assert result == "https://example.com/test_video.mp4"

    def test_supabase_upload_with_content_type(
        self, mock_supabase_client: Mock, sample_video_content: bytes
    ) -> None:
        """Test uploading with MIME type."""
        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock(return_value=mock_supabase_client)
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_STORAGE_BUCKET", "test-bucket"
        ), patch.dict("sys.modules", {"supabase": mock_supabase_module}):
            service = StorageService()
            service._supabase_client = mock_supabase_client

            file_path = "test_video.mp4"
            service.upload_file(sample_video_content, file_path, "video/mp4")

            mock_bucket = mock_supabase_client.storage.from_.return_value
            mock_bucket.upload.assert_called_once_with(
                file_path,
                sample_video_content,
                file_options={"content-type": "video/mp4"},
            )


class TestStorageServiceInitialization:
    """Test storage service initialization."""

    def test_init_local_storage(self) -> None:
        """Test initialization for local storage."""
        with patch.object(settings, "STORAGE_TYPE", "local"):
            service = StorageService()

            assert service.storage_type == "local"
            assert service._supabase_client is None

    def test_init_supabase_with_credentials(self) -> None:
        """Test initialization with valid Supabase credentials."""
        mock_client = Mock()
        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock(return_value=mock_client)
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_URL", "https://test.supabase.co/"
        ), patch.object(settings, "SUPABASE_KEY", "test-key"), patch.dict(
            "sys.modules", {"supabase": mock_supabase_module}
        ):
            service = StorageService()

            assert service.storage_type == "supabase"
            assert service._supabase_client == mock_client

    def test_init_supabase_missing_credentials(self) -> None:
        """Test initialization logs warning when credentials missing."""
        # Create a mock supabase module
        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock()
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_URL", None
        ), patch.object(settings, "SUPABASE_KEY", None), patch.dict(
            "sys.modules", {"supabase": mock_supabase_module}
        ), patch("app.services.storage_service.logger") as mock_logger:
            service = StorageService()

            assert service._supabase_client is None
            mock_logger.warning.assert_called_once()

    def test_init_supabase_missing_package(self) -> None:
        """Test that missing supabase package raises ImportError."""
        # Remove supabase from sys.modules to simulate missing package
        # Also remove any submodules that might be cached
        original_supabase = sys.modules.pop("supabase", None)
        original_supabase_client = sys.modules.pop("supabase.client", None)
        original_supabase_create = sys.modules.pop("supabase.create_client", None)
        # Remove any other supabase-related modules that might be cached
        keys_to_remove = [
            k for k in list(sys.modules.keys()) if k.startswith("supabase")
        ]
        original_modules = {k: sys.modules.pop(k) for k in keys_to_remove}

        try:
            # Save reference to original __import__ before patching
            import builtins

            original_import = builtins.__import__

            with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
                settings, "SUPABASE_URL", "https://test.supabase.co/"
            ), patch.object(settings, "SUPABASE_KEY", "test-key"):
                # Patch the import statement by making the module raise ImportError
                # We need to ensure sys.modules doesn't have supabase, and patch __import__
                def import_side_effect(name, *args, **kwargs):
                    if name == "supabase" or name.startswith("supabase."):
                        raise ImportError(f"No module named '{name}'")
                    # For other imports, use the original import function
                    return original_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=import_side_effect):
                    with pytest.raises(ImportError) as exc_info:
                        StorageService()

                    assert "supabase package is required" in str(exc_info.value)
        finally:
            # Restore if they existed
            if original_supabase:
                sys.modules["supabase"] = original_supabase
            if original_supabase_client:
                sys.modules["supabase.client"] = original_supabase_client
            if original_supabase_create:
                sys.modules["supabase.create_client"] = original_supabase_create
            # Restore other supabase modules
            sys.modules.update(original_modules)

    def test_init_supabase_url_trailing_slash(self) -> None:
        """Test that URL gets trailing slash added automatically."""
        mock_client = Mock()
        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock(return_value=mock_client)
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_URL", "https://test.supabase.co"
        ), patch.object(settings, "SUPABASE_KEY", "test-key"), patch.dict(
            "sys.modules", {"supabase": mock_supabase_module}
        ):
            service = StorageService()

            # Should add trailing slash
            mock_supabase_module.create_client.assert_called_once_with(
                "https://test.supabase.co/", "test-key"
            )
            assert service._supabase_client == mock_client


class TestStorageServicePathValidation:
    """Test path validation in storage service."""

    def test_validate_file_path_rejects_traversal(self) -> None:
        """Test that path traversal attempts are rejected."""
        with patch.object(settings, "STORAGE_TYPE", "local"):
            service = StorageService()

            with pytest.raises(ValueError) as exc_info:
                service.upload_file(b"content", "../../etc/passwd")

            assert "path traversal detected" in str(exc_info.value)

    def test_validate_file_path_rejects_absolute_paths_for_cloud(
        self, mock_supabase_client: Mock
    ) -> None:
        """Test that absolute paths are rejected for cloud storage."""
        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock(return_value=mock_supabase_client)
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_STORAGE_BUCKET", "test-bucket"
        ), patch.dict("sys.modules", {"supabase": mock_supabase_module}):
            service = StorageService()
            service._supabase_client = mock_supabase_client

            with pytest.raises(ValueError) as exc_info:
                service.upload_file(b"content", "/absolute/path/file.mp4")

            assert "absolute paths not allowed for cloud storage" in str(exc_info.value)

    def test_validate_file_path_allows_absolute_paths_for_local(
        self, temp_upload_dir: Path, sample_video_content: bytes
    ) -> None:
        """Test that absolute paths are allowed for local storage."""
        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()
            absolute_path = str(temp_upload_dir / "absolute_file.mp4")

            # Should not raise for local storage
            service.upload_file(sample_video_content, absolute_path)
            assert Path(absolute_path).exists()

    def test_validate_file_path_rejects_empty_path(self) -> None:
        """Test that empty paths are rejected."""
        with patch.object(settings, "STORAGE_TYPE", "local"):
            service = StorageService()

            with pytest.raises(ValueError) as exc_info:
                service.upload_file(b"content", "")

            assert "File path cannot be empty" in str(exc_info.value)

    def test_validate_file_path_allows_safe_relative_paths(
        self, temp_upload_dir: Path, sample_video_content: bytes
    ) -> None:
        """Test that safe relative paths are allowed."""
        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()

            # Should not raise
            service.upload_file(sample_video_content, "safe_file.mp4")
            assert (temp_upload_dir / "safe_file.mp4").exists()


class TestStorageServiceErrorHandling:
    """Test error handling in storage service."""

    def test_validate_supabase_config_missing_client(self) -> None:
        """Test that missing client raises ValueError."""
        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock()
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"):
            with patch.dict("sys.modules", {"supabase": mock_supabase_module}):
                service = StorageService()
                service._supabase_client = None

            with pytest.raises(ValueError) as exc_info:
                service._validate_supabase_config()

            assert "Supabase client not initialized" in str(exc_info.value)

    def test_validate_supabase_config_missing_bucket(self) -> None:
        """Test that missing bucket raises ValueError."""
        mock_client = Mock()
        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock()
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_STORAGE_BUCKET", None
        ), patch.dict("sys.modules", {"supabase": mock_supabase_module}):
            service = StorageService()
            service._supabase_client = mock_client

            with pytest.raises(ValueError) as exc_info:
                service._validate_supabase_config()

            assert "SUPABASE_STORAGE_BUCKET must be set" in str(exc_info.value)

    def test_supabase_operation_without_init(self) -> None:
        """Test that Supabase operations fail properly when not initialized."""
        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock()
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.dict(
            "sys.modules", {"supabase": mock_supabase_module}
        ):
            service = StorageService()
            service._supabase_client = None

            with pytest.raises(ValueError):
                service.upload_file(b"content", "test.mp4")


class TestStorageServiceIntegration:
    """Integration tests for storage service."""

    def test_upload_download_roundtrip_local(
        self, temp_upload_dir: Path, sample_video_content: bytes
    ) -> None:
        """Test upload then download returns same content."""
        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()
            file_path = "test_video.mp4"

            # Upload
            upload_result = service.upload_file(sample_video_content, file_path)
            assert upload_result == str(temp_upload_dir / file_path)

            # Download
            downloaded = service.download_file(file_path)
            assert downloaded == sample_video_content

    def test_upload_delete_roundtrip_local(
        self, temp_upload_dir: Path, sample_video_content: bytes
    ) -> None:
        """Test upload then delete removes file."""
        with patch.object(settings, "UPLOAD_DIR", str(temp_upload_dir)), patch.object(
            settings, "STORAGE_TYPE", "local"
        ):
            service = StorageService()
            file_path = "test_video.mp4"
            full_path = temp_upload_dir / file_path

            # Upload
            service.upload_file(sample_video_content, file_path)
            assert full_path.exists()

            # Delete
            service.delete_file(file_path)
            assert not full_path.exists()

    def test_upload_download_roundtrip_supabase(
        self, mock_supabase_client: Mock, sample_video_content: bytes
    ) -> None:
        """Test upload then download with Supabase (mocked)."""
        mock_bucket = mock_supabase_client.storage.from_.return_value
        mock_bucket.download.return_value = sample_video_content

        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock(return_value=mock_supabase_client)
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_STORAGE_BUCKET", "test-bucket"
        ), patch.dict("sys.modules", {"supabase": mock_supabase_module}):
            service = StorageService()
            service._supabase_client = mock_supabase_client

            file_path = "test_video.mp4"

            # Upload
            upload_result = service.upload_file(sample_video_content, file_path)
            assert upload_result == file_path

            # Download
            downloaded = service.download_file(file_path)
            assert downloaded == sample_video_content


class TestStorageServiceTypeSwitching:
    """Test storage type switching."""

    def test_storage_type_local(self) -> None:
        """Test service uses local storage when STORAGE_TYPE=local."""
        with patch.object(settings, "STORAGE_TYPE", "local"):
            service = StorageService()

            assert service.storage_type == "local"
            # Should return path for local storage
            assert service.get_file_url("test.mp4") == "test.mp4"

    def test_storage_type_supabase(self) -> None:
        """Test service uses Supabase when STORAGE_TYPE=supabase."""
        mock_client = Mock()
        mock_bucket = Mock()
        mock_bucket.get_public_url.return_value = "https://example.com/test.mp4"
        mock_client.storage.from_.return_value = mock_bucket

        mock_supabase_module = Mock()
        mock_supabase_module.create_client = Mock(return_value=mock_client)
        mock_supabase_module.Client = Mock()

        with patch.object(settings, "STORAGE_TYPE", "supabase"), patch.object(
            settings, "SUPABASE_STORAGE_BUCKET", "test-bucket"
        ), patch.dict("sys.modules", {"supabase": mock_supabase_module}):
            service = StorageService()
            service._supabase_client = mock_client

            assert service.storage_type == "supabase"
            # Should return URL for Supabase storage
            result = service.get_file_url("test.mp4")
            assert result == "https://example.com/test.mp4"
