# Ball Detection: YOLOv8 Fine-Tuning Guide

## Read this first (retraining strategy)

This project is a personal-use tool — it only ever needs to work on the courts you actually play at
(currently: **Royal Victoria** and **Lyle Park**, both in Newham, London). That changes the strategy:

- **Narrow distribution is your friend.** A general tennis-ball detector has to handle thousands of courts. You have two. Fine-tuning a few hundred frames from *your* courts can move detection from broken to usable in one round, where the same effort applied to a general model would be invisible.
- **Foliage backgrounds are the dominant failure mode.** A yellow ball against mid-spring tree canopy is camouflage, not occlusion — the model rejects the ball alongside thousands of similar-looking leaf-gap blobs. The ball is *visible to a human* in nearly every failure frame; the model just can't separate it from the noise floor.
- **Realistic expectation:** detection rate on canopy-background frames goes from ~10–15% to **60–85%** after one round of fine-tuning with 150–400 well-chosen frames. That's enough for the spline smoother to fill the rest. *(Caveat: those numbers were measured before the static-distractor filter shipped 2026-05-08, which corrected previously-inflated rates. See "Post-fix baseline (2026-05-08)" below.)*

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

### Post-fix baseline (2026-05-08)

The Round-1 / Round-2 numbers above were measured against the old pipeline, where the `bt_kept / yolo_detected ≥ 25%` safety net + per-frame `argmax(confidence)` fallback inflated rates by treating *any* high-confidence detection (including stationary balls on the court) as the serve ball. After the static-distractor filter + min-displacement gate shipped (ADR 005), the rates now reflect the *moving* serve ball only.

Measured with `backend/scripts/measure_ball_detection.py`, defaults `conf=0.25`, `max_gap=15`, `min_anchors=2`:

| Video | Resolution | Raw | Spline | After-spline | Empty windows |
|---|---|---|---|---|---|
| v29 | 406×720 | 19/867 (2.2%) | 0 | 2.2% | **6/10** |
| v37 | 1080p | 40/666 (6.0%) | 10 | 7.5% | 0/7 |
| v38 | 1080p | 22/343 (6.4%) | 0 | 6.4% | 0/4 |
| v39 | 1080p | 10/254 (3.9%) | 0 | 3.9% | 1/3 |

**Honest reading:**
- Raw rates of 4–7% per window mean the model only detects the ball as a 3–5 frame burst at the toss apex. Nothing during flight, nothing after contact.
- Lowering `DEFAULT_CONFIDENCE` from 0.25 → 0.15 produced **identical** numbers — the model is bimodal: it either sees the ball at conf 0.55–0.75 or doesn't see it at all. There's no gray zone to recover.
- The spline almost never fires (1 event in 24 windows). With one isolated burst per window and no detections on either side, there's nothing to bridge.
- 720p videos are bottlenecked by resolution: v29 has 6/10 windows entirely empty.
- Practical impact on biomechanics is small: `toss_peak_height` and `toss_drop` only need the apex burst + contact timestamp, both of which we have.

**The `DEFAULT_CONFIDENCE = 0.25` and spline params are not actively hurting** — there's nothing useful to tune here without first improving recall on motion-blurred / low-resolution frames. That's a Round-3 dataset question, not a parameter knob.

### Round 3 playbook (informed by post-fix baseline)

Round 1 and Round 2 were "broad coverage" rounds — get the model working at all on these courts. The post-fix baseline shows the bottleneck has shifted: the model has decent precision on apex frames and good true-negative behaviour, but **near-zero recall on the ball during flight and after contact**. Round 3 is a *targeted* round aimed at exactly those failure modes. Different goal → different frame selection, different annotation effort, different training settings.

Work through this top to bottom. Each section is a checklist.

#### Step 1 — Frame selection

Goal: build a dataset where the model is forced to learn the cases it currently fails on.

**Resolution:**
- ☐ Use **only 1080p videos** (post-May 2026, transcoder-output 608×1080). Ignore the `training_frames` directory; use `training_frames_1080` only.
- ☐ Do not mix 720p frames into the Round 3 dataset version. Inference distribution is 1080p; 720p is out of distribution and was hurting v29.

**Frame mix — aim for ~250 frames total, weighted as follows:**

| Type | % of dataset | What it looks like | Why |
|---|---|---|---|
| Mid-flight toss | **40–50%** | Ball ascending between trophy/release and apex. Often small, motion-blurred, against canopy. | Highest value. The model currently has near-zero recall here. |
| Right after contact | **15–20%** | Ball moving away from racket, very motion-blurred, small. Use the 2–8 frames after contact_timestamp. | Currently zero recall. |
| Just before contact | **10–15%** | Ball descending toward the racket, ~30° pre-contact zone. | Improves contact-frame detection for biomechanics. |
| Apex anchor | **10–15%** | Ball at toss apex (where current model already works). | Anchor — prevents Round 3 from forgetting the case Round 2 learned. |
| Null / hard negative | **5–10%** | Frames with no visible ball, especially canopy / fence / leaf-gap regions. | Just enough to keep true-negative behaviour; no longer the bottleneck. |

**How to find frames:**
- ☐ For each candidate video, scrub through Roboflow's video-frame uploader and pick frames manually for now. The current `extract_training_frames.py` only targets *apex-region failures + easy anchors* — it misses the flight regions we need. (See Step 6 for a planned extension.)
- ☐ **Hard rule: only label frames where you can see the ball with the human eye.** Uncertain frames ("is that a ball or a leaf?") hurt training more than they help. If you have to squint, skip it.
- ☐ Sample across multiple videos (4–6) so the model doesn't overfit to one lighting/court.

#### Step 2 — Annotation effort

The labelling cost per frame is higher than Round 2 because the current weights can't auto-detect flight frames. Plan accordingly.

- ☐ Mid-flight / post-contact frames: **manual rectangle tool**, ~30 sec each. SAM3 Smart Select struggles with motion blur — don't bother.
- ☐ Apex anchor frames: SAM3 Smart Select → polygon → Convert to box. ~10 sec each.
- ☐ Null frames: 0 boxes, 1 sec to confirm and save.
- ☐ Total budget: ~125 frames × 30 sec + 75 frames × 10 sec + 25 frames × 1 sec ≈ **75–90 minutes of pure labelling.** Plus ~30 min for frame selection. ~2 hours end-to-end.

#### Step 3 — Roboflow dataset settings

Different from Round 1+2: turn augmentation **on** for the first time.

- **Preprocessing:** Auto-Orient only. No resize (YOLO handles imgsz internally).
- **Augmentation (Round 3 first run, conservative):**
  - ☐ **Motion blur, small intensity** (kernel 1–3 px). Highest leverage — synthesizes flight-like examples from clear ones.
  - ☐ **Hue/saturation ±15%**. Helps canopy-vs-ball separation under different lighting.
  - ☐ **Small rotations ±5°**. Phone-tilt invariance.
  - ☐ **Skip horizontal flip.** Would put the ball on the wrong side of the player relative to dominant-hand assumptions.
  - ☐ **Skip vertical flip and large rotations** — these break gravity-aware features (apex is up, contact is down).
- **Validation split — manual check required:**
  - Roboflow's auto-split is random. With our targeted dataset, that risks a validation set dominated by easy apex frames, making mAP look great while real-world recall stays bad.
  - ☐ After auto-splitting, manually move frames so that **at least 30% of the validation set is mid-flight / post-contact frames**. mirror the train distribution roughly.

#### Step 4 — Colab training tweaks

Most settings stay the same as Round 2; two changes.

```python
from ultralytics import YOLO

model = YOLO("yolo_tennis_ball.pt")  # Round 2 weights, NOT yolov8s.pt

results = model.train(
    data=f"{dataset.location}/data.yaml",
    epochs=50,        # was 30 — Round 3 examples are harder
    imgsz=1280,       # unchanged
    batch=8,          # unchanged (T4 OOMs at 16)
    name="tennis_ball_london_v3",
    patience=10,      # early-stop if val mAP plateaus
    save=True,
    plots=True,
)
```

- ☐ **Start from Round 2 weights** (`yolo_tennis_ball.pt`), not COCO. Round 2 already learned the easy cases; Round 3 only needs to refine the hard ones.
- ☐ **50 epochs** (vs. Round 2's 30). The harder examples need more training time. `patience=10` handles plateaus.
- ☐ Watch `runs/detect/tennis_ball_london_v3/results.csv`. Healthy run: precision stays high (>0.9), recall climbs slowly (target: 0.85+ after 30+ epochs).
- ☐ **Watch for overfitting:** if training mAP keeps climbing while validation mAP plateaus or drops, stop. With only ~250 frames, this is a real risk. The early-stop will catch most cases.

#### Step 5 — Verify on the baseline videos

After training, before deploying:

- ☐ Download `runs/detect/tennis_ball_london_v3/weights/best.pt` to a *temporary* location (not yet `backend/ml_models/`).
- ☐ Run the measurement script with the new weights:
  ```bash
  # Temporarily symlink or copy best.pt as the active weight
  cp best.pt /tmp/round3_best.pt
  YOLO_MODEL_OVERRIDE=/tmp/round3_best.pt \
    docker compose exec backend python scripts/measure_ball_detection.py \
      --video-ids 37 38 39
  ```
  *(Note: the override env var doesn't exist yet — you'd either need to add it as a small change to `_get_model()`, or just temporarily replace `backend/ml_models/yolo_tennis_ball.pt` and remember to restore.)*
- ☐ **Target metrics post-Round 3** (rough, not promises):
  - Raw rate per window: **15–30%** (vs. current 4–7%) — meaning ~15 frames of ball detected per window instead of 5.
  - Spline activation: should fire on **most windows** (vs. current 1 in 24) — because we'd have detections before AND after the apex now.
  - Empty windows: **0** on 1080p videos. v29 (720p) will likely still have empties; that's OK.
- ☐ If results are worse than baseline, do not deploy. Diagnose: check val mAP curve, check label quality on a sample of flight frames.

#### Step 6 — Future improvement: `--mode flight` for the extract script

Manual frame-picking is the slow step in Round 3. A targeted extraction mode would halve the time.

- **Idea:** add `--mode flight` to `backend/scripts/extract_training_frames.py`. For each accepted serve window, extract 5–10 evenly-spaced frames from the **20–60% region** of the toss arc (between toss start and apex), regardless of current detection state. This is exactly the band where the model fails.
- **Effort:** ~2 hours. Reuses existing window-iteration code.
- **When to do it:** if you're going to repeat Round 3 (or Round 4), the script pays for itself in 30 min of saved labelling. If Round 3 is the only round, manual frame-picking is fine.
- **Status:** not yet implemented. Captured in `backlog/inbox.md` as a follow-up.

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

### Resolved: static-distractor filter (video 39, 2026-05-08)

**Symptom:** ball detection runs without error, 100% detection rate, but no ball appears in the stick-figure view for any serve window.

**Cause:** the (32, 564) cluster is a **real tennis ball lying on the court**, not a fence post or court marking. The fine-tuned model detects it confidently in every frame at ~0.74 confidence. With multiple stationary balls present (a second one at ~(200, 1058) appeared in serves 2–4), the moving serve ball — detected only as 3–5 frame bursts at the toss apex — was a small minority of YOLO's output and lost both the track-selection and the safety-net fallback.

Two layered failures:

1. **Selection-by-default in `_select_ball_track`.** When the moving ball formed only 1-frame fragments (no peak-window displacement), the static track was the sole multi-frame candidate and won with peak ≈ 1 px from sub-pixel jitter.
2. **`bt_kept / yolo_detected >= 0.25` safety net.** When the moving ball *did* form a 3–5 frame track, its retention ratio (5/~94 ≈ 5%) tripped the safety net. The fallback `argmax(confidence)` per frame then picked the static ball (conf 0.74) over the moving ball (conf ~0.55) every time.

**Fix (shipped 2026-05-08, see ADR 005):** pooled static-distractor scan across all serve windows, plus a minimum peak-displacement gate in `_select_ball_track`. The 25% safety net is removed. Auto-pipeline ball detection is now off by default (`AUTO_BALL_DETECTION_ON_UPLOAD`); the manual "Re-run ball detection" button in `ServeWindowsPanel` is the canonical entry point, with a `is_ball_detection_stale` indicator surfacing on window edits.

**Lesson:** "ByteTrack handles static separation" was true for the older, weaker model that produced few false positives on background. With a stronger fine-tuned model, *real* incidental balls become first-class detections and need explicit handling. Multiple balls per session is the rule, not the exception.

### What fine-tuning is

Fine-tuning takes an existing trained model and specialises it: keep the learned visual features (edges, textures, shapes) but teach it what a tennis ball looks like in *your* conditions. Faster and more accurate than training from scratch. Each round should start from the *previous round's output*, not from `yolov8s.pt`.

### Pipeline overview

YOLO produces `(ball_x, ball_y, confidence)` per frame. ByteTrack assigns persistent track IDs. Peak-window displacement selects the ball's track. Cubic spline interpolation fills short detection gaps (≤8 frames; longer gaps left as None).

### Roboflow projects

- **`tennis-ball-aseda-london`** (workspace: `aseda-test`) — your court-specific labeled frames. Use this for fine-tuning rounds.
- **`tennisball-3eqxr / tennis-ball-detection-qaxae`** — original 3,895-image public dataset used for initial training. Already baked into `yolo_tennis_ball.pt` — no need to re-download unless rebuilding from scratch.
