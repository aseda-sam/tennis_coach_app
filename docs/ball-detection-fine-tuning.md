# Ball Detection: YOLOv8 Fine-Tuning Guide

## Why YOLO

YOLOv8 is a bounding-box detector. It works per-frame, handles large objects well, and is easy to fine-tune on custom data. Combined with ByteTrack (via the `supervision` library), it provides persistent track IDs across frames — separating the moving ball from static background objects without any manual calibration.

## What fine-tuning is

YOLOv8 ships pretrained on COCO (80 object classes including "sports ball"). Fine-tuning takes this model and specialises it: we keep all the learned visual features (edges, textures, shapes) but teach it specifically what a tennis ball looks like in various conditions. This is much faster and more accurate than training from scratch.

## What labeling is

Each training image has a bounding box drawn around the tennis ball, stored as a `.txt` file with `class x_center y_center width height` (normalised 0-1). The Roboflow dataset already has 3,895 images labeled this way.

## Fine-tuning workflow

### 1. Download the dataset

```bash
pip install roboflow
```

```python
from roboflow import Roboflow

rf = Roboflow(api_key="YOUR_API_KEY")
project = rf.workspace().project("tennis-ball-detection")
version = project.version(1)
dataset = version.download("yolov8")
# Downloads to ./tennis-ball-detection-1/ with data.yaml, train/, valid/, test/
```

### 2. Train

```bash
yolo detect train \
    model=yolov8s.pt \
    data=tennis-ball-detection-1/data.yaml \
    epochs=50 \
    imgsz=640 \
    batch=16 \
    name=tennis_ball
```

- `yolov8s.pt` — "small" variant, good balance of speed and accuracy
- `imgsz=640` — standard YOLO input size, works well for our ball sizes
- `epochs=50` — start here; check val mAP, increase if still improving

Training outputs to `runs/detect/tennis_ball/`.

### 3. Evaluate

After training, check `runs/detect/tennis_ball/`:
- `results.csv` — per-epoch metrics (mAP50, mAP50-95, precision, recall)
- `confusion_matrix.png` — false positives / negatives
- `val_batch*_pred.png` — visual predictions on validation images

Key metrics to look for:
- **mAP50 > 0.85** — good baseline for single-class detection
- **Precision > 0.9** — few false positives (important: we don't want ghost balls)
- **Recall > 0.8** — catches most real balls (gaps are OK, our spline fills them)

### 4. Deploy

```bash
cp runs/detect/tennis_ball/weights/best.pt ml_models/yolo_tennis_ball.pt
```

The app loads from `ml_models/yolo_tennis_ball.pt` automatically.

## Pipeline overview

YOLO produces `(ball_x, ball_y, confidence)` per frame. ByteTrack assigns persistent track IDs. Peak-window displacement selects the ball's track. Cubic spline interpolation fills short detection gaps.

## Adding your own labeled data

To improve accuracy on our specific camera angles:

1. **Extract frames** from your serve videos:
   ```bash
   ffmpeg -i serve_video.mp4 -vf "fps=5" frames/frame_%04d.jpg
   ```

2. **Upload to Roboflow** (free tier: 10k images):
   - Create project → Upload images → Draw bounding boxes around the ball
   - Export in "YOLOv8" format

3. **Merge with existing dataset:**
   - Copy your labeled images/labels into the existing `train/` and `valid/` folders
   - Re-run training with the combined dataset

4. **Re-train** with the same command from step 2 above.

Good candidates for labeling: frames where the ball is partially occluded, in shadow, or against a cluttered background.
