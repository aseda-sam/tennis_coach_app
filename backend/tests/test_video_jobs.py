"""Contract tests for video jobs endpoint."""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.video import Video
from app.models.video_job import VideoJob


class TestVideoJobsAPI:
    """Test video jobs endpoint contracts."""

    def test_get_jobs_returns_empty_list_for_new_user(
        self, client: TestClient, test_user_id: str
    ) -> None:
        """Contract: GET /v0/videos/jobs returns empty list if no jobs."""
        response = client.get("/v0/videos/jobs")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_jobs_filters_by_status(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Contract: status query param filters results."""
        # Arrange: Create test video
        video = Video(
            filename="test_jobs_video.mp4",
            file_path="/path/to/test_jobs_video.mp4",
            file_size=1000,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        # Create jobs with different statuses
        queued_job = VideoJob(
            video_id=video.id,
            user_id=test_user_id,
            job_type="pose_detection",
            status="queued",
        )
        processing_job = VideoJob(
            video_id=video.id,
            user_id=test_user_id,
            job_type="pose_detection",
            status="processing",
            started_at=datetime.utcnow(),
        )
        completed_job = VideoJob(
            video_id=video.id,
            user_id=test_user_id,
            job_type="pose_detection",
            status="completed",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
        db_session.add_all([queued_job, processing_job, completed_job])
        db_session.commit()

        # Act: Filter by active statuses
        response = client.get("/v0/videos/jobs?status=queued,processing")

        # Assert
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 2
        for job in jobs:
            assert job["status"] in ["queued", "processing"]

    def test_get_jobs_only_returns_user_jobs(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Contract: endpoint only returns jobs for authenticated user."""
        # Arrange: Create videos for different users
        user_video = Video(
            filename="user_video.mp4",
            file_path="/path/to/user_video.mp4",
            file_size=1000,
            user_id=test_user_id,
        )
        other_user_video = Video(
            filename="other_video.mp4",
            file_path="/path/to/other_video.mp4",
            file_size=1000,
            user_id="other-user-id",
        )
        db_session.add_all([user_video, other_user_video])
        db_session.commit()

        # Create jobs for both users
        user_job = VideoJob(
            video_id=user_video.id,
            user_id=test_user_id,
            job_type="pose_detection",
            status="queued",
        )
        other_job = VideoJob(
            video_id=other_user_video.id,
            user_id="other-user-id",
            job_type="pose_detection",
            status="queued",
        )
        db_session.add_all([user_job, other_job])
        db_session.commit()

        # Act
        response = client.get("/v0/videos/jobs")

        # Assert: Only user's jobs returned
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["id"] == str(user_job.id)
        assert jobs[0]["video_id"] == user_video.id

    def test_get_jobs_returns_expected_fields(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Contract: response includes all expected fields."""
        # Arrange: Create test video and job
        video = Video(
            filename="test_fields_video.mp4",
            file_path="/path/to/test_fields_video.mp4",
            file_size=1000,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        job = VideoJob(
            video_id=video.id,
            user_id=test_user_id,
            job_type="pose_detection",
            status="processing",
            rq_job_id="rq-job-123",
            started_at=datetime.utcnow(),
        )
        db_session.add(job)
        db_session.commit()

        # Act
        response = client.get("/v0/videos/jobs")

        # Assert: All expected fields present
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        job_data = jobs[0]

        assert "id" in job_data
        assert "video_id" in job_data
        assert "job_type" in job_data
        assert "status" in job_data
        assert "created_at" in job_data
        assert job_data["video_id"] == video.id
        assert job_data["job_type"] == "pose_detection"
        assert job_data["status"] == "processing"
        assert job_data["started_at"] is not None

    def test_analyze_video_creates_job_record(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Contract: POST /v0/analysis/videos/{id} creates VideoJob immediately."""
        # Arrange: Create test video
        video = Video(
            filename="test_analyze_video.mp4",
            file_path="/path/to/test_analyze_video.mp4",
            file_size=1000,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        # Act: Start analysis (will fail at RQ enqueue, but job should be created)
        # Note: This test assumes Redis is not available or we mock it
        client.post(
            f"/v0/analysis/videos/{video.id}",
            json={"analysis_type": "pose_only", "confidence_threshold": 0.7},
        )

        # Assert: Job record exists in database
        # Even if RQ enqueue fails, VideoJob should be created
        jobs = db_session.query(VideoJob).filter(VideoJob.video_id == video.id).all()
        assert len(jobs) >= 1  # At least one job created

        # Verify job has expected fields
        job = jobs[0]
        assert job.video_id == video.id
        assert job.user_id == test_user_id
        assert job.job_type == "pose_only"
        assert job.status in [
            "queued",
            "failed",
        ]  # queued if created, failed if RQ unavailable

    def test_get_job_by_id_returns_job(
        self, client: TestClient, db_session: Session, test_user_id: str
    ) -> None:
        """Contract: GET /v0/videos/jobs/{job_id} returns a single job."""
        video = Video(
            filename="test_single_job_video.mp4",
            file_path="/path/to/test_single_job_video.mp4",
            file_size=1000,
            user_id=test_user_id,
        )
        db_session.add(video)
        db_session.commit()

        job = VideoJob(
            video_id=video.id,
            user_id=test_user_id,
            job_type="pose_only",
            status="queued",
        )
        db_session.add(job)
        db_session.commit()

        response = client.get(f"/v0/videos/jobs/{job.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job.id)
        assert data["video_id"] == video.id
        assert data["status"] == "queued"

    def test_get_job_by_id_returns_404_for_missing_job(
        self, client: TestClient
    ) -> None:
        """Contract: GET /v0/videos/jobs/{job_id} returns 404 when missing."""
        response = client.get("/v0/videos/jobs/00000000-0000-0000-0000-000000000999")

        assert response.status_code == 404
