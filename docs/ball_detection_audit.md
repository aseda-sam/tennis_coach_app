# Ball Detection Feature — Code Quality Audit

Audit date: branch cleanup. Scope: detection service, model, RQ integration, overlay, toss metrics, frontend. No fixes applied; this document flags issues for a follow-up pass.

---

## 1. `backend/app/services/ball_detection/detection_service.py`

| Issue | Location | Notes |
|-------|----------|--------|
| **Hardcoded constants** | `COCO_SPORTS_BALL_CLASS = 32`, `DEFAULT_CONFIDENCE = 0.25`, model `"yolo11n.pt"` | Consider making confidence (and optionally model name) configurable via `app.core.config` if you need to tune without code change. |
| **Video opened per window** | Loop over `windows` opens `cv2.VideoCapture` for each window | For many serve windows this is redundant. Could open once and seek, or document that window count is typically small. |
| **Empty windows** | No check that `windows` is non-empty | If `windows == []`, `total_frames` stays 0 and returns successfully; caller may want to treat as no-op or warn. |
| **Error handling** | `_error_result` used for import failure and open failure | Clear. No handling for partial failure (e.g. one window fails mid-run). |

---

## 2. `backend/app/models/ball_detection.py`

- Schema is clear: `ball_data` as Text/JSON, `time_windows` stored for traceability.
- No issues flagged.

---

## 3. `backend/app/services/rq_tasks.py` (ball detection block)

| Issue | Location | Notes |
|-------|----------|--------|
| **Hardcoded padding** | `padding_ms=300` passed to `analyze_serve_windows` | Same as detection_service default; consider a single constant or config if you ever want to tune. |
| **Broad except** | `except Exception as ball_err` | Intentionally broad so job continues; documented with noqa. Acceptable. |
| **No record on failure** | When `"error" in ball_results` or exception, no `BallDetection` row is created | Overlay and toss metrics simply see no ball data. Consider an optional `BallDetection(status="failed", error_message=...)` for observability. |

---

## 4. `backend/app/services/serve_analysis_service.py`

| Issue | Location | Notes |
|-------|----------|--------|
| **Type hint** | `_compute_toss_metrics` return type `Dict[str, any]` | Use `Dict[str, Any]` and `from typing import Any` for consistency. |
| **Magic numbers** | `video.height or 720`, `player_height_px = float(video_height) * 0.5`, `duration * 0.8` for end_sec, `video_height * 0.2 - best_y` fallback | Fallbacks are reasonable but undocumented. Consider named constants or a one-line comment. |
| **Toss window** | End of toss = contact_timestamp or 80% of window | Logic is documented in docstring; ensure product intent (80% rule) is still desired. |

---

## 5. `backend/app/services/overlay_data_service.py`

| Issue | Location | Notes |
|-------|----------|--------|
| **Silent parse failure** | `except (json.JSONDecodeError, TypeError, KeyError): pass` when building `ball_by_frame` | Ball overlay is skipped for that video; no log. Consider `logger.debug("Ball data parse failed for video %s: %s", video_id, e)` to aid debugging. |
| **Frame index alignment** | Pose frames from `enumerate(raw_pose_data)`; ball keyed by `frame_index` from detection | Assumes pose and ball use same video frame indices. Holds for current pipeline (same video, same frames). If ever different (e.g. subsampled pose), would need a mapping. |

---

## 6. `frontend/src/components/VideoOverlay.tsx`

| Issue | Location | Notes |
|-------|----------|--------|
| **Constants** | `BALL_TRAIL_LENGTH = 30`, ball radius `(contentWidth + contentHeight) / 150` | Document that 30 ≈ 1s at 30fps; radius divisor 150 is a scale heuristic. |
| **Trail reset** | `ballTrailRef.current = []` in `handleSeeked` | Correct; avoids stale trail after seek. |

---

## 7. `frontend/src/components/ServeAttemptsPanel.tsx`

| Issue | Location | Notes |
|-------|----------|--------|
| **Heuristics** | `getElbowAngleFeedback`, `getKneeBendFeedback` | Already noted elsewhere as candidates for future LLM or rule refinement. |
| **Toss display** | `toss_peak_height.toFixed(2)`, `toss_peak_timestamp` formatted | Straightforward; no issues. |

---

## Summary

- **Critical:** None.
- **Polish / follow-up:** Config or constants for confidence, padding, and magic numbers; optional failed BallDetection record; debug log on ball JSON parse failure; fix `any` → `Any` in serve_analysis_service; short comments for frontend constants.
- **Architecture:** Ball and pose frame indices are aligned by design; document or keep a brief comment if the pipeline changes (e.g. subsampled pose).
