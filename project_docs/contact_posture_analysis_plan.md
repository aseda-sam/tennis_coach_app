# Contact Posture Analysis Implementation Plan

## Overview

This document outlines the implementation plan for analyzing player posture at ball contact moments, starting with a minimal viable implementation and building toward a comprehensive posture analysis system.

## Phase 1: Minimal Implementation (MVP)

### Goal

Start with the simplest possible implementation: calculate elbow angle from pose data at ball contact frames.

### Core Components

#### 1. Posture Analysis Service

```python
# app/services/posture_analysis.py (IMPLEMENTED)
def calculate_elbow_angle(
    pose_landmarks: Dict, 
    contact_hand: str, 
    stroke_type: Optional[str] = None
) -> Optional[float]:
    """
    Calculate elbow angle from pose landmarks for the contact hand.
    
    Features:
    - Uses actual contact hand (left/right) from ball contact data
    - Focuses on forehands only (single-handed strokes)
    - Validates input parameters
    - Returns angle in degrees
    """

def get_pose_at_contact(
    ball_contact: BallContact, 
    pose_detection: PoseDetection, 
    video: Video
) -> Optional[Dict]:
    """
    Get pose data for the frame closest to ball contact timestamp.
    
    Features:
    - Uses actual video FPS for accurate frame calculation
    - Searches for nearest frame with pose data
    - Handles missing pose data gracefully
    """

def analyze_contact_posture(db: Session, ball_contact_id: int) -> Optional[float]:
    """
    Analyze posture for a specific ball contact.
    
    Features:
    - Fetches ball contact, video, and pose detection data
    - Uses contact hand and stroke type for analysis
    - Provides detailed logging
    - Returns calculated elbow angle
    """
```

#### 2. Testing (IMPLEMENTED)

- ✅ `test_real_posture_analysis.py` - Real data testing script
- ✅ Uses existing video and ball contact data from database
- ✅ Tests both left and right-handed players
- ✅ Validates forehand constraint functionality
- ✅ Tests actual video FPS usage
- ✅ Provides detailed analysis output

### Implementation Steps (COMPLETED)

1. **✅ Create posture analysis service**

   - ✅ `app/services/posture_analysis.py` - Core analysis functions
   - ✅ `calculate_elbow_angle()` with contact hand and stroke type support
   - ✅ `get_pose_at_contact()` with actual video FPS usage
   - ✅ `analyze_contact_posture()` for full database integration
   - ✅ Uses numpy for accurate angle calculations

2. **✅ Real data testing**

   - ✅ `test_real_posture_analysis.py` - Real database testing
   - ✅ Tests with actual video and ball contact data
   - ✅ Validates contact hand detection and forehand constraint
   - ✅ Confirms accurate frame calculation with video FPS

3. **✅ Enhanced functionality**

   - ✅ Contact hand detection (left/right from ball contact data)
   - ✅ Forehand-only constraint for single-handed strokes
   - ✅ Actual video FPS usage for accurate frame calculation
   - ✅ Comprehensive error handling and logging

### Success Criteria

- [x] Can calculate elbow angle from pose landmarks
- [x] Can find pose data at ball contact timestamp
- [x] Test script runs and prints elbow angle
- [x] No errors with real video data
- [x] Uses actual video FPS for accurate frame calculation
- [x] Supports both left and right-handed players
- [x] Focuses on forehands only (single-handed strokes)

## Current Implementation Status

### ✅ Phase 1 Complete - MVP Implementation

The minimal viable implementation has been successfully completed with the following features:

#### Core Functionality
- **Elbow Angle Calculation**: Accurate calculation using numpy vector math
- **Contact Hand Detection**: Uses actual contact hand from ball contact data (left/right)
- **Forehand Focus**: Constrains analysis to single-handed strokes only
- **Real Video FPS**: Uses actual video frame rate for accurate frame calculation
- **Robust Error Handling**: Comprehensive validation and logging

#### Key Improvements Made
1. **Enhanced Accuracy**: Uses actual video FPS instead of hardcoded 30fps assumption
2. **Player Agnostic**: Works for both left and right-handed players
3. **Stroke Specific**: Focuses on forehands, ready for future backhand support
4. **Real Data Testing**: Comprehensive testing with actual tennis video data

#### Test Results
- ✅ All tests passing with real video data
- ✅ Accurate frame-to-timestamp conversion
- ✅ Proper contact hand detection
- ✅ Forehand constraint working correctly
- ✅ Error handling for edge cases

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

### New Files (CREATED)

- ✅ `backend/app/services/posture_analysis.py` - Core analysis functions
- ✅ `backend/test_real_posture_analysis.py` - Real data testing script

### Modified Files

- ✅ None for MVP (kept it simple as planned!)

## Testing Strategy

### Unit Tests (IMPLEMENTED)

- ✅ Test elbow angle calculation with known coordinates
- ✅ Test frame lookup with various timestamps
- ✅ Test edge cases (missing keypoints, invalid data)
- ✅ Test contact hand validation (left/right)
- ✅ Test forehand constraint functionality

### Integration Tests (IMPLEMENTED)

- ✅ End-to-end test with real video and contact data
- ✅ Verify database storage and retrieval
- ✅ Test actual video FPS usage
- ✅ Test both left and right-handed players
- ⏳ Test API endpoint functionality (future enhancement)

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
