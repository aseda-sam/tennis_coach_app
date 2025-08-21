#!/usr/bin/env python3
"""
Test script to check all YOLO classes and find racket-like objects.
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

# COCO class names (first 80 classes)
COCO_CLASSES = [
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
]


def test_all_classes():
    """Test all YOLO classes to find racket-like objects."""

    print("🔍 Comprehensive YOLO Class Analysis")
    print("=" * 60)

    # Get a sample frame
    db = next(get_db())
    video = get_video_by_id(db, 9)

    if not video:
        print("❌ No video found")
        return

    video_path = Path(video.file_path)
    frames = cv_service.extract_frames(video_path, max_frames=10)

    if not frames:
        print("❌ No frames extracted")
        return

    print(f"📹 Testing on {len(frames)} frames from: {video.filename}")

    # Collect all detections across frames
    all_detections = []

    for frame_idx, frame in enumerate(frames):
        results = cv_service.ball_detector(frame, verbose=False)

        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    class_id = int(box.cls[0].cpu().numpy())
                    confidence = float(box.conf[0].cpu().numpy())
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                    # Calculate properties
                    bbox_width = x2 - x1
                    bbox_height = y2 - y1
                    aspect_ratio = bbox_width / bbox_height if bbox_height > 0 else 0
                    area = bbox_width * bbox_height

                    all_detections.append(
                        {
                            "frame": frame_idx,
                            "class_id": class_id,
                            "class_name": COCO_CLASSES[class_id]
                            if class_id < len(COCO_CLASSES)
                            else f"unknown_{class_id}",
                            "confidence": confidence,
                            "bbox": [x1, y1, x2, y2],
                            "aspect_ratio": aspect_ratio,
                            "area": area,
                        }
                    )

    print(f"\n🎯 Total detections: {len(all_detections)}")

    # Group by class
    class_groups = {}
    for det in all_detections:
        class_id = det["class_id"]
        if class_id not in class_groups:
            class_groups[class_id] = []
        class_groups[class_id].append(det)

    print("\n📊 Detected Classes:")
    for class_id in sorted(class_groups.keys()):
        detections = class_groups[class_id]
        class_name = detections[0]["class_name"]
        avg_conf = np.mean([d["confidence"] for d in detections])
        max_conf = np.max([d["confidence"] for d in detections])

        print(f"  Class {class_id} ({class_name}): {len(detections)} detections")
        print(f"    Avg confidence: {avg_conf:.3f}, Max confidence: {max_conf:.3f}")

        # Show aspect ratios for potential racket-like objects
        aspect_ratios = [d["aspect_ratio"] for d in detections]
        avg_aspect = np.mean(aspect_ratios)
        print(f"    Avg aspect ratio: {avg_aspect:.2f}")

        # Show some sample detections
        for i, det in enumerate(detections[:3]):  # Show first 3
            print(
                f"      Sample {i + 1}: conf={det['confidence']:.3f}, aspect={det['aspect_ratio']:.2f}, area={det['area']:.0f}"
            )

    # Look for racket-like objects based on shape
    print("\n🎾 Racket-like Object Analysis:")
    print(
        "Looking for objects with aspect ratios between 0.3 and 3.0 (typical racket shapes)"
    )

    racket_candidates = []
    for det in all_detections:
        aspect_ratio = det["aspect_ratio"]
        if 0.3 <= aspect_ratio <= 3.0 and det["confidence"] > 0.3:
            racket_candidates.append(det)

    print(f"Found {len(racket_candidates)} potential racket-like objects:")

    for det in racket_candidates:
        print(
            f"  {det['class_name']} (class {det['class_id']}): conf={det['confidence']:.3f}, aspect={det['aspect_ratio']:.2f}"
        )

    # Test with very low confidence threshold to see everything
    print("\n🔍 Low Confidence Analysis (threshold 0.1):")
    low_conf_detections = [d for d in all_detections if d["confidence"] > 0.1]

    print(f"Total detections with confidence > 0.1: {len(low_conf_detections)}")

    # Group by class for low confidence
    low_conf_classes = {}
    for det in low_conf_detections:
        class_id = det["class_id"]
        if class_id not in low_conf_classes:
            low_conf_classes[class_id] = []
        low_conf_classes[class_id].append(det)

    for class_id in sorted(low_conf_classes.keys()):
        detections = low_conf_classes[class_id]
        class_name = detections[0]["class_name"]
        print(f"  Class {class_id} ({class_name}): {len(detections)} detections")

    # Check if we're missing any classes by testing with very low threshold
    print("\n🔍 Testing with very low threshold (0.05):")
    frame = frames[0]
    results = cv_service.ball_detector(frame, verbose=False)

    very_low_detections = []
    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes:
                confidence = float(box.conf[0].cpu().numpy())
                class_id = int(box.cls[0].cpu().numpy())

                if confidence > 0.05:
                    very_low_detections.append(
                        {
                            "class_id": class_id,
                            "class_name": COCO_CLASSES[class_id]
                            if class_id < len(COCO_CLASSES)
                            else f"unknown_{class_id}",
                            "confidence": confidence,
                        }
                    )

    print(f"Detections with confidence > 0.05: {len(very_low_detections)}")
    classes_found = set(d["class_id"] for d in very_low_detections)
    print(f"Classes found: {sorted(classes_found)}")

    for class_id in sorted(classes_found):
        class_detections = [d for d in very_low_detections if d["class_id"] == class_id]
        class_name = class_detections[0]["class_name"]
        confidences = [d["confidence"] for d in class_detections]
        print(
            f"  Class {class_id} ({class_name}): {len(class_detections)} detections, confidences: {[f'{c:.3f}' for c in confidences]}"
        )


if __name__ == "__main__":
    test_all_classes()
