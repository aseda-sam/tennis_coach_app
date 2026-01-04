"""
RQ monitoring utilities for queue statistics and job inspection.
"""

import logging
from typing import Any, Dict, List, Optional

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError
from rq import Worker
from rq.job import Job, NoSuchJobError

from app.core.redis_config import analysis_queue, default_queue, redis_conn

logger = logging.getLogger(__name__)


def get_queue_stats() -> Dict[str, Any]:
    """
    Get queue and worker statistics.

    Returns:
        Dictionary with queue lengths, worker counts, and job status distribution
    """
    try:
        # Get queue lengths
        analysis_queue_length = len(analysis_queue)
        default_queue_length = len(default_queue)

        # Get worker statistics
        workers = Worker.all(connection=redis_conn)
        active_workers = len(workers)

        # Count jobs by status
        status_counts: Dict[str, int] = {}
        total_jobs = 0

        for queue in [analysis_queue, default_queue]:
            for job_id in queue.job_ids:
                try:
                    job = Job.fetch(job_id, connection=redis_conn)
                    rq_status = job.get_status()
                    status_counts[rq_status] = status_counts.get(rq_status, 0) + 1
                    total_jobs += 1
                except (
                    NoSuchJobError,
                    RedisConnectionError,
                    RedisTimeoutError,
                    AttributeError,
                ) as e:
                    logger.debug(f"Skipping job {job_id}: {e}")
                    continue

        return {
            "analysis_queue_length": analysis_queue_length,
            "default_queue_length": default_queue_length,
            "total_queued": analysis_queue_length + default_queue_length,
            "active_workers": active_workers,
            "total_jobs": total_jobs,
            "status_counts": status_counts,
        }

    except (RedisConnectionError, RedisTimeoutError, AttributeError) as e:
        logger.error(f"Error getting queue stats: {e}")
        return {
            "analysis_queue_length": 0,
            "default_queue_length": 0,
            "total_queued": 0,
            "active_workers": 0,
            "total_jobs": 0,
            "status_counts": {},
        }


def list_failed_jobs(limit: int = 10) -> List[Dict[str, Any]]:
    """
    List failed jobs with error details.

    Args:
        limit: Maximum number of failed jobs to return

    Returns:
        List of failed job dictionaries with error details
    """
    failed_jobs = []

    try:
        # Check both queues
        for queue in [analysis_queue, default_queue]:
            for job_id in queue.job_ids:
                try:
                    job = Job.fetch(job_id, connection=redis_conn)
                    if job.is_failed:
                        failed_jobs.append(
                            {
                                "job_id": job.id,
                                "func_name": job.func_name
                                if hasattr(job, "func_name")
                                else "unknown",
                                "args": job.args if hasattr(job, "args") else [],
                                "error": str(job.exc_info)
                                if job.exc_info
                                else "Unknown error",
                                "failed_at": job.ended_at.isoformat()
                                if hasattr(job, "ended_at") and job.ended_at
                                else None,
                            }
                        )
                        if len(failed_jobs) >= limit:
                            return failed_jobs
                except (
                    NoSuchJobError,
                    RedisConnectionError,
                    RedisTimeoutError,
                    AttributeError,
                ) as e:
                    logger.warning(f"Failed to fetch job {job_id}: {e}")
                    continue

    except (RedisConnectionError, RedisTimeoutError) as e:
        logger.error(f"Error listing failed jobs: {e}")

    return failed_jobs


def requeue_failed_job(job_id: str) -> bool:
    """
    Requeue a failed job.

    Args:
        job_id: UUID string identifier of the failed job

    Returns:
        True if job was requeued, False otherwise
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)

        if not job.is_failed:
            logger.warning(f"Job {job_id} is not in failed state")
            return False

        # Requeue the job
        job.requeue()
        logger.info(f"Requeued failed job {job_id}")
        return True

    except (
        NoSuchJobError,
        RedisConnectionError,
        RedisTimeoutError,
        AttributeError,
    ) as e:
        logger.error(f"Error requeuing job {job_id}: {e}")
        return False


def get_job_execution_time(job_id: str) -> Optional[float]:
    """
    Get job execution time in seconds.

    Args:
        job_id: UUID string identifier of the job

    Returns:
        Execution time in seconds, or None if job not found or not finished
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)

        if not job.is_finished:
            return None

        if (
            hasattr(job, "started_at")
            and hasattr(job, "ended_at")
            and job.started_at
            and job.ended_at
        ):
            delta = job.ended_at - job.started_at
            return delta.total_seconds()

        return None

    except (
        NoSuchJobError,
        RedisConnectionError,
        RedisTimeoutError,
        AttributeError,
    ) as e:
        logger.warning(f"Error getting execution time for job {job_id}: {e}")
        return None
