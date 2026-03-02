# ML Models Directory

This directory contains machine learning models used by the tennis coach application.

## Models

### MediaPipe Pose Landmarker (`pose_landmarker.task`)

- **Purpose**: Pose estimation for biomechanics analysis
- **Model**: MediaPipe Pose Landmarker Heavy (33 keypoints)
- **Size**: ~40MB (downloaded automatically)
- **Usage**: Detects player pose keypoints for serve analysis

### YOLOv8 Tennis Ball Detector (`yolo_tennis_ball.pt`)

- **Purpose**: Ball detection and tracking for toss analysis
- **Model**: Fine-tuned YOLOv8 with ByteTrack tracking
- **Usage**: Detects tennis ball per serve window; tracked with ByteTrack for persistent IDs

## Automatic Download

The model is automatically downloaded on first use to `backend/ml_models/pose_landmarker.task`.

If you need to force a re-download, delete the file and restart the backend.

## Configuration

Model path is configured in `app/core/config.py`:

```python
ML_MODELS_DIR: str = "ml_models"  # Relative to backend/
```

## Notes

- Model files are large and are not committed to Git (see `.gitignore`)
- The model is downloaded from Google's MediaPipe storage on first use
- MediaPipe pose model and YOLOv8 ball detection model are both actively used
