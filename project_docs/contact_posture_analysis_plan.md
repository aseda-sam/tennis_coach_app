# Contact Posture Analysis Implementation Plan

## Overview

This document outlines the implementation plan for analyzing player posture at ball contact moments, starting with a minimal viable implementation and building toward a comprehensive posture analysis system.

## Phase 1: Minimal Implementation (MVP)

### Goal

Start with the simplest possible implementation: calculate elbow angle from pose data at ball contact frames.

### Core Components

#### 1. Posture Analysis Service

```python
# app/services/posture_analysis/analysis_service.py
class ContactPostureAnalysisService:
    def calculate_elbow_angle(self, pose_landmarks: Dict) -> Optional[float]:
        """
        Calculate elbow angle from pose landmarks.

        Args:
            pose_landmarks: Dictionary with keypoint coordinates (x, y, confidence)

        Returns:
            Elbow angle in degrees, or None if keypoints missing
        """
        # Extract shoulder, elbow, wrist coordinates
        # Calculate angle using numpy
        # Return angle in degrees

    def get_pose_at_contact(self, ball_contact: BallContact, pose_detection: PoseDetection) -> Optional[Dict]:
        """
        Get pose data for the frame closest to ball contact timestamp.

        Args:
            ball_contact: BallContact object with video_timestamp
            pose_detection: PoseDetection object with pose_data

        Returns:
            Pose landmarks for contact frame, or None if not found
        """
        # Convert timestamp to frame index
        # Find nearest pose frame
        # Return pose landmarks

    def analyze_contact_posture(self, ball_contact_id: int) -> Optional[float]:
        """
        Analyze posture for a specific ball contact.

        Returns:
            Calculated elbow angle, or None if analysis failed
        """
        # Fetch contact and pose data
        # Calculate and store elbow angle
        # Return result
```

#### 2. Simple Testing

- Create standalone test script
- Use existing video and ball contact data
- Print results to console
- No database changes needed for MVP

### Implementation Steps

1. **Create simple posture analysis service**

   - `app/services/posture_analysis.py` - Single file with basic functions
   - `calculate_elbow_angle()` function
   - `get_pose_at_contact()` function
   - Use numpy for angle calculations

2. **Simple test script**

   - `test_posture_analysis.py` - Standalone test script
   - Use existing test video and ball contact
   - Print elbow angle result to console
   - No database changes needed for MVP

3. **Optional: Add to existing API**

   - Extend existing ball contact endpoint to include posture analysis
   - Only if the basic functions work correctly

### Success Criteria

- [ ] Can calculate elbow angle from pose landmarks
- [ ] Can find pose data at ball contact timestamp
- [ ] Test script runs and prints elbow angle
- [ ] No errors with real video data

## Phase 2: Enhanced Analysis (Future)

### Additional Metrics

- Shoulder alignment
- Hip rotation
- Wrist angle
- Stance width

### Advanced Features

- Background task processing
- Multiple posture metrics
- Posture scoring system
- Frontend visualization
- Batch analysis for all contacts

## Technical Details

### Dependencies

- Existing pose detection system
- Existing ball contact system
- NumPy for angle calculations

### Data Flow

1. User creates/identifies ball contact
2. System finds corresponding pose frame
3. Extract keypoint coordinates
4. Calculate posture metrics
5. Store results

### Key Design Decisions

- Start with single metric (elbow angle)
- Extend existing models rather than create new tables
- Use simple functions rather than complex services
- Focus on core functionality before optimization

## Files to Create/Modify

### New Files

- `backend/app/services/posture_analysis.py` - Core analysis functions
- `backend/test_posture_analysis.py` - Standalone test script

### Modified Files

- None for MVP (keep it simple!)

## Testing Strategy

### Unit Tests

- Test elbow angle calculation with known coordinates
- Test frame lookup with various timestamps
- Test edge cases (missing keypoints, invalid data)

### Integration Tests

- End-to-end test with real video and contact data
- Verify database storage and retrieval
- Test API endpoint functionality

## Future Considerations

### Performance

- Batch processing for multiple contacts
- Caching of pose data lookups
- Background task processing

### Accuracy

- Camera angle normalization
- Multi-player support
- Racket detection integration

### User Experience

- Real-time analysis feedback
- Visual posture overlays
- Coaching recommendations

---

_This plan prioritizes simplicity and rapid iteration, allowing us to validate the core concept before building more complex features._
