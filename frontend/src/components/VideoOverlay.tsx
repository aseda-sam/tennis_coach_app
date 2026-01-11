import React, { useEffect, useRef, useState } from 'react';
import { videoApi } from '../services/api';
import './VideoOverlay.css';

interface PoseFrame {
  frame_index: number;
  timestamp: number;
  keypoints: { [key: string]: number[] }; // {"left_shoulder": [x, y], ...}
  confidence: number;
}

interface OverlayData {
  video_id: number;
  fps: number;
  total_frames: number;
  width: number;
  height: number;
  frames: PoseFrame[];
}

interface VideoOverlayProps {
  videoId: number;
  videoElement: HTMLVideoElement | null;
  videoWidth: number;
  videoHeight: number;
  showOverlay: boolean;
  hasPoseData: boolean;
}

// Skeleton connections for full body
const SKELETON_CONNECTIONS = [
  // Arms
  ['left_shoulder', 'left_elbow'],
  ['left_elbow', 'left_wrist'],
  ['right_shoulder', 'right_elbow'],
  ['right_elbow', 'right_wrist'],
  // Legs
  ['left_hip', 'left_knee'],
  ['left_knee', 'left_ankle'],
  ['right_hip', 'right_knee'],
  ['right_knee', 'right_ankle'],
  // Torso frame
  ['left_shoulder', 'right_shoulder'],
  ['left_hip', 'right_hip'],
  ['left_shoulder', 'left_hip'],
  ['right_shoulder', 'right_hip'],
] as const;

const VideoOverlay: React.FC<VideoOverlayProps> = ({
  videoId,
  videoElement,
  videoWidth,
  videoHeight,
  showOverlay,
  hasPoseData,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [overlayData, setOverlayData] = useState<OverlayData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [canvasStyle, setCanvasStyle] = useState<React.CSSProperties>({
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
  });

  // Fetch overlay data when overlay is enabled
  useEffect(() => {
    if (!showOverlay || !hasPoseData || overlayData) {
      return;
    }

    const fetchOverlayData = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await videoApi.getOverlayData(videoId);
        setOverlayData(data);
      } catch (err: any) {
        console.error('Failed to fetch overlay data:', err);
        setError('Failed to load overlay data');
      } finally {
        setLoading(false);
      }
    };

    fetchOverlayData();
  }, [showOverlay, hasPoseData, videoId, overlayData]);

  // Draw overlay on canvas
  useEffect(() => {
    if (!showOverlay || !overlayData || !videoElement || !canvasRef.current) {
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const drawFrame = () => {
      if (!videoElement || !overlayData) return;

      // Get video element's displayed dimensions
      // Use offsetWidth/Height to get the actual rendered size (accounts for CSS object-fit)
      const displayedVideoWidth = videoElement.offsetWidth;
      const displayedVideoHeight = videoElement.offsetHeight;
      const videoNaturalWidth = videoElement.videoWidth;
      const videoNaturalHeight = videoElement.videoHeight;
      
      if (!videoNaturalWidth || !videoNaturalHeight || !displayedVideoWidth || !displayedVideoHeight) return;

      // Set canvas size to match video element's displayed size exactly
      canvas.width = displayedVideoWidth;
      canvas.height = displayedVideoHeight;

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Get current video time
      const currentTime = videoElement.currentTime;

      // Find matching frame (exact match or nearest)
      let frameIndex = Math.round(currentTime * overlayData.fps);
      if (frameIndex < 0) frameIndex = 0;
      if (frameIndex >= overlayData.frames.length) {
        frameIndex = overlayData.frames.length - 1;
      }

      const frame = overlayData.frames[frameIndex];
      if (!frame || !frame.keypoints || Object.keys(frame.keypoints).length === 0) {
        return; // No pose data for this frame
      }

      // Calculate scale from original video dimensions to displayed video dimensions
      // The canvas now matches the video element exactly, so we scale directly
      const scaleX = displayedVideoWidth / overlayData.width;
      const scaleY = displayedVideoHeight / overlayData.height;

      // Color scheme: neon green with black outline
      const keypointColor = '#00FF00'; // Neon green
      const connectionColor = '#00FF00'; // Neon green
      const outlineColor = '#000000'; // Black

      // Draw connections first (so keypoints appear on top)
      ctx.strokeStyle = connectionColor;
      ctx.lineWidth = 2;
      ctx.shadowColor = outlineColor;
      ctx.shadowBlur = 2;

      for (const [startKey, endKey] of SKELETON_CONNECTIONS) {
        const startPoint = frame.keypoints[startKey];
        const endPoint = frame.keypoints[endKey];

        if (startPoint && endPoint && startPoint.length >= 2 && endPoint.length >= 2) {
          // Scale coordinates from original video dimensions to displayed dimensions
          const x1 = startPoint[0] * scaleX;
          const y1 = startPoint[1] * scaleY;
          const x2 = endPoint[0] * scaleX;
          const y2 = endPoint[1] * scaleY;

          // Use dashed line for low confidence
          if (frame.confidence < 0.5) {
            ctx.setLineDash([5, 5]);
          } else {
            ctx.setLineDash([]);
          }

          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
        }
      }

      // Draw keypoints
      ctx.fillStyle = keypointColor;
      ctx.shadowColor = outlineColor;
      ctx.shadowBlur = 3;

      for (const [, coordinates] of Object.entries(frame.keypoints)) {
        if (coordinates && coordinates.length >= 2) {
          // Scale coordinates from original video dimensions to displayed dimensions
          const x = coordinates[0] * scaleX;
          const y = coordinates[1] * scaleY;

          // Draw keypoint circle
          ctx.beginPath();
          ctx.arc(x, y, 5, 0, 2 * Math.PI);
          ctx.fill();
          ctx.strokeStyle = outlineColor;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      // Reset line dash
      ctx.setLineDash([]);
    };

    // Draw on timeupdate
    const handleTimeUpdate = () => {
      drawFrame();
    };

    // Also update on resize
    const handleResize = () => {
      drawFrame();
    };

    videoElement.addEventListener('timeupdate', handleTimeUpdate);
    window.addEventListener('resize', handleResize);
    drawFrame(); // Initial draw

    return () => {
      videoElement.removeEventListener('timeupdate', handleTimeUpdate);
      window.removeEventListener('resize', handleResize);
    };
  }, [showOverlay, overlayData, videoElement]);

  // Update canvas position to match video element
  useEffect(() => {
    if (!videoElement || !showOverlay) return;

    const updateCanvasPosition = () => {
      const container = videoElement.parentElement;
      if (!container) return;

      const containerRect = container.getBoundingClientRect();
      const videoRect = videoElement.getBoundingClientRect();

      // Calculate offset of video within container
      const offsetX = videoRect.left - containerRect.left;
      const offsetY = videoRect.top - containerRect.top;

      setCanvasStyle({
        position: 'absolute',
        top: `${offsetY}px`,
        left: `${offsetX}px`,
        width: `${videoRect.width}px`,
        height: `${videoRect.height}px`,
        pointerEvents: 'none',
      });
    };

    updateCanvasPosition();
    const resizeObserver = new ResizeObserver(updateCanvasPosition);
    resizeObserver.observe(videoElement);
    resizeObserver.observe(videoElement.parentElement!);

    return () => {
      resizeObserver.disconnect();
    };
  }, [videoElement, showOverlay]);

  return (
    <canvas
      ref={canvasRef}
      className="video-overlay-canvas"
      style={canvasStyle}
    />
  );
};

export default VideoOverlay;
