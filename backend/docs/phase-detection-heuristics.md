# Serve Phase Detection Heuristics

## Overview

The app segments serves into 8 phases based on the **Kovacs & Ellenbecker (2011) biomechanical model** of the tennis serve. Phase detection uses **pose keypoint heuristics** — analyzing body positions, velocities, and relationships across the serve window to identify phase boundaries.

**Key insight:** We don't use ML models for phase detection. Instead, we use deterministic heuristics based on observable biomechanical features from MediaPipe pose keypoints.

## The 8 Kovacs Phases

| # | Phase | Biomechanical Definition (Kovacs) | Our Detection Method |
|---|-------|----------------------------------|---------------------|
| 1 | **Start** | Initial stance before motion begins | First frame of serve window (trivial) |
| 2 | **Release** | Ball leaves toss hand | Toss arm wrist rises above shoulder |
| 3 | **Loading** | Deepest knee bend + weight shift | Maximum knee-hip ratio (knees furthest below hips) |
| 4 | **Cocking** | Racket behind back, shoulder external rotation | Both arms raised + peak wrist height (trophy pose) |
| 5 | **Acceleration** | Racket accelerates toward ball | Dominant wrist velocity spike (2x mean) |
| 6 | **Contact** | Racket strikes ball | User-tagged timestamp (ground truth) |
| 7 | **Deceleration** | Wrist slows after contact | Velocity drops below 50% of peak |
| 8 | **Finish** | Follow-through complete | Dominant wrist drops below shoulder |

---

## Feature Extraction (Per Frame)

Before phase detection runs, we extract **per-frame features** from pose keypoints using `extract_frame_features()`:

### Normalized Coordinates
- **Hip center** is the origin `[0, 0]`
- **Torso length** (hip-to-shoulder distance) is the scale factor
- All keypoints are normalized: `(x - hip_center_x) / torso_length`, `(y - hip_center_y) / torso_length`
- **Height convention:** Negative Y = above hips (screen coords inverted)

### Extracted Features

1. **`max_wrist_height`** (float)
   - Normalized height of highest wrist above hip center
   - Used for: Cocking detection (peak trophy position)

2. **`any_wrist_above_shoulder`** (bool)
   - True if at least one wrist is higher than its shoulder
   - Used for: General serve motion detection

3. **`both_arms_raised`** (bool)
   - True if both wrists are above their respective shoulders
   - Used for: Cocking detection (trophy pose indicator)

4. **`max_wrist_velocity`** (float, px/sec)
   - Maximum velocity of left or right wrist since previous frame
   - Calculated: `distance(curr_wrist, prev_wrist) / (1/fps)`
   - Used for: Acceleration, Deceleration

5. **`knee_hip_ratio`** (float)
   - `(avg_knee_y - avg_hip_y) / torso_length`
   - Positive = knees below hips; larger = deeper bend
   - Used for: Loading detection

6. **`has_pose`** (bool)
   - True if MediaPipe detected a pose in this frame
   - Frames with `has_pose=False` are skipped in calculations

---

## Phase Detection Algorithms

### 1. Start
```python
detections[ServePhase.START] = (0, 1.0)  # First frame, 100% confidence
```
**Trivial:** First frame of the serve window.

---

### 2. Release (Toss Arm Wrist Rises Above Shoulder)

**Physical meaning:** Ball leaves the toss hand as arm extends upward.

**Heuristic:**
```python
def _detect_release(pose_frames, toss_side):
    for i, frame in enumerate(pose_frames):
        wrist = frame[f"{toss_side}_wrist"]
        shoulder = frame[f"{toss_side}_shoulder"]
        # Screen coords: smaller Y = higher
        if wrist[1] < shoulder[1]:
            return i  # First frame where toss wrist is above shoulder
```

**Why it works:**
- Toss arm is opposite dominant hand (right-handed player → left arm tosses)
- Wrist rising above shoulder is a clear, early landmark in the serve motion
- Returns the **first** frame meeting this condition

**Confidence:** 0.8

---

### 3. Loading (Deepest Knee Bend)

**Physical meaning:** Legs compress to store elastic energy before upward drive.

**Heuristic:**
```python
def _detect_loading(features):
    ratios = []
    for i, feat in enumerate(features):
        khr = feat["knee_hip_ratio"]  # (avg_knee_y - avg_hip_y) / torso_length
        if feat["has_pose"] and khr > 0:
            ratios.append((i, khr))

    best = max(ratios, key=lambda x: x[1])  # Largest ratio = deepest bend
    return best[0]
```

**Why it works:**
- `knee_hip_ratio` measures vertical distance between knees and hips, normalized by torso length
- In screen coords, larger Y = lower on screen → larger ratio = knees further below hips = deeper bend
- We find the **maximum** `knee_hip_ratio` across all frames

**Confidence:** 0.7

**Known limitation:** Loading can sometimes occur before or after Cocking in real serves, causing monotonic enforcement to drop it (see "Monotonic Enforcement" section).

---

### 4. Cocking (Trophy Pose — Both Arms Raised + Peak Wrist Height)

**Physical meaning:** Both arms up, racket behind back, shoulder at maximum external rotation. Visually looks like a trophy pose.

**Heuristic:**
```python
def _detect_cocking(pose_frames, features):
    candidates = []
    for i, feat in enumerate(features):
        if feat["both_arms_raised"]:
            candidates.append((i, feat["max_wrist_height"]))

    if not candidates:
        return None

    # Pick frame with highest wrist height among "both arms raised" frames
    best = max(candidates, key=lambda x: x[1])
    return best[0]
```

**Why it works:**
- Filters to frames where **both wrists are above shoulders** (`both_arms_raised=True`)
- Among those, picks the frame with **highest wrist** (peak of trophy position)
- This captures the iconic "arms up" moment before the racket drops and accelerates

**Confidence:** 0.7

**Note on naming:** "Trophy" was the original phase name, but Kovacs calls this stage **Cocking**. Trophy position is the visual pose, not the temporal phase. The trophy pose marks the **start** of the Cocking phase.

---

### 5. Acceleration (Dominant Wrist Velocity Spike)

**Physical meaning:** Racket accelerates rapidly toward the ball after the drop.

**Heuristic:**
```python
ACCELERATION_VELOCITY_MULTIPLIER = 2.0

def _detect_acceleration(features):
    velocities = [(i, feat["max_wrist_velocity"]) for i, feat in enumerate(features)]

    mean_vel = np.mean([v for _, v in velocities])
    threshold = mean_vel * 2.0  # 2x mean velocity

    # Find FIRST frame exceeding threshold
    for i, vel in velocities:
        if vel > threshold:
            return i
```

**Why it works:**
- During acceleration, wrist velocity spikes dramatically (racket head speed increases exponentially)
- Using **2x mean velocity** as threshold filters out slow movements
- Returns the **first** frame where velocity crosses this threshold

**Confidence:** 0.6

**Why confidence is lower:** Velocity can be noisy due to pose jitter. A 2x multiplier is conservative but not perfect.

---

### 6. Contact (User-Tagged Timestamp)

**Physical meaning:** Racket strikes the ball.

**Heuristic:**
```python
if contact_timestamp is not None:
    contact_frame = int((contact_timestamp - serve_start) * fps)
    detections[ServePhase.CONTACT] = (contact_frame, 1.0)
```

**Why it's different:**
- Contact is **not detected heuristically** — it's provided by the user (or auto-detected by ball tracking, if implemented)
- This is **ground truth** with 100% confidence
- All phases that depend on contact (Deceleration, Finish) require this to be set

**Confidence:** 1.0 (ground truth)

**Dependency:** Deceleration and Finish phases **require** contact to be detected. If `contact_timestamp` is `None`, those phases will not be detected.

---

### 7. Deceleration (Velocity Drops After Contact)

**Physical meaning:** Wrist slows down after contact as the arm begins follow-through.

**Heuristic:**
```python
DECELERATION_VELOCITY_FRACTION = 0.5

def _detect_deceleration(features, contact_frame):
    # Get peak velocity in 5-frame window around contact
    pre_contact = [
        feat["max_wrist_velocity"]
        for feat in features[contact_frame - 5 : contact_frame + 1]
    ]
    peak_vel = max(pre_contact)
    threshold = peak_vel * 0.5  # 50% of peak

    # Search AFTER contact for velocity drop
    for i in range(contact_frame + 1, len(features)):
        if features[i]["max_wrist_velocity"] < threshold:
            return i
```

**Why it works:**
- Contact is the moment of peak wrist velocity
- After contact, racket/wrist decelerates rapidly
- We define deceleration onset as when velocity drops below **50% of peak**

**Confidence:** 0.6

**Dependency:** Requires `contact_frame` to be detected. If contact is missing, deceleration is not detected.

---

### 8. Finish (Dominant Wrist Drops Below Shoulder)

**Physical meaning:** Follow-through complete, arm has crossed body and wrist descends.

**Heuristic:**
```python
def _detect_finish(pose_frames, dom_side, contact_frame):
    for i in range(contact_frame + 1, len(pose_frames)):
        wrist = frame[f"{dom_side}_wrist"]
        shoulder = frame[f"{dom_side}_shoulder"]
        # Screen coords: larger Y = lower
        if wrist[1] > shoulder[1]:
            return i  # First frame after contact where wrist is below shoulder
```

**Why it works:**
- After contact, the dominant arm wraps across the body
- Wrist dropping below shoulder is a clear, late landmark in the serve motion
- Returns the **first** frame after contact meeting this condition

**Confidence:** 0.7

**Dependency:** Requires `contact_frame` to be detected.

---

## Monotonic Enforcement

After all 8 phases are independently detected, we **enforce temporal ordering**:

```python
def _enforce_monotonic(detections, ...):
    ordered_phases = []
    last_frame = -1

    for phase in PHASE_ORDER:
        if phase not in detections:
            continue
        frame, confidence = detections[phase]
        if frame <= last_frame and phase != ServePhase.START:
            continue  # Out of order — discard this phase
        ordered_phases.append((phase, frame, confidence))
        last_frame = frame
```

**What this means:**
- Phases must appear in the order: Start → Release → Loading → Cocking → Acceleration → Contact → Deceleration → Finish
- If a phase is detected **out of order** (e.g., Loading detected after Cocking), it is **discarded**
- This prevents illogical phase sequences (e.g., "you can't load after you've already cocked")

**Why phases might be out of order:**
- **Loading vs. Cocking timing:** In real serves, deepest knee bend can occur slightly before or after the trophy pose, depending on player technique
- **Heuristic detection errors:** If a heuristic misfires (e.g., false peak in `knee_hip_ratio`), it might place a phase in the wrong spot
- **Pose detection noise:** Missing frames or jittery keypoints can cause detection gaps

**Consequence of monotonic enforcement:**
- This is why you sometimes see **only 3 phases** (Start, Release, Loading) — later phases may have been discarded due to ordering violations
- This is a **known limitation** of the current heuristic approach

---

## Why Only 3 Phases Show Up Sometimes

If your screenshot shows only **Start, Release, Loading**, here's what's likely happening:

1. **Contact timestamp is missing**
   - If `contact_timestamp` is `None`, then Contact, Deceleration, and Finish **cannot be detected** (they depend on contact)
   - This eliminates 3 phases immediately

2. **Cocking not detected**
   - `both_arms_raised` was never `True` in the serve window
   - Possible causes: player never reached trophy pose, or pose detection missed the arms

3. **Acceleration detected out of order**
   - If Acceleration was detected before Cocking (or Loading), monotonic enforcement drops it
   - This can happen if wrist velocity spikes early (e.g., during the toss) and the 2x threshold isn't high enough

4. **Monotonic enforcement dropped later phases**
   - Even if Cocking/Acceleration were detected, they might have been out of order relative to Loading
   - Example: If Loading frame > Cocking frame, Loading is discarded

**To debug:**
- Check if `contact_timestamp` exists for the serve window (query `serve_windows` table)
- Log the raw `detections` dict before `_enforce_monotonic` runs to see which phases were initially found
- Inspect the `both_arms_raised` and `max_wrist_height` features for the serve window to see if trophy pose was captured

---

## System Context: What Exists and What Doesn't

### Existing Infrastructure: Ball Detection

Ball detection is already implemented and integrated:

- **YOLO-based detection** (Ultralytics, COCO class 32 — "sports ball") runs as part of the video analysis job, after pose detection.
- Per-frame ball positions are stored in the **`ball_detections`** table (`ball_data` JSON: `frame_index`, `timestamp_ms`, `ball_x`, `ball_y`, `confidence`).
- **Toss metrics** are computed from ball data: `toss_peak_height` (normalized by player height) and `toss_peak_timestamp` (when ball reaches peak), in `pose_data_service._compute_toss_metrics()`.
- The frontend **overlay** displays ball positions and a ball trail (e.g. `VideoOverlay.tsx`, `StickFigureCanvas.tsx`).

Ball data is used today for toss metrics and visualization; it is not yet used to auto-detect contact (see plan for auto-contact from ball + wrist).

### Camera Angle Gap

- **Serve window detection** is camera-aware: `heuristic_detector.py` uses `AngleProfile` with different thresholds for `"behind"` vs `"profile"` (gap merge, padding, velocity, duration).
- **Phase segmentation and feature extraction are not camera-aware:** `phase_segmentation.py` and `feature_extractor.py` do not receive or use `camera_angle`. The same velocity and position heuristics apply for every view.
- **Consequence:** Behind-camera compresses lateral motion (wrist velocity looks smaller); profile view shows full lateral motion. Velocity-based phases (e.g. Acceleration) may behave differently by angle without any adjustment.

### Racket Tracking

- There is **no racket object detection**. MediaPipe provides pose keypoints only (33 body landmarks); YOLO is used only for the ball (COCO class 32), not for tennis racket (class 38).
- The **`racket_drop_depth`** metric is a **wrist proxy**: it uses dominant wrist position relative to shoulder, `(wrist_y - shoulder_y) / torso_length`, and assumes the racket follows the wrist. It is computed in `angle_calculations.calculate_racket_drop_depth()` between cocking and contact phases.
- So "racket" metrics are biomechanical proxies from pose, not actual racket tracking.

### Contact UI

- Contact timestamp **can** be set in the UI: "Mark Contact" in `ServeWindowRange` (hover), click-to-set in `TimelineMarkers`, keyboard shortcut `C` in `AddServeWindowButton`, and editing in `ServeWindowModal`.
- **Contact is the keystone:** without a set `contact_timestamp`, Contact, Deceleration, and Finish phases cannot be detected — so only 3 phases may appear (Start, Release, Loading) if contact is never tagged. Auto-detecting contact from ball + wrist data is intended to fill this gap when the user has not tagged it.

---

## Confidence Scores

Each phase has a **confidence score** (0.0–1.0):

| Phase | Confidence | Reasoning |
|-------|-----------|-----------|
| Start | 1.0 | Trivial (first frame) |
| Contact | 1.0 | Ground truth from user tag |
| Release | 0.8 | Clear landmark (wrist above shoulder), robust to noise |
| Cocking | 0.7 | Relies on `both_arms_raised` + peak height; can miss trophy pose |
| Loading | 0.7 | Knee-hip ratio is noisy; deepest bend can be ambiguous |
| Finish | 0.7 | Clear landmark (wrist below shoulder), but requires contact |
| Acceleration | 0.6 | Velocity is noisy; 2x threshold is conservative but imperfect |
| Deceleration | 0.6 | Velocity drop after contact; threshold-based, can be ambiguous |

**Lower confidence ≠ wrong.** It means the heuristic is more susceptible to noise or edge cases.

---

## Future Improvements

### 1. Improve Cocking/Loading Ordering
- Loading and Cocking often occur close together, and their relative timing varies by player
- Could use a **temporal window** (e.g., "Loading must be within 0.5s of Cocking") instead of strict ordering

### 2. Ball Tracking for Contact
- Currently contact is user-tagged
- Automatic ball tracking (planned) would provide ground-truth contact timestamps for all serves

### 3. Velocity Smoothing
- Apply Gaussian smoothing to `max_wrist_velocity` before Acceleration/Deceleration detection
- Would reduce false positives from pose jitter

### 4. Multi-Heuristic Fusion
- Use multiple features per phase (e.g., Cocking = trophy pose + shoulder angle + torso rotation)
- Combine with weighted voting for more robust detection

### 5. ML Phase Classifier
- Train a temporal model (LSTM, Transformer) on labeled serve sequences
- Would replace heuristics with learned phase boundaries
- Requires labeled training data (ground-truth phase annotations)

---

## Key Takeaways

1. **Phases are detected using simple, interpretable heuristics** — no ML models
2. **Contact is ground truth** (user-tagged) — all other phases are inferred from pose keypoints
3. **Monotonic enforcement** discards out-of-order phases, which can reduce detection count
4. **Velocity-based phases** (Acceleration, Deceleration) are less confident due to pose noise
5. **Trophy pose (Cocking)** is the visual landmark for Stage 4, but the phase name is "Cocking" per Kovacs
6. **Missing contact timestamp** prevents detection of Contact, Deceleration, and Finish

**For production:** If phase detection is unreliable, prioritize improving pose quality (better lighting, camera angle, MediaPipe refine pass) and ensuring contact timestamps are tagged.
