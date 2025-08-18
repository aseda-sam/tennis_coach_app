#!/usr/bin/env python3
"""
Test script for timing functionality.
This script demonstrates how to test the new timing logging features.
"""

import time

import requests

# Configuration
API_BASE = "http://localhost:8000"
TEST_VIDEO = "test_tennis_video.mp4"  # Use dedicated test video


def test_timing_functionality() -> None:
    """Test the timing functionality by analyzing an existing video."""

    print("🎾 Testing Timing Functionality")
    print("=" * 50)

    # Step 1: Check if video exists in database
    print(f"1. Checking if video '{TEST_VIDEO}' exists...")
    try:
        response = requests.get(f"{API_BASE}/v0/videos/", timeout=10)
        if response.status_code == 200:
            videos = response.json()
            video_id = None
            for video in videos:
                if video.get("filename") == TEST_VIDEO:
                    video_id = video.get("id")
                    break

            if video_id:
                print(f"   ✅ Video found with ID: {video_id}")
            else:
                print(f"   ❌ Video '{TEST_VIDEO}' not found in database")
                print("   💡 You can upload it via the frontend first")
                return
        else:
            print(f"   ❌ Failed to get videos: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to API. Make sure the server is running:")
        print("      python -m uvicorn app.main:app --reload --port 8000")
        return

    # Step 2: Start analysis
    print(f"\n2. Starting analysis for video ID {video_id}...")
    try:
        response = requests.post(
            f"{API_BASE}/v0/videos/{video_id}/analyze",
            json={"analysis_type": "comprehensive", "include_pose_detection": True},
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            task_id = result.get("task_id")
            print(f"   ✅ Analysis started! Task ID: {task_id}")
            print(f"   📊 Initial result: {result.get('message', 'N/A')}")
        else:
            print(f"   ❌ Failed to start analysis: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except (requests.RequestException, ValueError) as e:
        print(f"   ❌ Error starting analysis: {e}")
        return

    # Step 3: Monitor progress
    print("\n3. Monitoring analysis progress...")
    print("   📝 Watch the backend logs for timing information!")
    print("   🔍 Look for messages like:")
    print("      - ⏱️ Frame Extraction completed in X.XXXs")
    print("      - ⏱️ Ball Detection completed in X.XXXs")
    print("      - ⏱️ Pose Detection completed in X.XXXs")
    print("      - 📊 Analysis Timing Breakdown:")

    # Poll for status
    max_attempts = 30  # 30 seconds
    for _attempt in range(max_attempts):
        try:
            response = requests.get(f"{API_BASE}/v0/analysis/task/{task_id}", timeout=5)
            if response.status_code == 200:
                status = response.json()
                progress = status.get("progress", 0)
                current_stage = status.get("current_stage", "unknown")
                stage_message = status.get("stage_message", "")

                print(
                    f"   📈 Progress: {progress}% | Stage: {current_stage} | {stage_message}"
                )

                if status.get("status") == "completed":
                    print("   ✅ Analysis completed!")
                    break
                elif status.get("status") == "failed":
                    print(
                        f"   ❌ Analysis failed: {status.get('error', 'Unknown error')}"
                    )
                    break
            else:
                print(f"   ⚠️  Failed to get status: {response.status_code}")
        except (requests.RequestException, ValueError) as e:
            print(f"   ⚠️  Error checking status: {e}")

        time.sleep(1)

    print("\n4. Analysis complete!")
    print("   📊 Check the backend logs for detailed timing breakdown")
    print("   🎯 You should see messages like:")
    print("      - frame_extraction: X.XXXs (XX.X%)")
    print("      - ball_detection: X.XXXs (XX.X%)")
    print("      - pose_detection: X.XXXs (XX.X%)")
    print("      - frame_annotation: X.XXXs (XX.X%)")
    print("      - video_creation: X.XXXs (XX.X%)")


if __name__ == "__main__":
    test_timing_functionality()
