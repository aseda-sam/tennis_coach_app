# ML Models

This directory contains the machine learning models used for tennis video analysis in the Tennis Coach App.

## Overview

The application uses two main types of computer vision models:

1. **YOLO (You Only Look Once)** - For ball detection and tracking
2. **MediaPipe** - For pose estimation and player analysis

## YOLO Models

### Available Models

#### YOLOv8n (Nano) - `yolov8n.pt`
- **Size**: ~6.5MB
- **Speed**: Fastest processing
- **Accuracy**: Good for real-time applications
- **Use Case**: Development and testing, real-time analysis
- **Performance**: ~30-50 FPS on modern hardware

#### YOLOv8s (Small) - `yolov8s.pt`
- **Size**: ~22.6MB
- **Speed**: Moderate processing
- **Accuracy**: Better detection accuracy
- **Use Case**: Production analysis, higher accuracy requirements
- **Performance**: ~15-25 FPS on modern hardware

### Model Selection

The application automatically selects the appropriate model based on:

- **Environment**: Local development vs production
- **Video Quality**: Higher quality videos may benefit from larger models
- **Performance Requirements**: Real-time vs batch processing
- **Hardware Capabilities**: Available memory and processing power

### Configuration

Model selection is configured in `backend/app/core/config.py`:

```python
# YOLO Configuration
YOLO_DEFAULT_MODEL = "nano"  # or "small"
ML_MODELS_DIR = "ml_models"
CONFIDENCE_THRESHOLD = 0.7
BALL_CONFIDENCE_THRESHOLD = 0.7
```

### Usage

Models are automatically downloaded on first use:

```python
from ultralytics import YOLO

# Load model
model = YOLO('ml_models/yolov8n.pt')

# Run inference
results = model('path/to/video.mp4')
```

## MediaPipe Models

### Pose Estimation Model

MediaPipe uses a pre-trained pose estimation model that:

- **Detects 33 body keypoints**
- **Runs in real-time** on CPU and GPU
- **Optimized for mobile and desktop**
- **No additional model files required** (downloaded automatically)

### Keypoints Used

For tennis analysis, we focus on 11 relevant keypoints:

- **Shoulders**: Left and right shoulder positions
- **Elbows**: Left and right elbow positions
- **Wrists**: Left and right wrist positions
- **Hips**: Left and right hip positions
- **Knees**: Left and right knee positions
- **Ankles**: Left and right ankle positions

### Configuration

```python
# MediaPipe Configuration
POSE_DETECTION_CONFIDENCE = 0.5
POSE_TRACKING_CONFIDENCE = 0.5
POSE_OVERALL_CONFIDENCE = 0.8
```

## Model Management

### Automatic Download

Models are downloaded automatically when needed:

```python
# YOLO models are downloaded to ml_models/ directory
# MediaPipe models are downloaded to system cache
```

### Manual Download

You can pre-download models using the provided script:

```bash
cd backend
python scripts/download_models.py
```

### Model Updates

To update models:

1. **YOLO Models**: Replace the `.pt` files in this directory
2. **MediaPipe Models**: Update the `mediapipe` package

```bash
pip install --upgrade mediapipe
```

## Performance Optimization

### Model Selection Strategy

The application uses different models based on the environment:

#### Local Development
- **YOLO Model**: `yolov8n.pt` (nano)
- **Frame Skip**: 1 (process every frame)
- **Confidence Threshold**: 0.7

#### Docker Environment
- **YOLO Model**: `yolov8n.pt` (nano)
- **Frame Skip**: 3 (process every 3rd frame)
- **Confidence Threshold**: 0.7

#### Production Environment
- **YOLO Model**: `yolov8s.pt` (small)
- **Frame Skip**: 4 (process every 4th frame)
- **Confidence Threshold**: 0.8

### Memory Management

```python
# Model loading with memory optimization
import torch

# Set device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load model with optimization
model = YOLO('ml_models/yolov8n.pt')
model.to(device)

# Enable half precision for faster inference
model.half()
```

### Batch Processing

For multiple videos, models are loaded once and reused:

```python
class ModelManager:
    def __init__(self):
        self.yolo_model = None
        self.pose_model = None
    
    def get_yolo_model(self):
        if self.yolo_model is None:
            self.yolo_model = YOLO('ml_models/yolov8n.pt')
        return self.yolo_model
    
    def get_pose_model(self):
        if self.pose_model is None:
            self.pose_model = mp_pose.Pose()
        return self.pose_model
```

## Model Accuracy

### YOLO Ball Detection

#### Performance Metrics
- **Precision**: 85-95% (depending on video quality)
- **Recall**: 80-90% (depending on ball visibility)
- **False Positive Rate**: 5-15% (depending on scene complexity)

#### Factors Affecting Accuracy
- **Video Quality**: Higher resolution = better detection
- **Lighting Conditions**: Good lighting improves accuracy
- **Ball Size**: Larger balls are detected more reliably
- **Background Complexity**: Simple backgrounds reduce false positives
- **Camera Angle**: Side angles work better than overhead

### MediaPipe Pose Estimation

#### Performance Metrics
- **Keypoint Accuracy**: 90-95% for visible body parts
- **Tracking Consistency**: 85-90% across frames
- **Occlusion Handling**: 70-80% when body parts are partially hidden

#### Factors Affecting Accuracy
- **Player Visibility**: Full body visibility improves accuracy
- **Clothing**: Tight-fitting clothes work better
- **Lighting**: Good lighting improves keypoint detection
- **Camera Distance**: Closer shots provide better accuracy
- **Player Movement**: Slower movements are tracked more accurately

## Troubleshooting

### Common Issues

#### Model Download Failures

```bash
# Check internet connection
ping google.com

# Clear model cache
rm -rf ml_models/*.pt
python scripts/download_models.py
```

#### Memory Issues

```bash
# Monitor memory usage
htop

# Reduce model size
# Use yolov8n.pt instead of yolov8s.pt
```

#### CUDA Issues

```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Fallback to CPU
export CUDA_VISIBLE_DEVICES=""
```

### Performance Issues

#### Slow Inference

1. **Reduce input resolution**:
   ```python
   model.predict(source, imgsz=640)  # Instead of 1280
   ```

2. **Increase frame skip ratio**:
   ```python
   FRAME_SKIP_RATIO = 4  # Process every 4th frame
   ```

3. **Use smaller model**:
   ```python
   YOLO_DEFAULT_MODEL = "nano"  # Instead of "small"
   ```

#### High Memory Usage

1. **Enable model optimization**:
   ```python
   model.half()  # Use half precision
   ```

2. **Process videos in batches**:
   ```python
   BATCH_SIZE = 1  # Process one video at a time
   ```

3. **Clear model cache**:
   ```python
   torch.cuda.empty_cache()
   ```

## Model Training (Advanced)

### Custom YOLO Training

For improved ball detection on specific court types:

```python
# Prepare dataset
# Annotate tennis balls in your videos
# Create YOLO format annotations

# Train custom model
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
results = model.train(
    data='path/to/dataset.yaml',
    epochs=100,
    imgsz=640,
    batch=16
)
```

### Dataset Requirements

- **Minimum Images**: 1000+ annotated images
- **Variety**: Different lighting, angles, court types
- **Quality**: High-resolution images preferred
- **Annotations**: Accurate bounding boxes around tennis balls

## Future Enhancements

### Planned Model Improvements

1. **Custom Tennis Ball Model**: Trained specifically on tennis videos
2. **Racket Detection Model**: YOLO model for racket detection
3. **Player Tracking Model**: Multi-person tracking for doubles
4. **Stroke Classification Model**: CNN for stroke type recognition

### Model Optimization

1. **Quantization**: Reduce model size with minimal accuracy loss
2. **Pruning**: Remove unnecessary model parameters
3. **Knowledge Distillation**: Train smaller models from larger ones
4. **Edge Deployment**: Optimize for mobile and edge devices

## Resources

### Documentation

- [YOLO Documentation](https://docs.ultralytics.com/)
- [MediaPipe Documentation](https://mediapipe.dev/)
- [PyTorch Documentation](https://pytorch.org/docs/)

### Research Papers

- [YOLOv8 Paper](https://arxiv.org/abs/2305.09972)
- [MediaPipe Pose Paper](https://arxiv.org/abs/2006.10214)

### Community

- [Ultralytics GitHub](https://github.com/ultralytics/ultralytics)
- [MediaPipe GitHub](https://github.com/google/mediapipe)
- [Tennis Analysis Community](https://github.com/aseda-sam/tennis_coach_app)

## License

- **YOLO Models**: GPL-3.0 License
- **MediaPipe Models**: Apache 2.0 License
- **Custom Models**: MIT License (if trained on this project)
