"""Common API schemas and response models."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: Dict[str, Any] = Field(
        description="Error details",
        json_schema_extra={
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": {"field": "filename", "value": "invalid.mp4"},
            }
        },
    )


class SuccessResponse(BaseModel):
    """Standard success response model."""

    message: str = Field(description="Success message")
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Response data if applicable"
    )


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    items: list[Any] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    size: int = Field(description="Items per page")
    pages: int = Field(description="Total number of pages")


# Standard error codes
class ErrorCodes:
    """Standard error codes for the API."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    VIDEO_NOT_FOUND = "VIDEO_NOT_FOUND"
    ANALYSIS_NOT_AVAILABLE = "ANALYSIS_NOT_AVAILABLE"
    UPLOAD_FAILED = "UPLOAD_FAILED"
    DELETE_FAILED = "DELETE_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
