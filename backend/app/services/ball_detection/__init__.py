"""Ball detection service for tennis ball tracking in video."""

from app.services.ball_detection.yolo_detection_service import (
    YoloBallDetectionService,
)

__all__ = ["YoloBallDetectionService"]
