# Removed Algorithms Documentation

**Date**: January 2025  
**Status**: 📚 **ARCHIVED** - Algorithms removed for MVP simplification  
**Purpose**: Reference documentation for future recreation if needed

## Overview

This document captures the high-level thinking and algorithmic approaches that were implemented but are now being removed as part of the MVP simplification. The goal is to preserve the intellectual work and design decisions for potential future recreation.

## 🎾 Ball Contact Detection Algorithms

### 1. Basic Ball-Player Proximity Detection

**Algorithm**: `detect_ball_contact()`

**Core Concept**: Detect ball contact by measuring proximity between detected tennis balls and player wrist positions.

**Key Approach**:

- Use YOLO ball detection to find tennis balls in each frame
- Use MediaPipe pose detection to get player wrist positions (left/right)
- Calculate Euclidean distance between ball center and closest wrist
- Mark contact when distance falls below threshold (default: 50 pixels)

**Technical Details**:

```python
# Distance calculation
distance = sqrt((ball_center_x - wrist_x)² + (ball_center_y - wrist_y)²)

# Contact detection
if distance <= contact_threshold:
    # Record contact with timestamp, hand, confidence
```

**Strengths**:

- Simple and computationally efficient
- Works well for clear, close-up shots
- Good baseline approach

**Limitations**:

- High false positive rate due to camera perspective
- Timing issues (2+ second delays from actual contact)
- No consideration of ball trajectory or swing dynamics
- Sensitive to pose detection accuracy

### 2. Advanced Multi-Criteria Contact Detection

**Algorithm**: `detect_ball_contact_with_rackets()`

**Core Concept**: Sophisticated contact detection using multiple signals and smart filtering to reduce false positives.

**Multi-Criteria Approach**:

#### A. Racket Head Position Calculation

- **Problem**: Using racket center gives inaccurate contact points
- **Solution**: Calculate actual racket head position extending from center
- **Method**: Use wrist-to-racket vector to determine racket orientation
- **Benefit**: Contact detection at actual hitting surface, not racket center

#### B. Ball Size & Depth Perception

- **Insight**: Ball size indicates distance from camera (depth)
- **Implementation**:
  ```python
  ball_area = ball_width * ball_height
  ball_size_factor = min(ball_area / 400.0, 2.0)  # Normalize by typical ball size
  ```
- **Application**: Closer balls (larger) get stricter thresholds, distant balls get looser thresholds
- **Benefit**: Reduces false positives from distant ball detections

#### C. Smart False Positive Filtering

- **Early Video Skip**: Skip first 2 seconds (eliminates player positioning false positives)
- **Confidence Threshold**: Only use high-confidence ball detections (≥0.6)
- **Temporal Clustering**: Minimum 300ms between contacts (realistic tennis timing)
- **Quality Prioritization**: Prefer racket contacts over wrist contacts

#### D. Dynamic Threshold Adjustment

```python
# Depth-based threshold adjustment
adjusted_racket_threshold = racket_contact_threshold * (2.0 - ball_size_factor)
# Closer balls (larger) get stricter thresholds
```

**Key Parameters**:

- `min_ball_confidence: 0.6` - High-quality ball detections only
- `early_video_skip_seconds: 2.0` - Skip player positioning phase
- `racket_contact_threshold: 15.0` - Tight racket distance threshold
- `contact_threshold: 50.0` - Wrist fallback threshold

**Results**:

- ✅ Accurate timing alignment (vs 2+ second errors)
- ✅ Reduced false positives significantly
- ✅ Better contact quality scoring

### 3. Ball Trajectory Analysis

**Algorithm**: `_calculate_ball_trajectory_change()`

**Core Concept**: Detect sudden changes in ball velocity/direction that indicate contact events.

**Method**:

- Track ball positions across multiple frames
- Calculate velocity vectors between consecutive frames
- Detect sudden velocity changes (direction/speed)
- Use velocity change magnitude as contact signal

**Technical Implementation**:

```python
# Calculate velocity change
vel_change_x = abs(velocity_x[frame] - velocity_x[frame-1])
vel_change_y = abs(velocity_y[frame] - velocity_y[frame-1])
trajectory_change = sqrt(vel_change_x² + vel_change_y²)
```

**Use Case**: Secondary signal to validate proximity-based contact detection

## 🏓 Racket Detection (Planned but Not Implemented)

### Conceptual Approach

**Goal**: Detect tennis rackets using YOLO sports equipment classes for more accurate contact detection.

**Planned Implementation**:

1. **YOLO Sports Equipment Classes**: Use pre-trained YOLO models with sports equipment detection
2. **Racket Template Matching**: Add template matching for improved accuracy
3. **Position Tracking**: Track racket position across frames
4. **Head Position Estimation**: Estimate racket head position relative to player wrists

**Expected Benefits**:

- More accurate contact point detection
- Better understanding of swing dynamics
- Reduced false positives from wrist-based detection

**Status**: ❌ **Never Implemented** - Only exists in project plan and mock test data

## 🧠 Key Insights Discovered

### 1. Tennis Contact Detection Requires Loose Thresholds

- Real ball-racket distances can be 100+ pixels due to camera perspective
- Motion blur and detection accuracy affect proximity calculations
- 2D video perspective creates optical illusions

### 2. Early Video Frames Are Problematic

- First 2 seconds typically show player positioning, not actual hits
- Pre-swing racket movements create false contact signals
- Player setup phase should be filtered out

### 3. Ball Size Indicates Contact Likelihood

- Closer balls (larger bounding boxes) = more likely real contact
- Distant balls (smaller boxes) = likely visual parallax effects
- Depth perception is crucial for accurate detection

### 4. Contact Timing Patterns

- Real tennis hits are spaced 300ms+ apart
- Clustered detections usually indicate false positives
- Temporal analysis helps filter noise

### 5. Multi-Signal Approach Works Best

- Single proximity threshold is insufficient
- Combining ball size, confidence, timing, and trajectory improves accuracy
- Fallback mechanisms (racket → wrist) provide robustness

## 🔧 Technical Architecture

### Data Flow

```
Video Frames → YOLO Ball Detection → Ball Positions
     ↓
Pose Detection → Wrist Positions → Distance Calculation
     ↓
Contact Detection → Filtering → Contact Events
```

### Key Data Structures

```python
# Ball Detection
{
    "bbox": [x1, y1, x2, y2],
    "confidence": 0.85,
    "center": [x, y]
}

# Contact Detection
{
    "frame_index": 1234,
    "timestamp": 45.2,
    "ball_position": {"x": 320, "y": 240},
    "contact_hand": "right",
    "distance": 25.5,
    "confidence": 0.85,
    "contact_type": "racket"  # or "wrist"
}
```

## 🎯 Why These Were Removed

### MVP Simplification Decision

- **Goal**: Focus on posture analysis, not contact detection accuracy
- **Manual Alternative**: Manual ball contact marking works perfectly for MVP
- **Complexity vs Value**: Sophisticated detection adds complexity without MVP value
- **User Experience**: Manual marking is more reliable than automated detection

### Future Recreation Considerations

If recreating these algorithms in the future:

1. **Start Simple**: Begin with basic proximity detection
2. **Add Filtering**: Implement smart false positive filtering early
3. **Multi-Signal**: Combine multiple detection signals for robustness
4. **User Feedback**: Use manual annotations to validate and improve algorithms
5. **Incremental**: Build complexity gradually, validate each step

## 📚 References

- **Contact Detection Improvements**: `project_docs/archive/contact_detection_improvements.md`
- **Project Plan**: `project_docs/project_plan.md` (Phase 9C)
- **Test Files**: `backend/tests/test_contact_detection.py`, `backend/tests/test_improved_contact_detection.py`
- **Implementation**: `backend/app/services/ball_contact_service.py`

## 🔮 Future Possibilities

If automated contact detection is needed in the future:

1. **Machine Learning Approach**: Train classifier on confirmed contact vs non-contact examples
2. **Trajectory Analysis**: More sophisticated ball trajectory change detection
3. **Swing Phase Detection**: Identify backswing vs forward swing vs follow-through
4. **Multi-Ball Handling**: Better logic for videos with multiple balls
5. **Court Position Context**: Use court detection to validate contact locations
6. **Real-time Processing**: Optimize for live video analysis

---

**Note**: This documentation preserves the algorithmic thinking and design decisions. The actual implementation code has been removed as part of the MVP simplification, but the concepts and approaches can be recreated if needed in the future.
