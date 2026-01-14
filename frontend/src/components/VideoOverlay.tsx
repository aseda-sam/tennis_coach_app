import React, { useEffect, useMemo, useRef, useState } from 'react';
import { videoApi } from '../services/api';
import { OverlayData } from '../types/video';
import './VideoOverlay.css';

interface VideoOverlayProps {
  videoId: number;
  videoElement: HTMLVideoElement | null;
  showOverlay: boolean;
  hasPoseData: boolean;
}

/**
 * Compute the rendered video content rectangle accounting for object-fit.
 * Only handles 'contain' and 'cover' modes (the ones actually used).
 */
function computeVideoContentRect(
  elementWidth: number,
  elementHeight: number,
  videoWidth: number,
  videoHeight: number,
  objectFit: 'contain' | 'cover'
): {
  contentX: number;
  contentY: number;
  contentWidth: number;
  contentHeight: number;
  scaleX: number;
  scaleY: number;
} {
  const elementAspect = elementWidth / elementHeight;
  const videoAspect = videoWidth / videoHeight;

  let contentX = 0;
  let contentY = 0;
  let contentWidth = elementWidth;
  let contentHeight = elementHeight;

  if (objectFit === 'contain') {
    // Video scaled to fit within element, maintaining aspect ratio
    if (videoAspect > elementAspect) {
      // Video is wider - letterboxing (black bars top/bottom)
      contentWidth = elementWidth;
      contentHeight = elementWidth / videoAspect;
      contentY = (elementHeight - contentHeight) / 2;
    } else {
      // Video is taller - pillarboxing (black bars left/right)
      contentHeight = elementHeight;
      contentWidth = elementHeight * videoAspect;
      contentX = (elementWidth - contentWidth) / 2;
    }
  } else {
    // objectFit === 'cover' - video covers entire element, may be cropped
    if (videoAspect > elementAspect) {
      // Video is wider - crop left/right
      contentHeight = elementHeight;
      contentWidth = elementHeight * videoAspect;
      contentX = (elementWidth - contentWidth) / 2;
    } else {
      // Video is taller - crop top/bottom
      contentWidth = elementWidth;
      contentHeight = elementWidth / videoAspect;
      contentY = (elementHeight - contentHeight) / 2;
    }
  }

  // Calculate scale from original video dimensions to rendered content dimensions
  const scaleX = contentWidth / videoWidth;
  const scaleY = contentHeight / videoHeight;

  return {
    contentX,
    contentY,
    contentWidth,
    contentHeight,
    scaleX,
    scaleY,
  };
}

/**
 * Rotate point coordinates for 90° clockwise rotation.
 * Used when overlay dimensions don't match video dimensions (phone rotation metadata issue).
 */
function rotatePoint90(
  x: number,
  y: number,
  width: number,
  height: number
): { x: number; y: number } {
  return { x: height - y, y: x };
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
  showOverlay,
  hasPoseData,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const lastRenderedFrameRef = useRef<number>(-1);
  const animationFrameRef = useRef<number | null>(null);
  const [overlayData, setOverlayData] = useState<OverlayData | null>(null);

  // Fetch overlay data when overlay is enabled
  useEffect(() => {
    if (!showOverlay || !hasPoseData || overlayData) {
      return;
    }

    const fetchOverlayData = async () => {
      try {
        const data = await videoApi.getOverlayData(videoId);
        setOverlayData(data);
      } catch (err: any) {
        console.error('Failed to fetch overlay data:', err);
      }
    };

    fetchOverlayData();
  }, [showOverlay, hasPoseData, videoId, overlayData]);

  // Detect rotation once when overlay data and video element are available
  // This handles phone videos where OpenCV dimensions don't match browser dimensions
  const needsRotation = useMemo(() => {
    if (!overlayData || !videoElement) return false;

    const videoNaturalWidth = videoElement.videoWidth;
    const videoNaturalHeight = videoElement.videoHeight;

    if (!videoNaturalWidth || !videoNaturalHeight) return false;

    // Check if dimensions match (accounting for possible 90° rotation)
    const dimensionsMatch =
      (overlayData.width === videoNaturalWidth &&
        overlayData.height === videoNaturalHeight) ||
      (overlayData.width === videoNaturalHeight &&
        overlayData.height === videoNaturalWidth);

    // If dimensions don't match, we need to rotate (90° clockwise)
    return (
      !dimensionsMatch &&
      overlayData.width === videoNaturalHeight &&
      overlayData.height === videoNaturalWidth
    );
  }, [overlayData, videoElement]);

  // Clear canvas when overlay is disabled
  useEffect(() => {
    if (!showOverlay && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (ctx && canvas.width > 0 && canvas.height > 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      lastRenderedFrameRef.current = -1;
      // Cancel any pending animation frames
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    }
  }, [showOverlay]);

  // Draw overlay on canvas
  useEffect(() => {
    if (!showOverlay || !overlayData || !videoElement || !canvasRef.current) {
      // Clear canvas if overlay is disabled
      if (!showOverlay && canvasRef.current) {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (ctx && canvas.width > 0 && canvas.height > 0) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
      }
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const drawFrame = () => {
      if (!videoElement || !overlayData) return;

      const elementWidth = videoElement.offsetWidth;
      const elementHeight = videoElement.offsetHeight;
      const videoNaturalWidth = videoElement.videoWidth;
      const videoNaturalHeight = videoElement.videoHeight;

      if (
        !videoNaturalWidth ||
        !videoNaturalHeight ||
        !elementWidth ||
        !elementHeight
      )
        return;

      // Get object-fit mode from computed styles (default to 'contain')
      const computedStyle = window.getComputedStyle(videoElement);
      const objectFit = (
        computedStyle.objectFit === 'cover' ? 'cover' : 'contain'
      ) as 'contain' | 'cover';

      // Compute the rendered video content rectangle accounting for object-fit
      const contentRect = computeVideoContentRect(
        elementWidth,
        elementHeight,
        videoNaturalWidth,
        videoNaturalHeight,
        objectFit
      );

      // Set canvas size to match video element's displayed size
      canvas.width = elementWidth;
      canvas.height = elementHeight;

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Get current video time and find matching frame
      const currentTime = videoElement.currentTime;
      let frameIndex = Math.round(currentTime * overlayData.fps);
      if (frameIndex < 0) frameIndex = 0;
      if (frameIndex >= overlayData.frames.length) {
        frameIndex = overlayData.frames.length - 1;
      }

      // Skip redraw if frame hasn't changed (performance optimization)
      if (frameIndex === lastRenderedFrameRef.current) {
        return;
      }

      lastRenderedFrameRef.current = frameIndex;

      const frame = overlayData.frames[frameIndex];
      if (
        !frame ||
        !frame.keypoints ||
        Object.keys(frame.keypoints).length === 0
      ) {
        return; // No pose data for this frame
      }

      // Determine effective overlay dimensions (accounting for rotation)
      const overlayWidth = needsRotation
        ? overlayData.height
        : overlayData.width;
      const overlayHeight = needsRotation
        ? overlayData.width
        : overlayData.height;

      // Scale from overlay coordinate space to rendered content rect
      const scaleX = contentRect.contentWidth / overlayWidth;
      const scaleY = contentRect.contentHeight / overlayHeight;

      // Draw skeleton connections
      ctx.strokeStyle = '#00FF00'; // Neon green
      ctx.lineWidth = 2;
      ctx.shadowColor = '#000000'; // Black outline
      ctx.shadowBlur = 2;

      for (const [startKey, endKey] of SKELETON_CONNECTIONS) {
        const startPoint = frame.keypoints[startKey];
        const endPoint = frame.keypoints[endKey];

        if (
          startPoint &&
          endPoint &&
          startPoint.length >= 2 &&
          endPoint.length >= 2
        ) {
          // Apply rotation if needed
          let p1 = { x: startPoint[0], y: startPoint[1] };
          let p2 = { x: endPoint[0], y: endPoint[1] };

          if (needsRotation) {
            p1 = rotatePoint90(
              p1.x,
              p1.y,
              overlayData.width,
              overlayData.height
            );
            p2 = rotatePoint90(
              p2.x,
              p2.y,
              overlayData.width,
              overlayData.height
            );
          }

          // Scale + offset into rendered content rect
          const x1 = p1.x * scaleX + contentRect.contentX;
          const y1 = p1.y * scaleY + contentRect.contentY;
          const x2 = p2.x * scaleX + contentRect.contentX;
          const y2 = p2.y * scaleY + contentRect.contentY;

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

      // Reset line dash
      ctx.setLineDash([]);
    };

    // Use requestAnimationFrame for smooth rendering while playing
    const handleTimeUpdate = () => {
      if (animationFrameRef.current === null) {
        animationFrameRef.current = requestAnimationFrame(() => {
          drawFrame();
          animationFrameRef.current = null;
        });
      }
    };

    // Update on resize or seek (immediate draw)
    const handleResize = () => {
      lastRenderedFrameRef.current = -1; // Force redraw
      drawFrame();
    };

    const handleSeeked = () => {
      lastRenderedFrameRef.current = -1; // Force redraw on seek
      drawFrame();
    };

    videoElement.addEventListener('timeupdate', handleTimeUpdate);
    videoElement.addEventListener('seeked', handleSeeked);
    window.addEventListener('resize', handleResize);
    drawFrame(); // Initial draw

    return () => {
      videoElement.removeEventListener('timeupdate', handleTimeUpdate);
      videoElement.removeEventListener('seeked', handleSeeked);
      window.removeEventListener('resize', handleResize);
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      lastRenderedFrameRef.current = -1;
    };
  }, [showOverlay, overlayData, videoElement, needsRotation]);

  if (!showOverlay) {
    return null;
  }

  return <canvas ref={canvasRef} className="video-overlay-canvas" />;
};

export default VideoOverlay;
