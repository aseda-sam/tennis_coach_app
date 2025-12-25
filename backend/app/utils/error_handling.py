"""Centralized error handling utilities."""

import logging
import re
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.api.schemas.common import ErrorCodes

logger = logging.getLogger(__name__)


class APIError(HTTPException):
    """Custom API error with standardized format."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.error_code = error_code
        self.details = details or {}


def create_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Create a standardized error response."""

    error_data = {
        "error": {"code": error_code, "message": message, "details": details or {}}
    }

    return JSONResponse(status_code=status_code, content=error_data)


def handle_validation_error(field: str, value: str, message: str) -> APIError:
    """Handle validation errors."""
    return APIError(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code=ErrorCodes.VALIDATION_ERROR,
        message=message,
        details={"field": field, "value": value},
    )


def handle_file_error(
    error_type: str, filename: str, details: Optional[str] = None
) -> APIError:
    """Handle file-related errors."""
    error_codes = {
        "too_large": ErrorCodes.FILE_TOO_LARGE,
        "unsupported_format": ErrorCodes.UNSUPPORTED_FORMAT,
        "upload_failed": ErrorCodes.UPLOAD_FAILED,
        "not_found": ErrorCodes.VIDEO_NOT_FOUND,
    }

    error_messages = {
        "too_large": f"File {filename} exceeds maximum size limit",
        "unsupported_format": f"File format not supported for {filename}",
        "upload_failed": f"Failed to upload {filename}",
        "not_found": f"Video {filename} not found",
    }

    return APIError(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code=error_codes.get(error_type, ErrorCodes.VALIDATION_ERROR),
        message=error_messages.get(error_type, f"File error: {error_type}"),
        details={"filename": filename, "details": details},
    )


def handle_processing_error(operation: str, details: Optional[str] = None) -> APIError:
    """Handle processing errors."""
    return APIError(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=ErrorCodes.PROCESSING_FAILED,
        message=f"{operation} failed",
        details={"operation": operation, "details": details},
    )


def handle_not_found_error(resource_type: str, resource_id: str) -> APIError:
    """Handle not found errors."""
    return APIError(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code=ErrorCodes.VIDEO_NOT_FOUND,
        message=f"{resource_type} {resource_id} not found",
        details={"resource_type": resource_type, "resource_id": resource_id},
    )


def _extract_resource_info_from_error(
    error: ValueError, context: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """
    Extract resource type and ID from error message or context.

    Args:
        error: The ValueError exception
        context: Optional context dictionary with resource IDs

    Returns:
        Tuple of (resource_type, resource_id)
    """
    resource_type = "resource"
    resource_id = "unknown"

    # Check context for common resource ID fields
    context_mapping = {
        "video_id": "video",
        "player_id": "player",
        "annotation_id": "annotation",
        "ball_contact_id": "ball_contact",
    }

    if context:
        for key, res_type in context_mapping.items():
            if key in context:
                resource_type = res_type
                resource_id = str(context[key])
                break

    # Try to extract from error message (e.g., "Video with ID 999 not found")
    match = re.search(r"(\w+)\s+with\s+ID\s+(\d+)", str(error), re.IGNORECASE)
    if match:
        resource_type = match.group(1).lower()
        resource_id = match.group(2)

    return resource_type, resource_id


def log_and_raise_error(
    error: Exception, operation: str, context: Optional[Dict[str, Any]] = None
) -> None:
    """Log error and raise appropriate API error."""

    logger.error(
        f"Error in {operation}: {error!s}",
        extra={"context": context or {}, "error": str(error)},
    )

    if isinstance(error, APIError):
        raise error

    # Convert common exceptions to API errors
    if isinstance(error, ValueError):
        error_message = str(error).lower()
        if "not found" in error_message:
            resource_type, resource_id = _extract_resource_info_from_error(
                error, context
            )
            raise handle_not_found_error(resource_type, resource_id)
        else:
            raise handle_validation_error("input", "invalid", str(error))
    elif isinstance(error, FileNotFoundError):
        raise handle_not_found_error("file", str(error))
    elif isinstance(error, OSError):
        raise handle_processing_error(operation, str(error))
    else:
        raise handle_processing_error(operation, str(error))


# Global exception handlers
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle custom API errors."""
    return create_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.detail,
        details=exc.details,
    )


async def validation_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle validation errors."""
    return create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        error_code=ErrorCodes.VALIDATION_ERROR,
        message=str(exc),
        details={"field": "input", "value": "invalid"},
    )


async def general_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general errors."""
    logger.error(f"Unhandled error: {exc!s}", exc_info=True)

    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=ErrorCodes.INTERNAL_ERROR,
        message="Internal server error",
        details={"error": str(exc)},
    )
