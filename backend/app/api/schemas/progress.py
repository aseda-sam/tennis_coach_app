"""Progress overview API schemas."""

from typing import List, Literal

from pydantic import BaseModel, Field


class ProgressMetricDataPoint(BaseModel):
    """A single data point representing one video's aggregated metrics."""

    date: str = Field(description="Date of the video (YYYY-MM-DD)")
    avg: float = Field(description="Average value for this video")
    count: int = Field(ge=0, description="Number of serves in this video")


class ElbowAngleMetric(BaseModel):
    """Elbow angle at contact aggregated metrics."""

    current_avg: float = Field(description="Average elbow angle in current window")
    previous_avg: float | None = Field(
        default=None, description="Average elbow angle in previous equivalent window"
    )
    trend: Literal["improving", "declining", "stable"] = Field(
        description="Trend compared to previous window"
    )
    consistency: float = Field(ge=0, description="Standard deviation of elbow angle")
    consistency_rating: Literal["excellent", "good", "fair", "needs_work"] = Field(
        description="Rating based on standard deviation thresholds"
    )
    data_points: List[ProgressMetricDataPoint] = Field(
        description="Per-video data points ordered by date"
    )


class KneeBendMetric(BaseModel):
    """Knee bend detection rate metrics."""

    current_rate: float = Field(
        ge=0, le=1, description="Percentage of serves with knee bend detected"
    )
    previous_rate: float | None = Field(
        default=None, description="Knee bend rate in previous equivalent window"
    )
    trend: Literal["improving", "declining", "stable"] = Field(
        description="Trend compared to previous window"
    )
    data_points: List[ProgressMetricDataPoint] = Field(
        description="Per-video data points ordered by date"
    )


class CourtSideDistribution(BaseModel):
    """Distribution of serves by court side."""

    deuce: int = Field(ge=0, description="Number of serves from deuce side")
    ad: int = Field(ge=0, description="Number of serves from ad side")
    unknown: int = Field(ge=0, description="Number of serves with unknown court side")


class ProgressMetrics(BaseModel):
    """Container for all progress metrics."""

    elbow_angle: ElbowAngleMetric | None = Field(
        default=None, description="Elbow angle metrics (None if no data)"
    )
    knee_bend: KneeBendMetric | None = Field(
        default=None, description="Knee bend metrics (None if no data)"
    )


class ProgressResponse(BaseModel):
    """Top-level progress overview response."""

    time_period: str = Field(description="Time period filter applied")
    total_serves: int = Field(ge=0, description="Total serve attempts in window")
    total_videos: int = Field(ge=0, description="Total videos in window")
    metrics: ProgressMetrics = Field(description="Aggregated metrics")
    court_side: CourtSideDistribution = Field(
        description="Court side serve distribution"
    )
