#!/usr/bin/env python
"""Start RQ worker with proper configuration."""

import contextlib
import multiprocessing
import os
import socket
import sys
import time
from pathlib import Path

# CRITICAL: Set this BEFORE any other imports on macOS
# This disables the fork safety check that causes crashes
# Must be set before any imports that might use Objective-C
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

# On macOS, configure multiprocessing to use spawn instead of fork
# This is more compatible with libraries that use Objective-C
if sys.platform == "darwin":  # macOS
    with contextlib.suppress(RuntimeError):
        # Already set, that's fine
        multiprocessing.set_start_method("spawn", force=True)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from redis.exceptions import ResponseError as RedisResponseError
from rq import Worker

from app.core.redis_config import (
    analysis_queue,
    default_queue,
    get_worker_info,
    redis_conn,
)


def cleanup_stale_workers() -> None:
    """Clean up stale worker registrations from Redis."""
    try:
        existing_workers = Worker.all(connection=redis_conn)
        if existing_workers:
            print(f"Found {len(existing_workers)} existing worker(s) in Redis")
            for worker in existing_workers:
                # Check if worker is actually alive by trying to access its connection
                try:
                    # If worker is alive, it will respond to ping
                    # If stale, this will fail or worker won't respond
                    if not worker.is_alive():
                        print(f"  Cleaning up stale worker: {worker.name}")
                        worker.register_death()
                    else:
                        print(
                            f"  Worker {worker.name} is still alive, skipping cleanup"
                        )
                except Exception:  # noqa: BLE001
                    # Worker registration exists but worker is not responding
                    print(f"  Cleaning up stale worker registration: {worker.name}")
                    try:
                        worker.register_death()
                    except Exception:  # noqa: BLE001
                        # If register_death fails, try to delete the key directly
                        try:
                            redis_conn.delete(f"rq:worker:{worker.name}")
                            redis_conn.delete(f"rq:worker:{worker.name}:birth")
                        except Exception:  # noqa: BLE001, S110
                            pass  # Ignore cleanup failures - worker may already be cleaned up
        else:
            print("No existing workers found in Redis")
    except RedisResponseError as e:
        print(f"Warning: Could not check for stale workers: {e}")
        print("Proceeding anyway...")
    except Exception as e:  # noqa: BLE001
        print(f"Warning: Could not check for stale workers: {e}")
        print("Proceeding anyway...")


def generate_worker_name() -> str:
    """Generate a unique worker name using hostname and PID."""
    hostname = socket.gethostname()
    pid = os.getpid()
    # Use container name if available (from docker-compose), otherwise hostname
    container_name = os.environ.get("HOSTNAME", hostname)
    return f"worker-{container_name}-{pid}"


if __name__ == "__main__":
    # Verify environment variable is set
    fork_safety = os.environ.get("OBJC_DISABLE_INITIALIZE_FORK_SAFETY")
    if not fork_safety:
        print("WARNING: OBJC_DISABLE_INITIALIZE_FORK_SAFETY not set!")
        print("This may cause crashes on macOS. Setting it now...")
        os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    else:
        print(f"✓ Fork safety disabled: {fork_safety}")

    # Clean up stale workers before starting
    print("\nChecking for stale worker registrations...")
    cleanup_stale_workers()

    # Get worker info
    info = get_worker_info()
    recommended = info["recommended_workers"]

    # Configure polling interval (dequeue timeout)
    # RQ derives dequeue_timeout from worker_ttl: max(1, worker_ttl - 15).
    # Use RQ_DEQUEUE_TIMEOUT to control polling frequency, and map it to worker_ttl.
    try:
        desired_dequeue_timeout = int(os.getenv("RQ_DEQUEUE_TIMEOUT", "60"))
    except ValueError:
        desired_dequeue_timeout = 60

    worker_ttl = max(30, desired_dequeue_timeout + 15)

    # Generate unique worker name
    worker_name = generate_worker_name()

    print("=" * 60)
    print("RQ Worker Startup")
    print("=" * 60)
    print(f"Profile: {info['profile']}")
    print(f"CPU Cores: {info['cpu_count']}")
    print(f"Recommended Workers: {recommended}")
    print(f"Redis URL: {info['redis_url']}")
    print(f"Platform: {sys.platform}")
    print(f"Multiprocessing start method: {multiprocessing.get_start_method()}")
    print(f"Worker Name: {worker_name}")
    print(f"Worker TTL: {worker_ttl}s")
    print(f"Dequeue Timeout: {max(1, worker_ttl - 15)}s")
    print("=" * 60)
    print(f"\nStarting 1 worker (start {recommended - 1} more in separate terminals)")
    print("Listening on queues: default, analysis")
    print("\nPress Ctrl+C to stop\n")

    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Create worker with connection
            worker = Worker(
                [default_queue, analysis_queue],
                connection=redis_conn,
                name=worker_name,
                worker_ttl=worker_ttl,
            )
            # Scheduler disabled to reduce Redis command usage (Upstash free tier).
            # Retries use interval=0 (immediate) so no scheduler needed.
            worker.work(with_scheduler=False)
            break  # Success, exit retry loop
        except ValueError as e:
            error_msg = str(e)
            if "active worker" in error_msg.lower() and retry_count < max_retries - 1:
                retry_count += 1
                print(
                    f"\n⚠️  Worker registration conflict detected (attempt {retry_count}/{max_retries})"
                )
                print("Cleaning up stale registrations and retrying...")
                cleanup_stale_workers()
                # Generate a new unique name for retry
                worker_name = generate_worker_name()
                print(f"Retrying with worker name: {worker_name}\n")
                continue
            else:
                # Max retries reached or different ValueError
                print(f"\n\nError: {e}")
                import traceback

                traceback.print_exc()
                sys.exit(1)
        except RedisResponseError as e:
            error_msg = str(e).lower()
            if "max requests limit exceeded" in error_msg:
                retry_count += 1
                if retry_count >= max_retries:
                    print(
                        "\n\nRedis quota exceeded repeatedly. "
                        "Max retries reached, exiting."
                    )
                    sys.exit(1)
                print("\n\nRedis quota exceeded. Worker will sleep and retry in 60s...")
                time.sleep(60)
                continue
            print(f"\n\nError: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\nWorker stopped by user")
            break
        except Exception as e:  # noqa: BLE001 - Worker script needs to catch all errors
            print(f"\n\nError: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)
