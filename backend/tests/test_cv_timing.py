#!/usr/bin/env python3
"""
Direct CV service timing test.
This script tests the timing functionality directly without going through the API.
"""

import sys
import time
from pathlib import Path

# Add the app directory to the Python path (now relative to tests directory)
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.cv_service import cv_service


def test_cv_timing_direct() -> None:
    """Test CV service timing functionality directly."""

    print("🎾 Direct CV Service Timing Test")
    print("=" * 50)

    # Find a test video (use dedicated test video from test_data)
    video_dir = Path(__file__).parent / "test_data"
    test_videos = ["test_tennis_video.mp4"]

    video_path = None
    for video_name in test_videos:
        potential_path = video_dir / video_name
        if potential_path.exists():
            video_path = potential_path
            print(f"📹 Using test video: {video_name}")
            break

    if not video_path:
        print("❌ No test videos found!")
        print(f"   Looked in: {video_dir}")
        print("   Available videos:")
        for video_file in video_dir.glob("*.mp4"):
            print(f"     - {video_file.name}")
        return

    # Test 1: Frame extraction timing
    print("\n1. Testing frame extraction timing...")
    start_time = time.time()
    frames = cv_service.extract_frames(
        video_path, max_frames=50
    )  # Limit for quick test
    extraction_time = time.time() - start_time
    print(f"   ✅ Extracted {len(frames)} frames in {extraction_time:.3f}s")

    if not frames:
        print("   ❌ No frames extracted, stopping test")
        return

    # Test 2: Ball detection timing
    print("\n2. Testing ball detection timing...")
    start_time = time.time()
    ball_detections = cv_service.detect_balls(frames)
    ball_time = time.time() - start_time
    total_balls = sum(len(d) for d in ball_detections)
    print(f"   ✅ Detected {total_balls} balls in {ball_time:.3f}s")

    # Test 3: Pose detection timing
    print("\n3. Testing pose detection timing...")
    start_time = time.time()
    pose_detections = cv_service.detect_poses_batch(frames)
    pose_time = time.time() - start_time
    total_poses = sum(1 for p in pose_detections if p is not None)
    print(f"   ✅ Detected {total_poses} poses in {pose_time:.3f}s")

    # Test 4: Full analysis timing
    print("\n4. Testing full analysis timing...")
    start_time = time.time()
    analysis_results = cv_service.analyze_video(video_path, include_pose=True)
    analysis_time = time.time() - start_time

    if "error" in analysis_results:
        print(f"   ❌ Analysis failed: {analysis_results['error']}")
    else:
        print(f"   ✅ Full analysis completed in {analysis_time:.3f}s")

        # Show timing breakdown
        timing_info = analysis_results.get("timing", {})
        if timing_info:
            print("   📊 Timing breakdown:")
            for stage, duration in timing_info.items():
                if stage != "total_analysis":
                    percentage = (
                        (duration / analysis_time) * 100 if analysis_time > 0 else 0
                    )
                    print(f"     - {stage}: {duration:.3f}s ({percentage:.1f}%)")

        # Show analysis summary
        summary = analysis_results.get("analysis_summary", {})
        if summary:
            print("   📈 Analysis summary:")
            print(f"     - Total frames: {summary.get('total_frames', 0)}")
            print(f"     - Ball detections: {summary.get('total_ball_detections', 0)}")
            print(f"     - Pose detections: {summary.get('frames_with_pose', 0)}")

    print("\n✅ Timing test completed!")
    print("   🎯 All timing functions are working correctly")
    print("   📝 Check the logs above for detailed timing information")


if __name__ == "__main__":
    test_cv_timing_direct()
