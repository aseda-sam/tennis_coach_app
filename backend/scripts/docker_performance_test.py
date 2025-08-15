#!/usr/bin/env python3
"""
Simplified performance testing script for Docker environments.
Uses smaller test videos to avoid memory issues.
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DockerPerformanceTester:
    """Test video processing performance in Docker environment."""

    def __init__(self) -> None:
        self.results = []

    def get_system_info(self) -> Dict[str, str]:
        """Get system hardware information."""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "platform": psutil.sys.platform,
            "architecture": (psutil.sys.maxsize > 2**32 and "64-bit") or "32-bit",
        }

    def create_test_video(
        self, resolution: Tuple[int, int], fps: int, duration: int, output_path: Path
    ) -> None:
        """Create a test video with specified parameters."""
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(output_path), fourcc, fps, resolution)

        # Create a simple moving pattern
        for frame_num in range(fps * duration):
            frame = np.zeros((resolution[1], resolution[0], 3), dtype=np.uint8)

            # Add moving circle
            x = int((frame_num / (fps * duration)) * resolution[0])
            y = resolution[1] // 2
            cv2.circle(frame, (x, y), 50, (0, 255, 0), -1)

            out.write(frame)

        out.release()
        logger.info(
            f"Created test video: {resolution[0]}x{resolution[1]} @ {fps}fps, {duration}s"
        )

    def test_frame_extraction(
        self, video_path: Path, max_frames: Optional[int] = None
    ) -> Dict[str, float]:
        """Test frame extraction performance."""
        start_time = time.time()
        start_memory = psutil.virtual_memory().used

        frames = []
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Calculate frame interval
        if max_frames is None:
            interval = 1
        else:
            interval = total_frames // max_frames if total_frames > max_frames else 1

        while frame_count < (max_frames or total_frames):
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % interval == 0:
                frames.append(frame)

            frame_count += 1

            if interval > 1:
                for _ in range(interval - 1):
                    cap.read()

        cap.release()

        end_time = time.time()
        end_memory = psutil.virtual_memory().used

        return {
            "frames_extracted": len(frames),
            "extraction_time": end_time - start_time,
            "memory_used_mb": (end_memory - start_memory) / (1024**2),
            "frames_per_second": len(frames) / (end_time - start_time),
        }

    def test_yolo_processing(self, frames: List[np.ndarray]) -> Dict[str, float]:
        """Test YOLO processing performance."""
        try:
            from ultralytics import YOLO

            model = YOLO("yolov8n.pt")
        except ImportError:
            logger.warning("YOLO not available, skipping YOLO test")
            return {"yolo_available": False}

        start_time = time.time()
        start_memory = psutil.virtual_memory().used

        detections = []
        # Only test first 10 frames to avoid memory issues
        test_frames = frames[:10]

        for _i, frame in enumerate(test_frames):
            results = model(frame, verbose=False)
            detections.append(
                len(results[0].boxes) if results[0].boxes is not None else 0
            )

        end_time = time.time()
        end_memory = psutil.virtual_memory().used

        return {
            "yolo_available": True,
            "frames_processed": len(test_frames),
            "processing_time": end_time - start_time,
            "memory_used_mb": (end_memory - start_memory) / (1024**2),
            "frames_per_second": len(test_frames) / (end_time - start_time),
            "total_detections": sum(detections),
        }

    def test_mediapipe_processing(self, frames: List[np.ndarray]) -> Dict[str, float]:
        """Test MediaPipe pose detection performance."""
        try:
            import mediapipe as mp

            pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=True,
                min_detection_confidence=0.3,
                min_tracking_confidence=0.3,
            )
        except ImportError:
            logger.warning("MediaPipe not available, skipping pose test")
            return {"mediapipe_available": False}

        start_time = time.time()
        start_memory = psutil.virtual_memory().used

        pose_detections = 0
        # Only test first 10 frames to avoid memory issues
        test_frames = frames[:10]

        for frame in test_frames:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb_frame)
            if results.pose_landmarks:
                pose_detections += 1

        end_time = time.time()
        end_memory = psutil.virtual_memory().used

        return {
            "mediapipe_available": True,
            "frames_processed": len(test_frames),
            "processing_time": end_time - start_time,
            "memory_used_mb": (end_memory - start_memory) / (1024**2),
            "frames_per_second": len(test_frames) / (end_time - start_time),
            "pose_detections": pose_detections,
        }

    def run_docker_test(self, test_dir: Path = Path("test_videos")) -> None:
        """Run performance tests optimized for Docker."""
        test_dir.mkdir(exist_ok=True)

        # System info
        system_info = self.get_system_info()
        logger.info(f"System Info: {system_info}")

        # Docker-optimized test configurations (shorter, smaller)
        test_configs = [
            # (resolution, fps, duration, description)
            ((1280, 720), 30, 5, "720p_30fps_5s"),
            ((1920, 1080), 30, 3, "1080p_30fps_3s"),
            ((1920, 1080), 60, 2, "1080p_60fps_2s"),
        ]

        for resolution, fps, duration, description in test_configs:
            logger.info(f"\n=== Testing {description} ===")

            # Create test video
            video_path = test_dir / f"test_{description}.mp4"
            self.create_test_video(resolution, fps, duration, video_path)

            # Test frame extraction
            extraction_result = self.test_frame_extraction(video_path)
            logger.info(
                f"Frame extraction: {extraction_result['frames_per_second']:.1f} fps"
            )

            # Extract frames for processing tests (limit to 30 frames max)
            frames = []
            cap = cv2.VideoCapture(str(video_path))
            frame_count = 0
            while frame_count < 30:  # Limit to 30 frames
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
                frame_count += 1
            cap.release()

            # Test YOLO processing
            yolo_result = self.test_yolo_processing(frames)
            if yolo_result.get("yolo_available"):
                logger.info(
                    f"YOLO processing: {yolo_result['frames_per_second']:.1f} fps"
                )

            # Test MediaPipe processing
            mediapipe_result = self.test_mediapipe_processing(frames)
            if mediapipe_result.get("mediapipe_available"):
                logger.info(
                    f"MediaPipe processing: {mediapipe_result['frames_per_second']:.1f} fps"
                )

            # Store results
            self.results.append(
                {
                    "config": description,
                    "resolution": resolution,
                    "fps": fps,
                    "duration": duration,
                    "extraction": extraction_result,
                    "yolo": yolo_result,
                    "mediapipe": mediapipe_result,
                }
            )

            # Clean up
            video_path.unlink()

    def generate_docker_recommendations(self) -> Dict[str, any]:
        """Generate recommendations for Docker environment."""
        if not self.results:
            return {"error": "No test results available"}

        recommendations = {
            "max_resolution": (1920, 1080),  # Default to 1080p
            "max_fps": 30,  # Default to 30fps
            "max_duration": 180,  # 3 minutes
            "frame_skip_ratio": 3,  # Process every 3rd frame
            "reasoning": [],
        }

        # Analyze 1080p performance
        hd_results = [r for r in self.results if r["resolution"] == (1920, 1080)]
        if hd_results:
            avg_yolo_fps = np.mean(
                [
                    r["yolo"]["frames_per_second"]
                    for r in hd_results
                    if r["yolo"].get("yolo_available")
                ]
            )
            if avg_yolo_fps < 5:  # If 1080p processing is slow
                recommendations["max_resolution"] = (1280, 720)
                recommendations["reasoning"].append(
                    "1080p processing too slow, limiting to 720p"
                )
            else:
                recommendations["reasoning"].append("1080p processing is viable")

        # Analyze high FPS performance
        high_fps_results = [r for r in self.results if r["fps"] == 60]
        if high_fps_results:
            avg_yolo_fps = np.mean(
                [
                    r["yolo"]["frames_per_second"]
                    for r in high_fps_results
                    if r["yolo"].get("yolo_available")
                ]
            )
            if avg_yolo_fps < 3:  # If 60fps processing is slow
                recommendations["reasoning"].append(
                    "60fps processing too slow, limiting to 30fps"
                )
            else:
                recommendations["max_fps"] = 60
                recommendations["reasoning"].append("60fps processing is viable")

        return recommendations

    def print_summary(self) -> None:
        """Print test summary and recommendations."""
        print("\n" + "=" * 60)
        print("DOCKER PERFORMANCE TEST SUMMARY")
        print("=" * 60)

        for result in self.results:
            print(f"\n{result['config']}:")
            print(
                f"  Frame extraction: {result['extraction']['frames_per_second']:.1f} fps"
            )

            if result["yolo"].get("yolo_available"):
                print(
                    f"  YOLO processing: {result['yolo']['frames_per_second']:.1f} fps"
                )

            if result["mediapipe"].get("mediapipe_available"):
                print(
                    f"  MediaPipe processing: {result['mediapipe']['frames_per_second']:.1f} fps"
                )

        recommendations = self.generate_docker_recommendations()
        print("\nDOCKER RECOMMENDED DEFAULTS:")
        print(f"  Max resolution: {recommendations['max_resolution']}")
        print(f"  Max FPS: {recommendations['max_fps']}")
        print(f"  Frame skip ratio: {recommendations['frame_skip_ratio']}")
        print(f"  Reasoning: {', '.join(recommendations['reasoning'])}")


def main() -> None:
    """Run Docker performance tests."""
    tester = DockerPerformanceTester()
    tester.run_docker_test()
    tester.print_summary()


if __name__ == "__main__":
    main()
