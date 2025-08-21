#!/usr/bin/env python3
"""
Test script for racket detection functionality.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.database import get_db
from app.services.cv_service import cv_service
from app.services.video_service import get_video_by_id


def test_racket_detection():
    """Test racket detection on an existing video."""

    # Get the first video from the database
    db = next(get_db())
    video = get_video_by_id(db, 9)  # Use video ID 9

    if not video:
        print("No video found in database")
        return

    video_path = Path(video.file_path)

    if not video_path.exists():
        print(f"Video file not found: {video_path}")
        return

    print(f"Testing racket detection on: {video.filename}")
    print(f"Video path: {video_path}")

    # Extract frames
    print("\n1. Extracting frames...")
    frames = cv_service.extract_frames(
        video_path, max_frames=50
    )  # Test with first 50 frames
    print(f"Extracted {len(frames)} frames")

    if not frames:
        print("No frames extracted")
        return

    # Test racket detection
    print("\n2. Testing racket detection...")
    racket_detections = cv_service.detect_rackets(frames, confidence_threshold=0.3)

    total_racket_detections = sum(len(d) for d in racket_detections)
    frames_with_rackets = sum(1 for d in racket_detections if d)

    print(f"Total racket detections: {total_racket_detections}")
    print(f"Frames with rackets: {frames_with_rackets}")
    print(f"Racket detection rate: {frames_with_rackets / len(frames) * 100:.1f}%")

    # Show some sample detections
    print("\n3. Sample racket detections:")
    for i, frame_detections in enumerate(racket_detections):
        if frame_detections:
            print(f"  Frame {i}: {len(frame_detections)} rackets")
            for j, detection in enumerate(frame_detections):
                print(
                    f"    Racket {j + 1}: confidence={detection['confidence']:.3f}, "
                    f"aspect_ratio={detection['aspect_ratio']:.2f}, "
                    f"area={detection['area']:.0f}"
                )
            if i >= 5:  # Show first 5 frames with detections
                break

    # Test pose detection for racket position estimation
    print("\n4. Testing pose detection...")
    pose_detections = cv_service.detect_poses_batch(frames)
    frames_with_pose = sum(1 for p in pose_detections if p is not None)
    print(f"Frames with pose: {frames_with_pose}")
    print(f"Pose detection rate: {frames_with_pose / len(frames) * 100:.1f}%")

    # Test racket position estimation
    print("\n5. Testing racket position estimation...")
    racket_positions = cv_service.estimate_racket_head_position(
        racket_detections, pose_detections
    )

    frames_with_racket_positions = sum(1 for r in racket_positions if r is not None)
    print(f"Frames with racket positions: {frames_with_racket_positions}")
    print(
        f"Racket position estimation rate: {frames_with_racket_positions / len(frames) * 100:.1f}%"
    )

    # Show some sample racket positions
    print("\n6. Sample racket positions:")
    for i, position in enumerate(racket_positions):
        if position:
            print(
                f"  Frame {i}: score={position['score']:.3f}, "
                f"closest_wrist={position['closest_wrist']}, "
                f"distance_to_wrist={position['distance_to_wrist']:.1f}"
            )
            if i >= 5:  # Show first 5 frames with positions
                break

    print("\n✅ Racket detection test completed!")


if __name__ == "__main__":
    test_racket_detection()
