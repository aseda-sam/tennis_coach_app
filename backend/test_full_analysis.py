#!/usr/bin/env python3
"""
Test script for full analysis pipeline with racket detection.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.core.database import get_db
from app.services.cv_service import cv_service
from app.services.video_service import get_video_by_id


def test_full_analysis():
    """Test the full analysis pipeline with racket detection."""

    print("🔍 Full Analysis Pipeline Test")
    print("=" * 50)

    # Get the video
    db = next(get_db())
    video = get_video_by_id(db, 9)

    if not video:
        print("❌ No video found")
        return

    video_path = Path(video.file_path)
    print(f"📹 Testing on: {video.filename}")
    print(f"Video path: {video_path}")

    # Run full analysis
    print("\n🚀 Running full analysis pipeline...")
    results = cv_service.analyze_video(
        video_path=video_path,
        include_pose=True,
        confidence_threshold=0.3,
        video_quality_level="good",
    )

    if "error" in results:
        print(f"❌ Analysis failed: {results['error']}")
        return

    # Display results
    print("\n📊 Analysis Results:")
    print(f"  Frames processed: {results['frames_processed']}")

    # Ball detection results
    ball_summary = results["analysis_summary"]
    print("\n🎾 Ball Detection:")
    print(f"  Frames with balls: {ball_summary['frames_with_balls']}")
    print(f"  Total ball detections: {ball_summary['total_ball_detections']}")
    print(f"  Detection rate: {ball_summary['detection_rate']:.1%}")

    # Racket detection results
    print("\n🎾 Racket Detection:")
    print(f"  Frames with rackets: {ball_summary['frames_with_rackets']}")
    print(f"  Total racket detections: {ball_summary['total_racket_detections']}")
    print(f"  Racket detection rate: {ball_summary['racket_detection_rate']:.1%}")
    print(
        f"  Frames with racket positions: {ball_summary['frames_with_racket_positions']}"
    )

    # Pose detection results
    print("\n👤 Pose Detection:")
    print(f"  Frames with pose: {ball_summary['frames_with_pose']}")
    print(f"  Pose detection rate: {ball_summary['pose_detection_rate']:.1%}")

    # Timing information
    print("\n⏱️ Timing Breakdown:")
    for stage, duration in results["timing"].items():
        print(f"  {stage}: {duration:.3f}s")

    # Sample detections
    print("\n📋 Sample Detections:")

    # Sample ball detections
    ball_detections = results["ball_detections"]
    total_balls = sum(len(d) for d in ball_detections)
    print(f"  Total ball detections: {total_balls}")

    # Sample racket detections
    racket_detections = results["racket_detections"]
    total_rackets = sum(len(d) for d in racket_detections)
    print(f"  Total racket detections: {total_rackets}")

    # Sample racket positions
    racket_positions = results["racket_positions"]
    valid_positions = sum(1 for r in racket_positions if r is not None)
    print(f"  Valid racket positions: {valid_positions}")

    # Show some sample racket positions
    print("\n🎾 Sample Racket Positions:")
    for i, position in enumerate(racket_positions):
        if position and i < 5:  # Show first 5
            print(
                f"  Frame {i}: score={position['score']:.3f}, "
                f"closest_wrist={position['closest_wrist']}, "
                f"distance_to_wrist={position['distance_to_wrist']:.1f}"
            )

    print("\n✅ Full analysis test completed!")
    print(f"Annotated video: {results['annotated_video_path']}")


if __name__ == "__main__":
    test_full_analysis()
