"""Storage service for handling file uploads and downloads across different storage backends."""

import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Unified storage service supporting local and Supabase storage."""

    def __init__(self) -> None:
        """Initialize storage service based on configuration."""
        self.storage_type = settings.STORAGE_TYPE
        self._supabase_client = None

        if self.storage_type == "supabase":
            self._init_supabase()

    def _init_supabase(self) -> None:
        """Initialize Supabase client for storage."""
        try:
            from supabase import Client, create_client

            if not settings.SUPABASE_STORAGE_URL or not settings.SUPABASE_KEY:
                logger.warning(
                    "Supabase storage configured but SUPABASE_STORAGE_URL or SUPABASE_KEY not set."
                )
                return

            self._supabase_client: Client = create_client(
                settings.SUPABASE_STORAGE_URL, settings.SUPABASE_KEY
            )
            logger.info("Supabase storage client initialized")
        except ImportError:
            raise ImportError(
                "supabase package is required for Supabase storage. "
                "Install it with: pip install supabase"
            ) from None
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise RuntimeError(f"Failed to initialize Supabase client: {e}") from e

    def _validate_supabase_config(self) -> None:
        """Validate Supabase configuration and client."""
        if not self._supabase_client:
            raise ValueError(
                "Supabase client not initialized. Check SUPABASE_STORAGE_URL and SUPABASE_KEY."
            )
        if not settings.SUPABASE_STORAGE_BUCKET:
            raise ValueError("SUPABASE_STORAGE_BUCKET must be set")

    def _resolve_local_path(self, file_path: str) -> Path:
        """Resolve local file path (handles absolute or relative paths)."""
        if Path(file_path).is_absolute():
            return Path(file_path)
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
        if self.storage_type == "supabase":
            return self._download_from_supabase(file_path)
        return self._download_from_local(file_path)

    def delete_file(self, file_path: str) -> None:
        """
        Delete a file from storage.

        Args:
            file_path: Path to the file in storage
        """
        if self.storage_type == "supabase":
            self._delete_from_supabase(file_path)
        else:
            self._delete_from_local(file_path)

    def get_file_url(self, file_path: str) -> str:
        """
        Get a URL to access the file (for Supabase) or path (for local).

        Args:
            file_path: Path to the file in storage

        Returns:
            URL to access the file (Supabase) or file path (local)
        """
        if self.storage_type == "supabase":
            return self._get_supabase_url(file_path)
        return file_path  # Local storage - API route handles serving

    # Supabase storage methods

    def _upload_to_supabase(
        self, file_content: bytes, file_path: str, content_type: Optional[str] = None
    ) -> str:
        """Upload file to Supabase storage."""
        self._validate_supabase_config()

        self._supabase_client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
            file_path, file_content, file_options={"content-type": content_type}
        )

        logger.info(f"File uploaded to Supabase: {file_path}")
        return file_path

    def _download_from_supabase(self, file_path: str) -> bytes:
        """Download file from Supabase storage."""
        self._validate_supabase_config()

        return self._supabase_client.storage.from_(
            settings.SUPABASE_STORAGE_BUCKET
        ).download(file_path)

    def _delete_from_supabase(self, file_path: str) -> None:
        """Delete file from Supabase storage."""
        self._validate_supabase_config()

        self._supabase_client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove(
            [file_path]
        )

        logger.info(f"File deleted from Supabase: {file_path}")

    def _get_supabase_url(self, file_path: str) -> str:
        """Get public URL for file in Supabase storage."""
        self._validate_supabase_config()

        return self._supabase_client.storage.from_(
            settings.SUPABASE_STORAGE_BUCKET
        ).get_public_url(file_path)

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
