"""Storage service for handling file uploads and downloads across different storage backends."""

import logging
import tempfile
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Unified storage service supporting local and cloud storage backends."""

    def __init__(self) -> None:
        """Initialize storage service based on configuration."""
        self.storage_type = settings.STORAGE_TYPE
        self._supabase_client = None

        if self.storage_type == "supabase":
            self._init_supabase()

    def _init_supabase(self) -> None:
        """Initialize cloud storage client for remote file storage."""
        try:
            from supabase import Client, create_client

            if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
                logger.warning(
                    "Cloud storage configured but SUPABASE_URL or SUPABASE_SECRET_KEY not set."
                )
                return

            # Ensure URL has trailing slash (required by cloud storage client)
            supabase_url = settings.SUPABASE_URL
            if not supabase_url.endswith("/"):
                supabase_url = supabase_url + "/"
                logger.debug(f"Added trailing slash to storage URL: {supabase_url}")

            self._supabase_client: Client = create_client(
                supabase_url, settings.SUPABASE_SECRET_KEY
            )
            logger.info("Cloud storage client initialized")
        except ImportError:
            raise ImportError(
                "supabase package is required for cloud storage. "
                "Install it with: pip install supabase"
            ) from None
        except Exception as e:
            logger.error(f"Failed to initialize cloud storage client: {e}")
            raise RuntimeError(f"Failed to initialize cloud storage client: {e}") from e

    def _validate_supabase_config(self) -> None:
        """Validate cloud storage configuration and client."""
        if not self._supabase_client:
            raise ValueError(
                "Cloud storage client not initialized. Check SUPABASE_URL and SUPABASE_SECRET_KEY."
            )
        if not settings.SUPABASE_STORAGE_BUCKET:
            raise ValueError("SUPABASE_STORAGE_BUCKET must be set")

    def _validate_file_path(self, file_path: str) -> None:
        """Validate file path to prevent directory traversal attacks.

        Args:
            file_path: Path to validate

        Raises:
            ValueError: If path contains traversal attempts or is invalid
        """
        if not file_path or not file_path.strip():
            raise ValueError("File path cannot be empty")

        # Reject paths containing directory traversal attempts
        # For local storage: allow ".." at the start (will be resolved by _resolve_local_path)
        # For cloud storage: reject all ".." (security requirement)
        # Always reject ".." in the middle or end of paths (suspicious)
        if ".." in file_path:
            if self.storage_type == "local" and file_path.startswith("../"):
                # Allow ".." at the start for local storage - will be resolved safely
                # But check if there are any ".." in the middle or end (suspicious)
                if ".." in file_path[3:]:  # Check after the leading "../"
                    raise ValueError("Invalid file path: path traversal detected")
                # Leading "../" is allowed for local storage
            else:
                # Cloud storage or ".." not at start - reject
                raise ValueError("Invalid file path: path traversal detected")

        # For cloud storage, reject absolute paths (local storage allows them)
        if self.storage_type != "local" and file_path.startswith("/"):
            raise ValueError(
                "Invalid file path: absolute paths not allowed for cloud storage"
            )

    def _resolve_local_path(self, file_path: str) -> Path:
        """Resolve local file path (handles absolute or relative paths).

        For absolute paths or paths starting with '..', use them directly.
        For relative paths, resolve against UPLOAD_DIR.
        """
        path_obj = Path(file_path)
        if path_obj.is_absolute():
            return path_obj
        # If path starts with '..', it's a relative path to a parent directory
        # Use it as-is (it will be resolved relative to current working directory)
        if file_path.startswith(".."):
            return path_obj.resolve()
        return Path(settings.UPLOAD_DIR) / file_path

    def upload_file(
        self, file_content: bytes, file_path: str, content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to storage.

        Args:
            file_content: File content as bytes
            file_path: Path where file should be stored
            content_type: MIME type of the file

        Returns:
            Storage path/URL of the uploaded file
        """
        self._validate_file_path(file_path)
        if self.storage_type == "supabase":
            return self._upload_to_supabase(file_content, file_path, content_type)
        return self._upload_to_local(file_content, file_path)

    def download_file(self, file_path: str) -> bytes:
        """
        Download a file from storage.

        Args:
            file_path: Path to the file in storage

        Returns:
            File content as bytes
        """
        self._validate_file_path(file_path)
        if self.storage_type == "supabase":
            return self._download_from_supabase(file_path)
        return self._download_from_local(file_path)

    def delete_file(self, file_path: str) -> None:
        """
        Delete a file from storage.

        Args:
            file_path: Path to the file in storage
        """
        self._validate_file_path(file_path)
        if self.storage_type == "supabase":
            self._delete_from_supabase(file_path)
        else:
            self._delete_from_local(file_path)

    def get_file_url(self, file_path: str) -> str:
        """
        Get a URL to access the file (for cloud storage) or path (for local).

        Args:
            file_path: Path to the file in storage

        Returns:
            URL to access the file (cloud storage) or file path (local)
        """
        self._validate_file_path(file_path)
        if self.storage_type == "supabase":
            return self._get_supabase_url(file_path)
        return file_path  # Local storage - API route handles serving

    def create_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Create a signed URL for secure, time-limited access to a file.

        Args:
            file_path: Path to the file in storage
            expires_in: Number of seconds the URL should remain valid (default: 1 hour)

        Returns:
            Signed URL string for cloud storage, or file path for local storage

        Raises:
            ValueError: If storage configuration is invalid
            RuntimeError: If signed URL creation fails
        """
        self._validate_file_path(file_path)
        if self.storage_type == "supabase":
            return self._create_supabase_signed_url(file_path, expires_in)
        return file_path  # Local storage - API route handles serving

    def get_local_file_path(
        self, file_path: str, temp_dir: Optional[str] = None
    ) -> Path:
        """
        Get a local file path for processing.

        For cloud storage: Downloads file to a temporary location and returns the path.
        For local storage: Returns the actual file path.

        IMPORTANT: When using cloud storage, the caller MUST clean up the temp file
        after processing. Use a try/finally block or context manager.

        Args:
            file_path: Path to the file in storage
            temp_dir: Optional directory for temp files (defaults to PROCESSED_DIR)

        Returns:
            Path object pointing to a local file that can be used for processing

        Example:
            temp_path = None
            try:
                temp_path = storage_service.get_local_file_path("raw/video.mp4")
                # Process video using temp_path
                process_video(temp_path)
            finally:
                if temp_path and temp_path.exists():
                    temp_path.unlink()  # Clean up
        """
        self._validate_file_path(file_path)

        if self.storage_type == "supabase":
            # Download from cloud storage to temp file
            logger.info(
                f"Downloading file from cloud storage for processing: {file_path}"
            )
            file_content = self.download_file(file_path)

            temp_dir_path = Path(temp_dir) if temp_dir else Path(settings.PROCESSED_DIR)
            temp_dir_path.mkdir(parents=True, exist_ok=True)

            # Create temp file
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=Path(file_path).suffix, dir=str(temp_dir_path)
            ) as temp_file:
                temp_file.write(file_content)
                temp_path = Path(temp_file.name)

            logger.debug(f"Downloaded to temp file: {temp_path}")
            return temp_path
        else:
            # For local storage, return the actual path
            return self._resolve_local_path(file_path)

    # Cloud storage methods

    def _upload_to_supabase(
        self, file_content: bytes, file_path: str, content_type: Optional[str] = None
    ) -> str:
        """
        Upload file to cloud storage with automatic unique filename generation.

        If a file with the same name already exists, automatically appends a counter
        (e.g., test.mp4 -> test_1.mp4 -> test_2.mp4) to ensure uniqueness, consistent
        with local storage behavior.

        Args:
            file_content: File content as bytes
            file_path: Path where file should be stored
            content_type: MIME type of the file

        Returns:
            Storage path of the uploaded file (may have counter appended)

        Raises:
            RuntimeError: If unable to generate unique filename after max attempts
            ValueError: If storage configuration is invalid
        """
        self._validate_supabase_config()

        file_options: dict[str, str] = {}
        if content_type:
            file_options["content-type"] = content_type

        # Extract directory and filename components for counter-based naming
        path_obj = Path(file_path)
        directory = str(path_obj.parent) if path_obj.parent != Path(".") else ""
        base_name = path_obj.stem
        extension = path_obj.suffix

        # Try to upload, and if duplicate error occurs, append counter and retry
        current_path = file_path
        counter = 0
        max_attempts = 1000

        while counter < max_attempts:
            try:
                # Attempt upload
                self._supabase_client.storage.from_(
                    settings.SUPABASE_STORAGE_BUCKET
                ).upload(current_path, file_content, file_options=file_options)

                # Success - file uploaded
                if counter > 0:
                    logger.debug(
                        f"File {file_path} already existed, uploaded as {current_path}"
                    )
                logger.info(f"File uploaded to cloud storage: {current_path}")
                return current_path

            except (RuntimeError, ValueError):
                # Re-raise configuration/validation errors immediately
                raise
            except Exception as e:
                # Check if error is due to duplicate file
                # Supabase raises StorageApiError or HTTPStatusError for duplicates
                error_msg = str(e).lower()
                error_type = type(e).__name__.lower()
                is_duplicate = (
                    "duplicate" in error_msg
                    or "409" in error_msg
                    or "already exists" in error_msg
                    or "resource already exists" in error_msg
                    or "storageapi" in error_type
                )

                if is_duplicate and counter < max_attempts - 1:
                    # Generate new filename with counter
                    counter += 1
                    if directory:
                        current_path = f"{directory}/{base_name}_{counter}{extension}"
                    else:
                        current_path = f"{base_name}_{counter}{extension}"
                    logger.debug(f"File {file_path} exists, trying {current_path}")
                else:
                    # Not a duplicate error, or max attempts reached
                    if counter >= max_attempts - 1:
                        logger.error(
                            f"Could not generate unique filename for {file_path} "
                            f"after {max_attempts} attempts"
                        )
                        raise RuntimeError(
                            f"Could not generate unique filename for {file_path} "
                            f"after {max_attempts} attempts"
                        ) from e
                    # Re-raise if it's a different error
                    logger.error(f"Upload failed for {current_path}: {e}")
                    raise

    def _download_from_supabase(self, file_path: str) -> bytes:
        """Download file from cloud storage."""
        self._validate_supabase_config()

        return self._supabase_client.storage.from_(
            settings.SUPABASE_STORAGE_BUCKET
        ).download(file_path)

    def _delete_from_supabase(self, file_path: str) -> None:
        """Delete file from cloud storage."""
        self._validate_supabase_config()

        self._supabase_client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove(
            [file_path]
        )

        logger.info(f"File deleted from cloud storage: {file_path}")

    def _get_supabase_url(self, file_path: str) -> str:
        """Get public URL for file in cloud storage."""
        self._validate_supabase_config()

        return self._supabase_client.storage.from_(
            settings.SUPABASE_STORAGE_BUCKET
        ).get_public_url(file_path)

    def _create_supabase_signed_url(self, file_path: str, expires_in: int) -> str:
        """Create a signed URL for secure, time-limited access to a file in cloud storage."""
        self._validate_supabase_config()

        try:
            response = self._supabase_client.storage.from_(
                settings.SUPABASE_STORAGE_BUCKET
            ).create_signed_url(file_path, expires_in)

            # Supabase returns dict with 'signedURL' key
            if isinstance(response, dict) and "signedURL" in response:
                return response["signedURL"]
            elif isinstance(response, dict) and "url" in response:
                # Fallback for different response formats
                return response["url"]
            else:
                raise RuntimeError(
                    f"Unexpected response format from Supabase signed URL: {response}"
                )
        except Exception as e:
            logger.error(f"Failed to create signed URL for {file_path}: {e}")
            raise RuntimeError(f"Failed to create signed URL: {e}") from e

    # Local storage methods

    def _upload_to_local(self, file_content: bytes, file_path: str) -> str:
        """Upload file to local filesystem."""
        full_path = self._resolve_local_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File uploaded to local storage: {full_path}")
        return str(full_path)

    def _download_from_local(self, file_path: str) -> bytes:
        """Download file from local filesystem."""
        full_path = self._resolve_local_path(file_path)

        with open(full_path, "rb") as f:
            return f.read()

    def _delete_from_local(self, file_path: str) -> None:
        """Delete file from local filesystem."""
        full_path = self._resolve_local_path(file_path)

        if full_path.exists():
            full_path.unlink()
            logger.info(f"File deleted from local storage: {full_path}")
        else:
            logger.warning(f"File not found for deletion: {full_path}")


# Create singleton instance
storage_service = StorageService()
