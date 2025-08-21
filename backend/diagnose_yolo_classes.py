#!/usr/bin/env python3
"""
Diagnostic script to check YOLO model classes and detections.
"""

import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import numpy as np

from app.core.database import get_db
from app.services.cv_service import cv_service
from app.services.video_service import get_video_by_id


def diagnose_yolo_classes():
    """Diagnose what classes are available in our YOLO model."""

    print("🔍 YOLO Model Class Diagnosis")
    print("=" * 50)

    # Check what YOLO models are available
    print(f"Available YOLO models: {list(cv_service.yolo_models.keys())}")
    print(f"Current ball detector: {cv_service.ball_detector}")

    if not cv_service.ball_detector:
        print("❌ No YOLO model available")
        return

    # Get a sample frame to test detection
    db = next(get_db())
    video = get_video_by_id(db, 9)

    if not video:
        print("❌ No video found")
        return

    video_path = Path(video.file_path)
    frames = cv_service.extract_frames(video_path, max_frames=5)

    if not frames:
        print("❌ No frames extracted")
        return

    print(f"\n📹 Testing on {len(frames)} frames from: {video.filename}")

    # Test detection on first frame
    frame = frames[0]
    print(f"Frame shape: {frame.shape}")

    # Run YOLO detection
    results = cv_service.ball_detector(frame, verbose=False)

    # Analyze all detections
    all_classes = set()
    class_counts = {}

    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes:
                class_id = int(box.cls[0].cpu().numpy())
                confidence = float(box.conf[0].cpu().numpy())

                all_classes.add(class_id)
                if class_id not in class_counts:
                    class_counts[class_id] = []
                class_counts[class_id].append(confidence)

    print(f"\n🎯 Detected Classes: {sorted(all_classes)}")
    print(f"Total unique classes: {len(all_classes)}")

    # Show class details
    print("\n📊 Class Details:")
    for class_id in sorted(all_classes):
        confidences = class_counts[class_id]
        avg_conf = np.mean(confidences)
        max_conf = np.max(confidences)
        count = len(confidences)

        print(
            f"  Class {class_id}: {count} detections, avg_conf={avg_conf:.3f}, max_conf={max_conf:.3f}"
        )

    # Test with different confidence thresholds
    print("\n🔍 Testing different confidence thresholds:")
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]

    for threshold in thresholds:
        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())

                    if confidence > threshold:
                        detections.append(
                            {"class_id": class_id, "confidence": confidence}
                        )

        print(f"  Threshold {threshold}: {len(detections)} detections")
        if detections:
            classes_found = set(d["class_id"] for d in detections)
            print(f"    Classes: {sorted(classes_found)}")

    # Test our racket classes specifically
    print("\n🎾 Testing racket-specific classes:")
    racket_classes = [43, 44, 48]

    for class_id in racket_classes:
        if class_id in class_counts:
            confidences = class_counts[class_id]
            print(
                f"  Class {class_id} (potential racket): {len(confidences)} detections"
            )
            print(f"    Confidences: {[f'{c:.3f}' for c in confidences[:5]]}")
        else:
            print(f"  Class {class_id} (potential racket): NOT FOUND")

    # Test all frames for racket-like objects
    print("\n🎾 Testing all frames for racket detection:")
    for i, frame in enumerate(frames):
        results = cv_service.ball_detector(frame, verbose=False)

        frame_detections = []
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0].cpu().numpy())
                    confidence = float(box.conf[0].cpu().numpy())

                    if class_id in racket_classes and confidence > 0.1:
                        frame_detections.append(
                            {"class_id": class_id, "confidence": confidence}
                        )

        if frame_detections:
            print(f"  Frame {i}: {len(frame_detections)} potential rackets")
            for det in frame_detections:
                print(f"    Class {det['class_id']}: {det['confidence']:.3f}")
        else:
            print(f"  Frame {i}: No rackets detected")


if __name__ == "__main__":
    diagnose_yolo_classes()
