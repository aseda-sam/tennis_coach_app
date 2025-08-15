# Video Processing Performance Analysis

## Overview

This document analyzes the performance bottlenecks in our tennis video processing pipeline and provides testing strategies to determine optimal defaults for different environments.

## Bottleneck Analysis

### 1. **Primary Bottlenecks (in order of impact)**

#### **YOLO Model Processing** - Most CPU/GPU intensive
- **Impact**: 70-80% of processing time
- **Details**: YOLOv8n processes each frame through neural network
- **M1 MacBook Pro**: Benefits from Neural Engine acceleration
- **Docker**: Limited by container CPU/memory constraints

#### **Frame Resolution** - Exponential impact
- **4K (3840x2160)**: 8,294,400 pixels per frame
- **1080p (1920x1080)**: 2,073,600 pixels per frame
- **Impact**: 4K is 4x more pixels = 4x more processing time

#### **Frame Rate** - Linear impact
- **30fps**: 30 frames per second
- **60fps**: 60 frames per second
- **Impact**: 60fps = 2x more frames to process

#### **Memory Usage** - Storage bottleneck
- **4K frame**: ~24MB uncompressed RGB
- **1080p frame**: ~6MB uncompressed RGB
- **Impact**: High memory usage can cause crashes

#### **FFmpeg Operations** - I/O bottleneck
- **Video encoding/decoding**: CPU intensive
- **Impact**: Affects video creation and streaming

### 2. **Environment-Specific Considerations**

#### **M1 MacBook Pro (Local)**
**Advantages:**
- **Neural Engine**: Optimized for ML workloads
- **Unified Memory**: Fast GPU-CPU data transfer
- **ARM64**: Efficient for modern workloads
- **8-core CPU**: Good parallel processing

**Limitations:**
- **Memory**: 8GB or 16GB unified memory
- **Thermal throttling**: Under sustained load

#### **Docker Container**
**Advantages:**
- **Consistent environment**: Same across deployments
- **Resource isolation**: Predictable performance

**Limitations:**
- **CPU constraints**: Limited by container allocation
- **Memory limits**: Container memory restrictions
- **No GPU acceleration**: Unless explicitly configured

#### **Render (Production)**
**Advantages:**
- **Scalable resources**: Can upgrade as needed
- **Dedicated environment**: No local resource contention

**Limitations:**
- **Free tier constraints**: Limited CPU/memory
- **Network latency**: For video uploads/downloads

## Testing Strategy

### 1. **Performance Testing Script**

We've created `backend/scripts/performance_test.py` to test:

- **Frame extraction speed** (FFmpeg/OpenCV)
- **YOLO processing speed** (ball detection)
- **MediaPipe processing speed** (pose detection)
- **Memory usage** during processing
- **System resource utilization**

### 2. **Test Configurations**

The script tests these configurations:

```python
test_configs = [
    ((1920, 1080), 30, 10, "1080p_30fps_10s"),
    ((1920, 1080), 60, 10, "1080p_60fps_10s"),
    ((3840, 2160), 30, 5, "4K_30fps_5s"),
    ((3840, 2160), 60, 5, "4K_60fps_5s"),
    ((1280, 720), 30, 15, "720p_30fps_15s"),
]
```

### 3. **Running the Tests**

#### **Local Environment**
```bash
cd backend
python scripts/run_performance_test.py
```

#### **Docker Environment**
```bash
# Build and run in Docker
docker build -t tennis-backend .
docker run --rm tennis-backend python scripts/run_performance_test.py
```

#### **Production Environment**
```bash
# Run on Render or similar
python scripts/run_performance_test.py
```

## Expected Results by Environment

### **M1 MacBook Pro (Local)**
**Expected Performance:**
- **1080p 30fps**: 15-25 fps processing
- **1080p 60fps**: 8-15 fps processing
- **4K 30fps**: 3-8 fps processing
- **4K 60fps**: 1-4 fps processing

**Recommended Limits:**
- **Max Resolution**: 1080p (4K possible but slow)
- **Max FPS**: 30fps
- **Max Duration**: 5 minutes
- **Frame Skip**: 2 (process every 2nd frame)

### **Docker Container**
**Expected Performance:**
- **1080p 30fps**: 10-20 fps processing
- **1080p 60fps**: 5-12 fps processing
- **4K 30fps**: 2-6 fps processing
- **4K 60fps**: 1-3 fps processing

**Recommended Limits:**
- **Max Resolution**: 1080p
- **Max FPS**: 30fps
- **Max Duration**: 3 minutes
- **Frame Skip**: 3 (process every 3rd frame)

### **Render Free Tier**
**Expected Performance:**
- **1080p 30fps**: 5-15 fps processing
- **1080p 60fps**: 3-8 fps processing
- **4K**: Not recommended

**Recommended Limits:**
- **Max Resolution**: 720p
- **Max FPS**: 30fps
- **Max Duration**: 2 minutes
- **Frame Skip**: 4 (process every 4th frame)

## Implementation Strategy

### 1. **Dynamic Configuration**

Based on test results, implement dynamic configuration:

```python
# In config.py
class Settings(BaseSettings):
    # Dynamic limits based on environment
    MAX_VIDEO_RESOLUTION: tuple[int, int] = (1920, 1080)  # Default 1080p
    MAX_FPS: int = 30  # Default 30fps
    MAX_VIDEO_DURATION: int = 300  # 5 minutes
    FRAME_SKIP_RATIO: int = 2  # Process every nth frame
    
    # Environment detection
    ENVIRONMENT: str = "local"  # local, docker, production
```

### 2. **Environment Detection**

```python
def detect_environment() -> str:
    """Detect current environment."""
    if os.path.exists("/.dockerenv"):
        return "docker"
    elif os.getenv("RENDER"):
        return "production"
    else:
        return "local"
```

### 3. **Validation Implementation**

```python
def validate_video_file(filename: str, file_size: int, metadata: VideoMetadata) -> None:
    """Enhanced video validation with resolution and FPS limits."""
    
    # Existing validations...
    
    # Resolution validation
    if metadata.width and metadata.height:
        if metadata.width > settings.MAX_VIDEO_RESOLUTION[0] or \
           metadata.height > settings.MAX_VIDEO_RESOLUTION[1]:
            raise handle_file_error(
                "resolution_too_high",
                filename,
                f"Maximum resolution is {settings.MAX_VIDEO_RESOLUTION[0]}x{settings.MAX_VIDEO_RESOLUTION[1]}"
            )
    
    # FPS validation
    if metadata.fps and metadata.fps > settings.MAX_FPS:
        raise handle_file_error(
            "fps_too_high",
            filename,
            f"Maximum frame rate is {settings.MAX_FPS}fps"
        )
    
    # Duration validation
    if metadata.duration and metadata.duration > settings.MAX_VIDEO_DURATION:
        raise handle_file_error(
            "duration_too_long",
            filename,
            f"Maximum duration is {settings.MAX_VIDEO_DURATION} seconds"
        )
```

## Optimization Strategies

### 1. **Immediate Optimizations**

- **Frame skipping**: Process every nth frame
- **Resolution limits**: Prevent 4K uploads
- **FPS limits**: Cap at 30fps
- **Duration limits**: Prevent very long videos

### 2. **Advanced Optimizations**

- **Video downscaling**: Automatically convert 4K to 1080p
- **Dynamic frame skip**: Adjust based on resolution
- **Background processing**: Use Celery for long videos
- **Caching**: Cache processed results

### 3. **Model Optimizations**

- **YOLO model size**: Use smaller models (nano vs small)
- **Batch processing**: Process multiple frames together
- **GPU acceleration**: Enable CUDA/MPS when available

## Monitoring and Metrics

### 1. **Key Metrics to Track**

- **Processing time per frame**
- **Memory usage during processing**
- **CPU utilization**
- **Success/failure rates**
- **User upload patterns**

### 2. **Alerting**

- **Processing time > 5 minutes**
- **Memory usage > 80%**
- **Failure rate > 10%**
- **Queue length > 10 videos**

## Next Steps

1. **Run performance tests** on your local environment
2. **Analyze results** and adjust limits accordingly
3. **Implement validation** in the upload endpoint
4. **Test with real videos** to validate limits
5. **Deploy and monitor** in production

## Conclusion

The key insight is that **4K resolution is the primary bottleneck**, not file size or duration. Your M1 MacBook Pro can likely handle 4K processing, but it will be slow. The optimal approach is to:

1. **Test your specific hardware** with the performance script
2. **Set reasonable defaults** based on test results
3. **Implement validation** to prevent problematic uploads
4. **Consider downscaling** for high-resolution videos

This approach ensures good user experience while preventing system crashes.
