#!/usr/bin/env python3
"""
Test posture analysis with real video data from the database.

This script connects to the database and tests posture analysis
with actual video, pose detection, and ball contact data.
"""

import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.database import SessionLocal
from app.models.ball_contact import BallContact
from app.models.pose_detection import PoseDetection
from app.models.video import Video
from app.services.posture_analysis import (
    analyze_contact_posture,
    calculate_elbow_angle,
    get_pose_at_contact,
)


def test_with_real_data(video_id: int = 1) -> None:
    """Test posture analysis with real database data."""
    print(f"🔍 Testing posture analysis with video ID {video_id}")

    # Create database session
    db = SessionLocal()

    try:
        # Check if video exists
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            print(f"❌ Video with ID {video_id} not found")
            return

        print(f"✅ Found video: {video.filename}")
        print(
            f"   Duration: {video.duration:.1f}s"
            if video.duration
            else "   Duration: Unknown"
        )
        print(f"   FPS: {video.fps}" if video.fps else "   FPS: Unknown")

        # Check for pose detection
        pose_detection = (
            db.query(PoseDetection)
            .filter(
                PoseDetection.video_id == video_id, PoseDetection.status == "completed"
            )
            .first()
        )

        if not pose_detection:
            print("❌ No completed pose detection found for this video")
            print("   Run pose detection analysis first")
            return

        print("✅ Found pose detection:")
        print(f"   Total frames: {pose_detection.total_frames}")
        print(f"   Frames with poses: {pose_detection.frames_with_poses}")
        print(f"   Detection rate: {pose_detection.detection_rate:.1%}")

        # Check for ball contacts
        ball_contacts = (
            db.query(BallContact).filter(BallContact.video_id == video_id).all()
        )

        if not ball_contacts:
            print("❌ No ball contacts found for this video")
            print("   Create some ball contacts first")
            return

        print(f"✅ Found {len(ball_contacts)} ball contact(s)")

        # Test posture analysis for each contact
        for i, contact in enumerate(ball_contacts, 1):
            print(f"\n🎾 Testing contact {i}:")
            print(f"   Timestamp: {contact.video_timestamp:.2f}s")
            print(f"   Hand: {contact.contact_hand}")
            print(f"   Stroke: {contact.stroke_type}")

            # Test pose lookup
            pose_landmarks = get_pose_at_contact(contact, pose_detection)

            if pose_landmarks:
                print("   ✅ Found pose data at contact moment")
                print(f"   Keypoints available: {list(pose_landmarks.keys())}")

                # Test elbow angle calculation
                elbow_angle = calculate_elbow_angle(pose_landmarks)

                if elbow_angle is not None:
                    print(f"   🎯 Elbow angle: {elbow_angle:.1f}°")

                    # Provide some context
                    if elbow_angle < 90:
                        print("   📝 Analysis: Very bent elbow (acute angle)")
                    elif elbow_angle < 120:
                        print("   📝 Analysis: Moderately bent elbow")
                    elif elbow_angle < 150:
                        print("   📝 Analysis: Slightly bent elbow")
                    else:
                        print("   📝 Analysis: Nearly straight arm")
                else:
                    print("   ❌ Could not calculate elbow angle")
            else:
                print("   ❌ No pose data found at contact moment")

        # Test the full analysis function
        print("\n🔬 Testing full analysis function:")
        for i, contact in enumerate(ball_contacts, 1):
            print(f"\n   Contact {i} (ID: {contact.id}):")
            elbow_angle = analyze_contact_posture(db, contact.id)

            if elbow_angle is not None:
                print(f"   ✅ Analysis successful: {elbow_angle:.1f}°")
            else:
                print("   ❌ Analysis failed")

    except (ValueError, KeyError, AttributeError, ConnectionError) as e:
        print(f"❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()

    finally:
        db.close()


def main() -> int:
    """Main function."""
    print("🚀 Real Data Posture Analysis Test\n")

    # Test with video ID 1
    test_with_real_data(video_id=4)

    print("\n✅ Test completed!")
    return 0


if __name__ == "__main__":
    exit(main())
