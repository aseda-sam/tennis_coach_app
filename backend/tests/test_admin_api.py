"""
Tests for admin API endpoints and authorization.

TDD Contract: Tests define behavior, not implementation details.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.dependencies.auth import get_current_user
from app.main import app
from app.utils.authorization import is_admin, require_admin


class TestAdminAuthorization:
    """Tests for admin authorization utilities."""

    def test_is_admin_with_valid_admin_id(self) -> None:
        """Test is_admin returns True for user in admin allowlist."""
        admin_user_id = settings.admin_user_ids[0]
        user = {
            "id": admin_user_id,
            "email": "admin@example.com",
            "user_metadata": {},
        }

        assert is_admin(user) is True

    def test_is_admin_with_non_admin_id(self) -> None:
        """Test is_admin returns False for user not in admin allowlist."""
        user = {
            "id": "11111111-1111-1111-1111-111111111111",
            "email": "user@example.com",
            "user_metadata": {},
        }

        assert is_admin(user) is False

    def test_is_admin_with_missing_id(self) -> None:
        """Test is_admin returns False when user dict has no id."""
        user = {
            "email": "user@example.com",
            "user_metadata": {},
        }

        assert is_admin(user) is False

    def test_is_admin_with_empty_id(self) -> None:
        """Test is_admin returns False when user id is empty string."""
        user = {
            "id": "",
            "email": "user@example.com",
            "user_metadata": {},
        }

        assert is_admin(user) is False

    def test_is_admin_with_multiple_admin_ids(self) -> None:
        """Test is_admin works with comma-separated admin IDs."""
        with patch.object(settings, "ADMIN_USER_IDS", "admin1,admin2,admin3"):
            user1 = {"id": "admin1", "email": "admin1@example.com"}
            user2 = {"id": "admin2", "email": "admin2@example.com"}
            user3 = {"id": "admin3", "email": "admin3@example.com"}
            non_admin = {"id": "user1", "email": "user@example.com"}

            assert is_admin(user1) is True
            assert is_admin(user2) is True
            assert is_admin(user3) is True
            assert is_admin(non_admin) is False

    def test_require_admin_allows_admin(self) -> None:
        """Test require_admin does not raise for admin user."""
        admin_user_id = settings.admin_user_ids[0]
        user = {
            "id": admin_user_id,
            "email": "admin@example.com",
            "user_metadata": {},
        }

        # Should not raise
        require_admin(user)

    def test_require_admin_raises_for_non_admin(self) -> None:
        """Test require_admin raises 403 for non-admin user."""
        user = {
            "id": "11111111-1111-1111-1111-111111111111",
            "email": "user@example.com",
            "user_metadata": {},
        }

        with pytest.raises(HTTPException) as exc_info:
            require_admin(user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin access required" in str(exc_info.value.detail)


class TestAdminStatusEndpoint:
    """Tests for GET /admin/status endpoint."""

    def test_admin_status_as_admin(self, client: TestClient) -> None:
        """Test admin status endpoint returns True for admin user."""
        # Default mock user in conftest is admin (00000000-0000-0000-0000-000000000000)
        response = client.get("/v0/admin/status")

        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] is True

    def test_admin_status_as_non_admin(self, client: TestClient) -> None:
        """Test admin status endpoint returns False for non-admin user."""

        async def mock_non_admin() -> dict:
            return {
                "id": "11111111-1111-1111-1111-111111111111",
                "email": "user@example.com",
                "user_metadata": {},
            }

        app.dependency_overrides[get_current_user] = mock_non_admin

        try:
            response = client.get("/v0/admin/status")

            assert response.status_code == 200
            data = response.json()
            assert data["is_admin"] is False
        finally:
            app.dependency_overrides.clear()

    def test_admin_status_requires_auth(self, client: TestClient) -> None:
        """Test admin status endpoint requires authentication."""

        async def require_auth() -> None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        app.dependency_overrides[get_current_user] = require_auth

        try:
            response = client.get("/v0/admin/status")

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()


class TestUploadForUserEndpoint:
    """Tests for POST /admin/videos/upload-for-user endpoint."""

    def test_upload_for_user_requires_admin(self, client: TestClient) -> None:
        """Test upload-for-user endpoint requires admin access."""

        async def mock_non_admin() -> dict:
            return {
                "id": "11111111-1111-1111-1111-111111111111",
                "email": "user@example.com",
                "user_metadata": {},
            }

        app.dependency_overrides[get_current_user] = mock_non_admin

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                tmp_file.write(
                    b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom"
                    + b"\x00" * 10000
                )
                tmp_file_path = tmp_file.name

            try:
                with open(tmp_file_path, "rb") as f:
                    response = client.post(
                        "/v0/admin/videos/upload-for-user",
                        files={"file": ("test.mp4", f, "video/mp4")},
                        params={
                            "target_user_id": "22222222-2222-2222-2222-222222222222"
                        },
                    )

                assert response.status_code == 403
                error_data = response.json()
                assert "error" in error_data or "Admin access required" in str(
                    response.text
                )
            finally:
                Path(tmp_file_path).unlink(missing_ok=True)
        finally:
            app.dependency_overrides.clear()

    def test_upload_for_user_validates_target_user_id(self, client: TestClient) -> None:
        """Test upload-for-user validates target_user_id parameter."""
        with patch("app.api.routes.admin.get_user_by_id") as mock_get_user:
            mock_get_user.return_value = None  # User doesn't exist

            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                tmp_file.write(
                    b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom"
                    + b"\x00" * 10000
                )
                tmp_file_path = tmp_file.name

            try:
                with open(tmp_file_path, "rb") as f:
                    response = client.post(
                        "/v0/admin/videos/upload-for-user",
                        files={"file": ("test.mp4", f, "video/mp4")},
                        params={"target_user_id": "invalid-user-id"},
                    )

                assert response.status_code == 400
                mock_get_user.assert_called_once()
                assert mock_get_user.call_args[0][0] == "invalid-user-id"
            finally:
                Path(tmp_file_path).unlink(missing_ok=True)

    def test_upload_for_user_success(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test successful upload-for-user assigns video to target user."""
        target_user_id = "22222222-2222-2222-2222-222222222222"

        with (
            patch("app.api.routes.admin.get_user_by_id") as mock_get_user,
            patch("app.services.storage_service.storage_service") as mock_storage,
            patch.object(settings, "AUTO_ENQUEUE_ON_UPLOAD", False),
            patch.object(settings, "TRANSCODE_ENABLED", False),
        ):
            # Mock user exists
            mock_get_user.return_value = {
                "id": target_user_id,
                "email": "target@example.com",
            }

            # Mock storage
            mock_storage.upload_file.return_value = "storage/path/test.mp4"

            # Create test video file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                tmp_file.write(
                    b"\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom"
                    + b"\x00" * 10000
                )
                tmp_file_path = tmp_file.name

            try:
                with open(tmp_file_path, "rb") as f:
                    response = client.post(
                        "/v0/admin/videos/upload-for-user",
                        files={"file": ("test.mp4", f, "video/mp4")},
                        params={"target_user_id": target_user_id},
                    )

                assert response.status_code == 200
                data = response.json()
                assert "video_id" in data
                assert "filename" in data

                # Verify video was created with target user_id
                from app.models.video import Video

                video = (
                    db_session.query(Video).filter(Video.id == data["video_id"]).first()
                )
                assert video is not None
                assert video.user_id == target_user_id
                # Admin user should NOT be the owner
                assert video.user_id != "00000000-0000-0000-0000-000000000000"
            finally:
                Path(tmp_file_path).unlink(missing_ok=True)


class TestDemoManagementEndpoints:
    """Tests for demo management endpoints (admin only)."""

    def test_list_demos_requires_admin(self, client: TestClient) -> None:
        """Test list demos endpoint requires admin access."""

        async def mock_non_admin() -> dict:
            return {
                "id": "11111111-1111-1111-1111-111111111111",
                "email": "user@example.com",
                "user_metadata": {},
            }

        app.dependency_overrides[get_current_user] = mock_non_admin

        try:
            response = client.get("/v0/admin/demos")

            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_list_demos_success(self, client: TestClient, db_session: Session) -> None:
        """Test list demos returns demo videos for admin."""
        from app.services import video_service

        # Create a demo video
        demo_video = video_service.create_video_record(
            db=db_session,
            filename="demo.mp4",
            file_path="storage/demo.mp4",
            file_size=1024,
            user_id=settings.DEMO_USER_ID,
            content_type="video/mp4",
            duration=1.0,
            fps=30.0,
            width=640,
            height=480,
            frame_count=30,
            is_demo=True,
        )

        try:
            response = client.get("/v0/admin/demos")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            # Should include the demo video we created
            demo_ids = [item["id"] for item in data]
            assert demo_video.id in demo_ids
        finally:
            db_session.delete(demo_video)
            db_session.commit()

    def test_set_active_demo_requires_admin(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test set active demo endpoint requires admin access."""
        from app.services import video_service

        # Create a demo video
        demo_video = video_service.create_video_record(
            db=db_session,
            filename="demo.mp4",
            file_path="storage/demo.mp4",
            file_size=1024,
            user_id=settings.DEMO_USER_ID,
            content_type="video/mp4",
            duration=1.0,
            fps=30.0,
            width=640,
            height=480,
            frame_count=30,
            is_demo=True,
        )

        async def mock_non_admin() -> dict:
            return {
                "id": "11111111-1111-1111-1111-111111111111",
                "email": "user@example.com",
                "user_metadata": {},
            }

        app.dependency_overrides[get_current_user] = mock_non_admin

        try:
            response = client.post(f"/v0/admin/demos/{demo_video.id}/set-active")

            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()
            db_session.delete(demo_video)
            db_session.commit()

    def test_analyze_demo_pose_requires_admin(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test analyze demo pose endpoint requires admin access."""
        from app.services import video_service

        # Create a demo video
        demo_video = video_service.create_video_record(
            db=db_session,
            filename="demo.mp4",
            file_path="storage/demo.mp4",
            file_size=1024,
            user_id=settings.DEMO_USER_ID,
            content_type="video/mp4",
            duration=1.0,
            fps=30.0,
            width=640,
            height=480,
            frame_count=30,
            is_demo=True,
        )

        async def mock_non_admin() -> dict:
            return {
                "id": "11111111-1111-1111-1111-111111111111",
                "email": "user@example.com",
                "user_metadata": {},
            }

        app.dependency_overrides[get_current_user] = mock_non_admin

        try:
            response = client.post(f"/v0/admin/demos/{demo_video.id}/analyze-pose")

            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()
            db_session.delete(demo_video)
            db_session.commit()


class TestGetUserById:
    """Tests for get_user_by_id utility function."""

    def test_get_user_by_id_local_profile(self) -> None:
        """Test get_user_by_id in local profile validates UUID format."""
        from app.utils.supabase_auth import get_user_by_id

        with patch.object(settings, "PROFILE", "local"):
            # Valid UUID format
            result = get_user_by_id("123e4567-e89b-12d3-a456-426614174000")
            assert result is not None
            assert result["id"] == "123e4567-e89b-12d3-a456-426614174000"
            assert result["email"] is None

            # Invalid UUID format
            result = get_user_by_id("not-a-uuid")
            assert result is None

    def test_get_user_by_id_production_valid_user(self) -> None:
        """Test get_user_by_id in production fetches from Supabase."""
        from app.utils.supabase_auth import get_user_by_id

        mock_user = Mock()
        mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
        mock_user.email = "user@example.com"
        mock_user.user_metadata = {}

        mock_response = Mock()
        mock_response.user = mock_user
        mock_response.error = None

        with (
            patch.object(settings, "PROFILE", "production"),
            patch("app.utils.supabase_auth.get_supabase_client") as mock_get_client,
        ):
            mock_client = Mock()
            mock_client.auth.admin.get_user_by_id.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = get_user_by_id("123e4567-e89b-12d3-a456-426614174000")

            assert result is not None
            assert result["id"] == "123e4567-e89b-12d3-a456-426614174000"
            assert result["email"] == "user@example.com"

    def test_get_user_by_id_production_user_not_found(self) -> None:
        """Test get_user_by_id returns None when user doesn't exist."""
        from app.utils.supabase_auth import get_user_by_id

        mock_response = Mock()
        mock_response.user = None
        mock_response.error = Mock()
        mock_response.error.message = "User not found"

        with (
            patch.object(settings, "PROFILE", "production"),
            patch("app.utils.supabase_auth.get_supabase_client") as mock_get_client,
        ):
            mock_client = Mock()
            mock_client.auth.admin.get_user_by_id.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = get_user_by_id("123e4567-e89b-12d3-a456-426614174000")

            assert result is None

    def test_get_user_by_id_production_exception_handling(self) -> None:
        """Test get_user_by_id handles exceptions gracefully."""
        from app.utils.supabase_auth import get_user_by_id

        with (
            patch.object(settings, "PROFILE", "production"),
            patch("app.utils.supabase_auth.get_supabase_client") as mock_get_client,
        ):
            mock_client = Mock()
            mock_client.auth.admin.get_user_by_id.side_effect = Exception("API error")
            mock_get_client.return_value = mock_client

            result = get_user_by_id("123e4567-e89b-12d3-a456-426614174000")

            assert result is None
