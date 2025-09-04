#!/usr/bin/env python3
"""
Simple test script for posture analysis functionality.

This script tests the basic posture analysis functions without requiring
database setup or API endpoints.
"""

import json
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.models.ball_contact import BallContact
from app.models.pose_detection import PoseDetection
from app.services.posture_analysis import calculate_elbow_angle, get_pose_at_contact


def test_elbow_angle_calculation() -> bool:
    """Test elbow angle calculation with synthetic data."""
    print("🧪 Testing elbow angle calculation...")

    # Create synthetic pose landmarks (normalized coordinates 0-1)
    pose_landmarks = {
        "right_shoulder": [0.3, 0.2, 0.9],  # [x, y, confidence]
        "right_elbow": [0.4, 0.4, 0.8],  # [x, y, confidence]
        "right_wrist": [0.5, 0.6, 0.7],  # [x, y, confidence]
        "left_shoulder": [0.7, 0.2, 0.9],
        "left_elbow": [0.6, 0.4, 0.8],
        "left_wrist": [0.5, 0.6, 0.7],
    }

    # Calculate elbow angle
    angle = calculate_elbow_angle(pose_landmarks)

    if angle is not None:
        print(f"✅ Elbow angle calculated: {angle:.1f}°")
        return True
    else:
        print("❌ Failed to calculate elbow angle")
        return False


def test_elbow_angle_with_missing_data() -> bool:
    """Test elbow angle calculation with missing keypoints."""
    print("\n🧪 Testing elbow angle with missing data...")

    # Test with missing right arm data
    pose_landmarks = {
        "right_shoulder": [0.3, 0.2, 0.9],
        # Missing right_elbow and right_wrist
        "left_shoulder": [0.7, 0.2, 0.9],
        "left_elbow": [0.6, 0.4, 0.8],
        "left_wrist": [0.5, 0.6, 0.7],
    }

    angle = calculate_elbow_angle(pose_landmarks)

    if angle is not None:
        print(f"✅ Fallback to left arm worked: {angle:.1f}°")
        return True
    else:
        print("❌ Failed to fallback to left arm")
        return False


def test_elbow_angle_with_no_data() -> bool:
    """Test elbow angle calculation with no valid data."""
    print("\n🧪 Testing elbow angle with no valid data...")

    pose_landmarks = {
        "nose": [0.5, 0.1, 0.9],
        "left_eye": [0.48, 0.12, 0.8],
        # No arm keypoints
    }

    angle = calculate_elbow_angle(pose_landmarks)

    if angle is None:
        print("✅ Correctly returned None for missing arm data")
        return True
    else:
        print(f"❌ Should have returned None, got {angle}")
        return False


def test_pose_lookup_with_synthetic_data() -> bool:
    """Test pose lookup with synthetic data."""
    print("\n🧪 Testing pose lookup with synthetic data...")

    # Create synthetic ball contact
    ball_contact = BallContact()
    ball_contact.video_timestamp = 2.5  # 2.5 seconds into video

    # Create synthetic pose detection with frame data
    pose_detection = PoseDetection()

    # Create synthetic pose data for multiple frames
    synthetic_pose_data = []
    for frame_idx in range(100):  # 100 frames
        if frame_idx == 75:  # Frame 75 should match our timestamp (2.5s * 30fps)
            # Add pose data for this frame
            frame_data = {
                "right_shoulder": [0.3, 0.2, 0.9],
                "right_elbow": [0.4, 0.4, 0.8],
                "right_wrist": [0.5, 0.6, 0.7],
            }
        else:
            frame_data = None  # No pose detected in other frames

        synthetic_pose_data.append(frame_data)

    # Serialize the pose data
    pose_detection.pose_data = json.dumps(synthetic_pose_data)

    # Test pose lookup
    pose_landmarks = get_pose_at_contact(ball_contact, pose_detection)

    if pose_landmarks is not None:
        print("✅ Successfully found pose data at contact timestamp")
        print(f"   Found keypoints: {list(pose_landmarks.keys())}")
        return True
    else:
        print("❌ Failed to find pose data at contact timestamp")
        return False


def test_angle_calculation_accuracy() -> bool:
    """Test angle calculation with known values."""
    print("\n🧪 Testing angle calculation accuracy...")

    # Test with a 90-degree angle (right angle)
    pose_landmarks = {
        "right_shoulder": [0.0, 0.0, 1.0],  # Origin
        "right_elbow": [1.0, 0.0, 1.0],  # Point on x-axis
        "right_wrist": [1.0, 1.0, 1.0],  # Point creating 90° angle
    }

    angle = calculate_elbow_angle(pose_landmarks)

    if angle is not None:
        # Should be close to 90 degrees
        if 85 <= angle <= 95:
            print(f"✅ Angle calculation accurate: {angle:.1f}° (expected ~90°)")
            return True
        else:
            print(f"❌ Angle calculation inaccurate: {angle:.1f}° (expected ~90°)")
            return False
    else:
        print("❌ Failed to calculate angle")
        return False


def main() -> int:
    """Run all tests."""
    print("🚀 Starting Posture Analysis Tests\n")

    tests = [
        test_elbow_angle_calculation,
        test_elbow_angle_with_missing_data,
        test_elbow_angle_with_no_data,
        test_pose_lookup_with_synthetic_data,
        test_angle_calculation_accuracy,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except (ValueError, KeyError, AttributeError) as e:
            print(f"❌ Test failed with exception: {e}")

    print(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Posture analysis functions are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return 1


if __name__ == "__main__":
    exit(main())
