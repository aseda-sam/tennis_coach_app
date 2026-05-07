# Ball Detection: YOLOv8 Fine-Tuning Guide

## Read this first (retraining strategy)

This project is a personal-use tool — it only ever needs to work on the courts you actually play at
(currently: **Royal Victoria** and **Lyle Park**, both in Newham, London). That changes the strategy:

- **Narrow distribution is your friend.** A general tennis-ball detector has to handle thousands of courts. You have two. Fine-tuning a few hundred frames from *your* courts can move detection from broken to usable in one round, where the same effort applied to a general model would be invisible.
- **Foliage backgrounds are the dominant failure mode.** A yellow ball against mid-spring tree canopy is camouflage, not occlusion — the model rejects the ball alongside thousands of similar-looking leaf-gap blobs. The ball is *visible to a human* in nearly every failure frame; the model just can't separate it from the noise floor.
- **Realistic expectation:** detection rate on canopy-background frames goes from ~10–15% to **60–85%** after one round of fine-tuning with 150–400 well-chosen frames. That's enough for the spline smoother to fill the rest.

## Locked-in decisions (don't reopen casually)

These are baked in by the data and the pipeline. Mixing them is what creates train/inference distribution mismatch — the silent killer of retraining effort.

- **Camera angle: `profile` (side view).** The majority of serve videos are profile. Behind footage exists but is the minority. Train on profile only. If you ever standardize on behind, retrain a separate model — don't mix angles in one dataset.
- **Resolution: 608×1080 transcoded video** (changed May 2026 from 406×720; CRF lowered from 23 → 18). The upload pipeline transcodes in place (originals overwritten — see `backend/app/services/rq_tasks.py`). Inference runs on the transcoded file. Train on the transcoded file. Don't substitute originals from your phone, even if you have them — the resulting model will under-perform at inference time. Pre-May 2026 videos are stuck at 406×720 — don't mix them with 1080p frames in the same dataset version.
- **Frame rate: 30 fps.** All videos are normalized by the transcoder.
- **One class only: `ball`.** No sub-types. ByteTrack handles "which ball is the serve ball" downstream; YOLO just finds balls.
- **imgsz: 1280.** Set in `backend/.env` as `YOLO_IMGSZ=1280`. Train and inference imgsz must always match.
- **Underlying principle:** training distribution ⊇ inference distribution. Whatever you don't train on becomes a guess.

---

## Training rounds log

| Round | Date | Frames | Resolution | Roboflow project | Base model | mAP50 (val) | Status |
|---|---|---|---|---|---|---|---|
| 1 | 2026-05-07 | 105 (75/20/10 split) | 406×720 (pre-upgrade) | `tennis-ball-aseda-london` v1 | `yolo_tennis_ball.pt` (3,895-image base) | 0.894 (P=1.00, R=0.83) | Complete |
| 2 | 2026-05-07 | 219 (155/43/21 split) | mixed: 105×406×720 + 114×608×1080 | `tennis-ball-aseda-london` v2 | Round 1 output (`tennis_ball_london_v1/weights/best.pt`) | 0.926 (P=0.964, R=0.865) | Complete |

**Round 1 notes:** 105 frames from Royal Victoria and Lyle Park courts (videos v008, v011, v018, v021, v024, v029, v030, v033). Labeled manually using SAM3 polygon → box conversion in Roboflow. No augmentation. Source resolution is 406×720.

**Round 2 notes:** 219 frames total — Round 1 frames retained + 114 new 1080p frames from videos v035–v039 (608×1080, CRF 18). Mixed resolutions are fine: YOLO rescales internally at imgsz=1280. Validation set grew from 10 to 43 images, making metrics more reliable. Auto-labeled in Roboflow using Round 1 weights, reviewed manually.

**Round 1 real-world results** (ball detection rate per video, before → after):

| Video | Court | Before | After Round 1 | Δ |
|---|---|---|---|---|
| v21 | Royal Victoria | 92.0% | 90.3% | -1.7% (already high) |
| v24 | Royal Victoria | 74.5% | 74.6% | +0.1% |
| v29 | Lyle Park | 66.1% | 81.0% | **+14.9%** |

**Round 2 real-world results** (1080p videos, Round 1 → Round 2):

| Video | Court | After Round 1 | After Round 2 | Δ |
|---|---|---|---|---|
| v35 | TBD | 80.5% | 74.4% | -6.1% |
| v36 | TBD | 70.7% | 75.2% | **+4.5%** |
| v37 | TBD | 86.8% | 87.7% | +0.9% |
| v38 | TBD | 71.6% | 72.5% | +0.9% |
| v39 | TBD | 100.0% | 100.0% | 0% |

---

## The retraining loop

Five steps in order. Each one assumes the previous step is done.

### 1. Try the free wins before labeling

Two zero-training-cost levers exist. Run these on a known-bad serve and benchmark before committing to a labeling round:

1. **`YOLO_IMGSZ=1280`** — already set in `backend/.env`. At imgsz=1280 the model retains more spatial features. Costs ~3× inference time per frame.
2. **Lower `DEFAULT_CONFIDENCE` from 0.25 → ~0.15** (`yolo_detection_service.py`). Skip until *after* fine-tuning — without retrained weights this just floods the pipeline with leaf false positives.

Re-run a known-bad serve through the pipeline and record the detection rate. That's your baseline for measuring whether retraining actually helped.

### 2. Extract training frames

For 406×720 videos (pre-May 2026):
```bash
docker compose exec backend python scripts/extract_training_frames.py \
  --camera-angle profile \
  --player-id 1 \
  --out-dir /app/data/training_frames
```

For 1080p videos (post-May 2026):
```bash
docker compose exec backend python scripts/extract_training_frames.py \
  --camera-angle profile \
  --player-id 1 \
  --out-dir /app/data/training_frames_1080
```

Keep the two output directories separate — different resolution rounds go into different Roboflow dataset versions.

The script:
- Pulls frames from each serve window where ball detection failed, restricted to the **apex region** (15–80% of the window). Tag: `_fail`.
- Adds 3 high-confidence detection frames per video as anchors. Tag: `_easy`.
- Writes `manifest.csv` recording video / serve / frame / tag / detection state.

Aim for **150–400 frames total**. If fewer, bump `--max-fail-per-serve` (default 5) or `--easy-per-video` (default 3).

**Caveat about easy frames:** YOLO can be confidently wrong. Some "easy" frames will have no ball (false positives on fences, leaves). That's fine — they become null-image training signal (see Rule 2 below).

### 3. Label in Roboflow

**Roboflow project:** `tennis-ball-aseda-london` (workspace: `aseda-test`)

Upload frames to a new batch. Label each frame following the rules below.

#### Labeling workflow

Use **SAM3 Smart Select** (polygon mode) for speed, then convert per-image via `... → Convert → Polygons → Boxes (Individual)`. Verify the boxes visually before saving. Switch to the manual rectangle tool for blurry in-flight balls against foliage — SAM3 struggles there.

#### Labeling rules

- **Rule 1 — Label every visible tennis ball.** Including ball in hand pre-toss, ball in flight, stationary balls on court. Don't just label the active serve ball.
- **Rule 2 — Null images are valuable training data.** Frames with *no visible ball* get saved with zero boxes. This teaches the model that fence nodes, leaf gaps, and window patterns are NOT balls.
- **Rule 3 — Skip occluded balls.** Don't box a ball hidden behind the player's body, racket, or fence post.
- **Rule 4 — Tight boxes, including motion blur.** If the ball is a streak, draw the box tight around the streak.
- **Rule 5 — Single class: `ball`.** No sub-classes.

#### Dataset version settings

When generating a version in Roboflow:
- **Preprocessing:** Auto-Orient only. No resize — YOLO handles resizing internally.
- **Augmentation:** None for the first round. Add targeted augmentation (hue/saturation, blur) only if the trained model still fails and you have evidence augmentation would help.
- **Split method:** "Split Images Between Train/Valid/Test" (not "Use Existing Values").

### 4. Train in Colab

The training notebook is `train_yolo_ball_detector.ipynb` (lives in Google Drive/Colab, not in this repo).

**Key principle:** Don't train from `yolov8s.pt` (COCO weights). Start from the *existing* `yolo_tennis_ball.pt` — the 3,895-image base dataset is already baked into those weights. Fine-tuning from there means the new court-specific frames teach the model your conditions without forgetting general tennis ball knowledge.

**Step 1 — Upload the current weights to Colab:**
```python
# In Colab, upload yolo_tennis_ball.pt from ml_models/ or mount Google Drive
```

**Step 2 — Download your Roboflow dataset:**
```python
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace("aseda-test").project("tennis-ball-aseda-london")
version = project.version(1)  # update version number each round
dataset = version.download("yolov8")
```

**Step 3 — Train:**
```python
from ultralytics import YOLO

model = YOLO("yolo_tennis_ball.pt")  # NOT yolov8s.pt

results = model.train(
    data=f"{dataset.location}/data.yaml",
    epochs=30,       # fine-tuning, not scratch training
    imgsz=1280,      # must match YOLO_IMGSZ in backend/.env
    batch=8,         # T4 OOMs at 16 with imgsz=1280
    name="tennis_ball_london_v1",
    patience=10,
    save=True,
    plots=True,
)
```

Free Colab T4 handles ~100 images × 30 epochs in ~5–10 min.

Watch per-epoch metrics in `runs/detect/tennis_ball_london_v1/results.csv`:
- **mAP50 > 0.85** — good baseline for single-class detection
- **Precision > 0.9** — important: false positives waste ByteTrack tracks downstream
- **Recall > 0.8** — gaps are filled by the spline smoother

### 5. Deploy and verify

Download `runs/detect/tennis_ball_london_v1/weights/best.pt` from Colab and replace the weights:

```bash
cp best.pt backend/ml_models/yolo_tennis_ball.pt
```

Re-run a known-bad serve through `scripts/annotate_ball_tracking.py` and confirm detection rate on canopy frames moved up. If it didn't, check labels — review a handful of annotations before doing another round.

---

## Reference

### Why YOLO

YOLOv8 is a bounding-box detector. It works per-frame and is easy to fine-tune on custom data. Combined with ByteTrack (via the `supervision` library), it provides persistent track IDs across frames — separating the moving ball from static background objects without manual calibration.

Full architecture rationale: [ADR 002](../../docs/decisions/002-yolo-bytetrack-ball-detection.md).

### Known issue: static false-positive locks out the real ball (video 39, 2026-05-07)

**Symptom:** ball detection runs without error, 100% detection rate, but no ball appears in the stick-figure view for any serve window.

**Cause:** YOLO latched onto a fixed object at ~(32, 564) in every frame — probably a court marking, fence post, or similar feature at the far-left edge of the frame. ByteTrack kept it as a single persistent track. `_select_ball_track` then picked it as the "best" track because it was the only (or dominant) track. The actual moving ball was either not detected at all or detected on a shorter, lower-displacement track that lost the selection.

**Why it's invisible in the UI:** After normalization, x≈32 maps to ~184px left of the body's hip center. With the stick-figure scale, that renders off the left edge of the canvas.

**Fix needed in `_select_ball_track`:** add a minimum peak-displacement threshold (e.g. 5px). Reject any track whose peak-window displacement is below the threshold; return `None` rather than a static false positive. This prevents a parked object from winning when no real ball motion is found.

### What fine-tuning is

Fine-tuning takes an existing trained model and specialises it: keep the learned visual features (edges, textures, shapes) but teach it what a tennis ball looks like in *your* conditions. Faster and more accurate than training from scratch. Each round should start from the *previous round's output*, not from `yolov8s.pt`.

### Pipeline overview

YOLO produces `(ball_x, ball_y, confidence)` per frame. ByteTrack assigns persistent track IDs. Peak-window displacement selects the ball's track. Cubic spline interpolation fills short detection gaps (≤8 frames; longer gaps left as None).

### Roboflow projects

- **`tennis-ball-aseda-london`** (workspace: `aseda-test`) — your court-specific labeled frames. Use this for fine-tuning rounds.
- **`tennisball-3eqxr / tennis-ball-detection-qaxae`** — original 3,895-image public dataset used for initial training. Already baked into `yolo_tennis_ball.pt` — no need to re-download unless rebuilding from scratch.
