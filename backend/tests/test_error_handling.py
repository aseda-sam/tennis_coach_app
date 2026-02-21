"""Unit tests for error_handling utilities.

Tests handle_service_error() branch behaviour: each exception type/message
maps to the correct HTTP status code, and the error contract shape is stable.
"""

import pytest
from fastapi import HTTPException, status

from app.api.schemas.common import ErrorCodes
from app.utils.error_handling import APIError, handle_service_error


class TestHandleServiceError:
    """Unit tests for handle_service_error()."""

    # --- ValueError branches ---

    def test_value_error_not_found_raises_404(self) -> None:
        with pytest.raises(APIError) as exc_info:
            handle_service_error(ValueError("Video with ID 1 not found"), "op", {})
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_value_error_not_found_case_insensitive(self) -> None:
        with pytest.raises(APIError) as exc_info:
            handle_service_error(ValueError("Player NOT FOUND"), "op", {})
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_value_error_access_denied_raises_403(self) -> None:
        with pytest.raises(APIError) as exc_info:
            handle_service_error(
                ValueError("Access denied for this resource"), "op", {}
            )
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    def test_value_error_forbidden_raises_403(self) -> None:
        with pytest.raises(APIError) as exc_info:
            handle_service_error(ValueError("Forbidden: demo video"), "op", {})
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    def test_value_error_other_raises_400(self) -> None:
        with pytest.raises(APIError) as exc_info:
            handle_service_error(ValueError("start must be before end"), "op", {})
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_value_error_400_uses_validation_error_code(self) -> None:
        with pytest.raises(APIError) as exc_info:
            handle_service_error(ValueError("bad input"), "op", {})
        assert exc_info.value.error_code == ErrorCodes.VALIDATION_ERROR

    def test_value_error_message_preserved(self) -> None:
        with pytest.raises(APIError) as exc_info:
            handle_service_error(ValueError("something is wrong"), "op", {})
        assert "something is wrong" in exc_info.value.detail

    # --- HTTPException passthrough ---

    def test_http_exception_reraised_unchanged(self) -> None:
        original = HTTPException(status_code=409, detail="Conflict")
        with pytest.raises(HTTPException) as exc_info:
            handle_service_error(original, "op", {})
        assert exc_info.value is original
        assert exc_info.value.status_code == 409

    def test_api_error_reraised_unchanged(self) -> None:
        original = APIError(
            status_code=422,
            error_code="CUSTOM",
            message="custom error",
        )
        with pytest.raises(APIError) as exc_info:
            handle_service_error(original, "op", {})
        assert exc_info.value is original

    # --- Generic exception → 500 ---

    def test_runtime_error_raises_500(self) -> None:
        with pytest.raises(APIError) as exc_info:
            handle_service_error(RuntimeError("unexpected crash"), "op", {})
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_os_error_raises_500(self) -> None:
        with pytest.raises(APIError) as exc_info:
            handle_service_error(OSError("disk full"), "op", {})
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # --- Context aids resource extraction for 404 ---

    def test_not_found_with_video_id_context(self) -> None:
        with pytest.raises(APIError) as exc_info:
            handle_service_error(
                ValueError("not found"),
                "get_video",
                {"video_id": 42},
            )
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "42" in str(exc_info.value.details)
