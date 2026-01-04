#!/usr/bin/env python
"""Start RQ worker with proper configuration."""

import multiprocessing
import os
import sys
from pathlib import Path

# CRITICAL: Set this BEFORE any other imports on macOS
# This disables the fork safety check that causes crashes
# Must be set before any imports that might use Objective-C
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

# On macOS, configure multiprocessing to use spawn instead of fork
# This is more compatible with libraries that use Objective-C
if sys.platform == "darwin":  # macOS
    try:
        multiprocessing.set_start_method("spawn", force=True)
    except RuntimeError:
        # Already set, that's fine
        pass

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rq import Worker

from app.core.redis_config import (
    analysis_queue,
    default_queue,
    get_worker_info,
    redis_conn,
)

if __name__ == "__main__":
    # Verify environment variable is set
    fork_safety = os.environ.get("OBJC_DISABLE_INITIALIZE_FORK_SAFETY")
    if not fork_safety:
        print("WARNING: OBJC_DISABLE_INITIALIZE_FORK_SAFETY not set!")
        print("This may cause crashes on macOS. Setting it now...")
        os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
    else:
        print(f"✓ Fork safety disabled: {fork_safety}")

    # Get worker info
    info = get_worker_info()
    recommended = info["recommended_workers"]

    print("=" * 60)
    print("RQ Worker Startup")
    print("=" * 60)
    print(f"Environment: {info['environment']}")
    print(f"CPU Cores: {info['cpu_count']}")
    print(f"Recommended Workers: {recommended}")
    print(f"Redis URL: {info['redis_url']}")
    print(f"Platform: {sys.platform}")
    print(f"Multiprocessing start method: {multiprocessing.get_start_method()}")
    print("=" * 60)
    print(f"\nStarting 1 worker (start {recommended - 1} more in separate terminals)")
    print("Listening on queues: default, analysis")
    print("\nPress Ctrl+C to stop\n")

    try:
        # Create worker with connection
        worker = Worker(
            [default_queue, analysis_queue],
            connection=redis_conn,
            name=f"worker-{os.getpid()}",
        )
        worker.work()
    except KeyboardInterrupt:
        print("\n\nWorker stopped by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
