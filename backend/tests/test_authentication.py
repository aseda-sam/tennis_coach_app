"""
Tests for authentication functionality.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user
from app.main import app
from app.utils.supabase_auth import get_supabase_client, verify_supabase_token


class TestSupabaseAuth:
    """Tests for Supabase authentication utilities."""

    def test_get_supabase_client_missing_url(self) -> None:
        """Test that missing SUPABASE_URL raises ValueError."""
        with patch("app.utils.supabase_auth.settings") as mock_settings:
            mock_settings.SUPABASE_URL = None
            mock_settings.SUPABASE_SECRET_KEY = "test-key"  # noqa: S105

            with pytest.raises(ValueError, match="SUPABASE_URL not configured"):
                get_supabase_client()

    def test_get_supabase_client_missing_key(self) -> None:
        """Test that missing SUPABASE_SECRET_KEY raises ValueError."""
        with patch("app.utils.supabase_auth.settings") as mock_settings:
            mock_settings.SUPABASE_URL = "https://test.supabase.co/"
            mock_settings.SUPABASE_SECRET_KEY = None

            with pytest.raises(ValueError, match="SUPABASE_SECRET_KEY not configured"):
                get_supabase_client()

    def test_get_supabase_client_adds_trailing_slash(self) -> None:
        """Test that URL gets trailing slash added if missing."""
        with patch("app.utils.supabase_auth.settings") as mock_settings, patch(
            "app.utils.supabase_auth.create_client"
        ) as mock_create:
            mock_settings.SUPABASE_URL = "https://test.supabase.co"
            mock_settings.SUPABASE_SECRET_KEY = "test-key"  # noqa: S105

            get_supabase_client()

            mock_create.assert_called_once_with("https://test.supabase.co/", "test-key")

    def test_verify_supabase_token_valid(self) -> None:
        """Test token verification with valid token."""
        mock_user = Mock()
        mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
        mock_user.email = "test@example.com"
        mock_user.user_metadata = {"role": "user"}

        mock_response = Mock()
        mock_response.user = mock_user

        with patch("app.utils.supabase_auth.get_supabase_client") as mock_get_client:
            mock_client = Mock()
            mock_client.auth.get_user.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = verify_supabase_token("valid-token")

            assert result is not None
            assert result["id"] == "123e4567-e89b-12d3-a456-426614174000"
            assert result["email"] == "test@example.com"
            assert result["user_metadata"] == {"role": "user"}

    def test_verify_supabase_token_invalid(self) -> None:
        """Test token verification with invalid token."""
        with patch("app.utils.supabase_auth.get_supabase_client") as mock_get_client:
            mock_client = Mock()
            mock_client.auth.get_user.side_effect = Exception("Invalid token")
            mock_get_client.return_value = mock_client

            result = verify_supabase_token("invalid-token")

            assert result is None

    def test_verify_supabase_token_no_user(self) -> None:
        """Test token verification when response has no user."""
        mock_response = Mock()
        mock_response.user = None

        with patch("app.utils.supabase_auth.get_supabase_client") as mock_get_client:
            mock_client = Mock()
            mock_client.auth.get_user.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = verify_supabase_token("token")

            assert result is None

    def test_verify_supabase_token_empty_metadata(self) -> None:
        """Test token verification with empty user_metadata."""
        mock_user = Mock()
        mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
        mock_user.email = "test@example.com"
        mock_user.user_metadata = None

        mock_response = Mock()
        mock_response.user = mock_user

        with patch("app.utils.supabase_auth.get_supabase_client") as mock_get_client:
            mock_client = Mock()
            mock_client.auth.get_user.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = verify_supabase_token("valid-token")

            assert result is not None
            assert result["user_metadata"] == {}


class TestAuthDependency:
    """Tests for authentication dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_local_profile_no_auth(self) -> None:
        """Test that local profile returns mock user without auth."""
        with patch("app.dependencies.auth.settings") as mock_settings:
            mock_settings.PROFILE = "local"

            result = await get_current_user(credentials=None)

            assert result["id"] == "00000000-0000-0000-0000-000000000000"
            assert result["email"] == "dev@localhost"
            assert result["user_metadata"] == {}

    @pytest.mark.asyncio
    async def test_get_current_user_production_no_credentials(self) -> None:
        """Test that production profile requires credentials."""
        with patch("app.dependencies.auth.settings") as mock_settings:
            mock_settings.PROFILE = "production"

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=None)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Authentication required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self) -> None:
        """Test that valid token returns user."""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "valid-token"

        mock_user = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "test@example.com",
            "user_metadata": {},
        }

        with patch("app.dependencies.auth.settings") as mock_settings, patch(
            "app.dependencies.auth.verify_supabase_token"
        ) as mock_verify:
            mock_settings.PROFILE = "production"
            mock_verify.return_value = mock_user

            result = await get_current_user(credentials=mock_credentials)

            assert result == mock_user
            mock_verify.assert_called_once_with("valid-token")

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self) -> None:
        """Test that invalid token raises 401."""
        mock_credentials = Mock(spec=HTTPAuthorizationCredentials)
        mock_credentials.credentials = "invalid-token"

        with patch("app.dependencies.auth.settings") as mock_settings, patch(
            "app.dependencies.auth.verify_supabase_token"
        ) as mock_verify:
            mock_settings.PROFILE = "production"
            mock_verify.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=mock_credentials)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid authentication credentials" in str(exc_info.value.detail)


class TestProtectedEndpoint:
    """Tests for protected endpoints."""

    def test_video_upload_requires_auth(self, client: TestClient) -> None:
        """Test that video upload endpoint requires authentication."""
        # Override auth dependency to require auth
        from app.dependencies.auth import get_current_user

        async def require_auth() -> None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        app.dependency_overrides[get_current_user] = require_auth

        # Try to upload without auth
        response = client.post(
            "/v0/videos/upload", files={"file": ("test.mp4", b"fake")}
        )

        assert response.status_code == 401
        app.dependency_overrides.clear()

    def test_video_upload_with_mock_auth(self, client: TestClient) -> None:
        """Test that video upload works with mock authentication."""
        from app.dependencies.auth import get_current_user

        async def mock_auth() -> dict:
            return {
                "id": "00000000-0000-0000-0000-000000000000",
                "email": "test@example.com",
                "user_metadata": {},
            }

        app.dependency_overrides[get_current_user] = mock_auth

        # Upload should work with mock auth
        # Note: This will fail if video validation fails, but auth should pass
        response = client.post(
            "/v0/videos/upload", files={"file": ("test.mp4", b"fake")}
        )

        # Auth passed (might fail on validation, but not 401)
        assert response.status_code != 401
        app.dependency_overrides.clear()
