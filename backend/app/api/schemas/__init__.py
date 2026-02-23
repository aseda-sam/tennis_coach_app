"""API schemas package."""

from app.api.schemas.background_tasks import AnalysisRequest, AnalysisResponse
from app.api.schemas.common import (
    ErrorCodes,
    ErrorResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
)
from app.api.schemas.overlay_data import PoseFrame, PoseKeypoint, PoseOverlayData
from app.api.schemas.player import (
    PlayerCreate,
    PlayerDeleteResponse,
    PlayerInfo,
    PlayerListItem,
    PlayerUpdate,
)
from app.api.schemas.serve_biomechanics import (
    BiomechanicsReportResponse,
    MetricValueResponse,
    PhaseWindowResponse,
)
from app.api.schemas.serve_detection import (
    AcceptProposalRequest,
    BulkAcceptRequest,
    BulkAcceptResponse,
    ClearProposalsResponse,
    DetectionStatusResponse,
    EditProposalRequest,
    ProposeResponse,
    RejectByConfidenceRequest,
    RejectByConfidenceResponse,
    ServeWindowProposalInfo,
)
from app.api.schemas.serve_window import (
    ServeWindowCreate,
    ServeWindowInfo,
    ServeWindowUpdate,
)
from app.api.schemas.video import (
    BallContactTimestampsResponse,
    BulkAnalysisStatusRequest,
    BulkAnalysisStatusResponse,
    VideoAnalysisStatus,
    VideoDeleteResponse,
    VideoInfo,
    VideoJobResponse,
    VideoListItem,
    VideoMetadataUpdateRequest,
    VideoSignedUrlResponse,
    VideoUploadResponse,
)

__all__ = [
    "AcceptProposalRequest",
    "AnalysisRequest",
    "AnalysisResponse",
    "BallContactTimestampsResponse",
    "BiomechanicsReportResponse",
    "BulkAcceptRequest",
    "BulkAcceptResponse",
    "BulkAnalysisStatusRequest",
    "BulkAnalysisStatusResponse",
    "ClearProposalsResponse",
    "DetectionStatusResponse",
    "EditProposalRequest",
    "ErrorCodes",
    "ErrorResponse",
    "MetricValueResponse",
    "PaginatedResponse",
    "PaginationParams",
    "PhaseWindowResponse",
    "PlayerCreate",
    "PlayerDeleteResponse",
    "PlayerInfo",
    "PlayerListItem",
    "PlayerUpdate",
    "PoseFrame",
    "PoseKeypoint",
    "PoseOverlayData",
    "ProposeResponse",
    "RejectByConfidenceRequest",
    "RejectByConfidenceResponse",
    "ServeWindowCreate",
    "ServeWindowInfo",
    "ServeWindowProposalInfo",
    "ServeWindowUpdate",
    "SuccessResponse",
    "VideoAnalysisStatus",
    "VideoDeleteResponse",
    "VideoInfo",
    "VideoJobResponse",
    "VideoListItem",
    "VideoMetadataUpdateRequest",
    "VideoSignedUrlResponse",
    "VideoUploadResponse",
]
