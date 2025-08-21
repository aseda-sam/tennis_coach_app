#!/usr/bin/env python3
"""
Quick test to verify racket bounding box visualization.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import cv2

from app.core.database import get_db
from app.services.cv_service import cv_service
from app.services.video_service import get_video_by_id


def test_racket_visualization():
    """Test racket bounding box visualization on a few frames."""

    print("🎾 Racket Visualization Test")
    print("=" * 40)

    # Get the video
    db = next(get_db())
    video = get_video_by_id(db, 9)

    if not video:
        print("❌ No video found")
        return

    video_path = Path(video.file_path)
    print(f"📹 Testing on: {video.filename}")

    # Extract just a few frames for quick testing
    frames = cv_service.extract_frames(video_path, max_frames=10)

    if not frames:
        print("❌ No frames extracted")
        return

    print(f"📹 Processing {len(frames)} frames")

    # Run detection
    ball_detections = cv_service.detect_balls(frames, confidence_threshold=0.3)
    racket_detections = cv_service.detect_rackets(frames, confidence_threshold=0.3)
    pose_detections = cv_service.detect_poses_batch(frames)

    # Create annotated frames
    annotated_frames = []

    for i, frame in enumerate(frames):
        annotated_frame = frame.copy()

        # Draw ball detections (red)
        for detection in ball_detections[i]:
            bbox = detection["bbox"]
            cv2.rectangle(
                annotated_frame,
                (bbox[0], bbox[1]),
                (bbox[2], bbox[3]),
                (0, 0, 255),  # Red
                2,
            )
            cv2.putText(
                annotated_frame,
                f"Ball: {detection['confidence']:.2f}",
                (bbox[0], bbox[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
            )

        # Draw racket detections (blue)
        for detection in racket_detections[i]:
            bbox = detection["bbox"]
            cv2.rectangle(
                annotated_frame,
                (bbox[0], bbox[1]),
                (bbox[2], bbox[3]),
                (255, 0, 0),  # Blue
                2,
            )
            cv2.putText(
                annotated_frame,
                f"Racket: {detection['confidence']:.2f}",
                (bbox[0], bbox[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 0),
                1,
            )

        # Draw pose overlay (green)
        if pose_detections[i]:
            annotated_frame = cv_service.draw_pose_overlay(
                annotated_frame, pose_detections[i]
            )

        annotated_frames.append(annotated_frame)

        # Print detection counts for this frame
        ball_count = len(ball_detections[i])
        racket_count = len(racket_detections[i])
        pose_detected = pose_detections[i] is not None

        print(
            f"  Frame {i}: {ball_count} balls, {racket_count} rackets, pose: {pose_detected}"
        )

    # Save a sample frame to verify visualization
    if annotated_frames:
        sample_frame = annotated_frames[0]
        output_path = Path("../data/videos/processed/sample_racket_visualization.jpg")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cv2.imwrite(str(output_path), sample_frame)
        print(f"\n✅ Sample frame saved: {output_path}")
        print(
            "You can view this image to verify racket bounding boxes are drawn correctly."
        )

    # Count total detections
    total_balls = sum(len(d) for d in ball_detections)
    total_rackets = sum(len(d) for d in racket_detections)
    total_poses = sum(1 for p in pose_detections if p is not None)

    print("\n📊 Detection Summary:")
    print(f"  Total ball detections: {total_balls}")
    print(f"  Total racket detections: {total_rackets}")
    print(f"  Frames with pose: {total_poses}")

    print("\n✅ Visualization test completed!")


if __name__ == "__main__":
    test_racket_visualization()
