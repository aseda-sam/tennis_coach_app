import { useQuery } from '@tanstack/react-query';
import React, { useCallback, useEffect, useRef } from 'react';
import { videoApi } from '../services/api';
import { OverlayData } from '../types/video';
import './StickFigureCanvas.css';

interface StickFigureCanvasProps {
  videoId: number;
  currentTime: number;
  fps?: number;
  isPlaying: boolean;
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

// Joint circles for key points
const JOINT_POINTS = [
  'left_shoulder',
  'right_shoulder',
  'left_elbow',
  'right_elbow',
  'left_wrist',
  'right_wrist',
  'left_hip',
  'right_hip',
  'left_knee',
  'right_knee',
  'left_ankle',
  'right_ankle',
] as const;

/**
 * Normalize pose keypoints to a consistent scale and center position.
 * Returns coordinates in a normalized space where the figure is centered
 * and scaled based on torso length.
 */
function normalizePose(
  keypoints: Record<string, number[]>,
  canvasWidth: number,
  canvasHeight: number
): Record<string, { x: number; y: number }> | null {
  // Required keypoints for normalization
  const leftHip = keypoints['left_hip'];
  const rightHip = keypoints['right_hip'];
  const leftShoulder = keypoints['left_shoulder'];
  const rightShoulder = keypoints['right_shoulder'];

  if (!leftHip || !rightHip || !leftShoulder || !rightShoulder) {
    return null;
  }

  // Calculate hip center (will be our reference point)
  const hipCenterX = (leftHip[0] + rightHip[0]) / 2;
  const hipCenterY = (leftHip[1] + rightHip[1]) / 2;

  // Calculate shoulder center
  const shoulderCenterX = (leftShoulder[0] + rightShoulder[0]) / 2;
  const shoulderCenterY = (leftShoulder[1] + rightShoulder[1]) / 2;

  // Calculate torso length (for scaling)
  const torsoLength = Math.sqrt(
    Math.pow(shoulderCenterX - hipCenterX, 2) +
      Math.pow(shoulderCenterY - hipCenterY, 2)
  );

  if (torsoLength === 0) return null;

  // Target size: figure should take up about 60% of the canvas height
  // Assuming full body is roughly 4x torso length
  const targetHeight = canvasHeight * 0.6;
  const scale = targetHeight / (torsoLength * 4);

  // Center position (slightly above center to account for legs below hips)
  const centerX = canvasWidth / 2;
  const centerY = canvasHeight * 0.4; // Place hip center at 40% from top

  // Transform all keypoints
  const normalized: Record<string, { x: number; y: number }> = {};

  for (const [name, coords] of Object.entries(keypoints)) {
    if (coords && coords.length >= 2) {
      // Translate relative to hip center, scale, then translate to canvas center
      const relX = coords[0] - hipCenterX;
      const relY = coords[1] - hipCenterY;

      normalized[name] = {
        x: centerX + relX * scale,
        y: centerY + relY * scale,
      };
    }
  }

  return normalized;
}

const StickFigureCanvas: React.FC<StickFigureCanvasProps> = ({
  videoId,
  currentTime,
  isPlaying,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animationFrameRef = useRef<number | null>(null);
  const lastRenderedTimeRef = useRef<number>(-1);

  // Fetch overlay data using React Query
  const { data: overlayData, isLoading } = useQuery<OverlayData>({
    queryKey: ['overlay-data', videoId],
    queryFn: () => videoApi.getOverlayData(videoId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const drawFrame = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || !overlayData) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Get container dimensions
    const containerWidth = container.offsetWidth;
    const containerHeight = container.offsetHeight;

    // Set canvas size to match container (with device pixel ratio for sharpness)
    const dpr = window.devicePixelRatio || 1;
    canvas.width = containerWidth * dpr;
    canvas.height = containerHeight * dpr;
    canvas.style.width = `${containerWidth}px`;
    canvas.style.height = `${containerHeight}px`;
    ctx.scale(dpr, dpr);

    // Clear canvas with dark background
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, containerWidth, containerHeight);

    // Draw subtle grid pattern
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    const gridSize = 40;
    for (let x = 0; x < containerWidth; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, containerHeight);
      ctx.stroke();
    }
    for (let y = 0; y < containerHeight; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(containerWidth, y);
      ctx.stroke();
    }

    // Get frame index from current time
    let frameIndex = Math.round(currentTime * overlayData.fps);
    if (frameIndex < 0) frameIndex = 0;
    if (frameIndex >= overlayData.frames.length) {
      frameIndex = overlayData.frames.length - 1;
    }

    const frame = overlayData.frames[frameIndex];
    if (
      !frame ||
      !frame.keypoints ||
      Object.keys(frame.keypoints).length === 0
    ) {
      // No pose data - show blank canvas (grid already drawn)
      return;
    }

    // Normalize pose to canvas coordinates
    const normalizedPose = normalizePose(
      frame.keypoints,
      containerWidth,
      containerHeight
    );
    if (!normalizedPose) {
      // Incomplete pose data - show blank canvas (grid already drawn)
      return;
    }

    // Draw skeleton connections with glow effect
    ctx.shadowColor = '#00ff88';
    ctx.shadowBlur = 8;
    ctx.strokeStyle = '#00ff88';
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';

    for (const [startKey, endKey] of SKELETON_CONNECTIONS) {
      const start = normalizedPose[startKey];
      const end = normalizedPose[endKey];

      if (start && end) {
        ctx.beginPath();
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(end.x, end.y);
        ctx.stroke();
      }
    }

    // Draw joint circles
    ctx.shadowBlur = 4;
    ctx.fillStyle = '#ffffff';

    for (const jointName of JOINT_POINTS) {
      const joint = normalizedPose[jointName];
      if (joint) {
        ctx.beginPath();
        ctx.arc(joint.x, joint.y, 5, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Reset shadow
    ctx.shadowBlur = 0;

    // Draw frame info
    ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.font = '12px monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`Frame: ${frameIndex}`, 10, containerHeight - 30);
    ctx.fillText(`Time: ${currentTime.toFixed(2)}s`, 10, containerHeight - 14);

    // Draw confidence indicator
    const confidence = frame.confidence || 0;
    ctx.textAlign = 'right';
    ctx.fillStyle =
      confidence > 0.7 ? '#00ff88' : confidence > 0.4 ? '#ffaa00' : '#ff4444';
    ctx.fillText(
      `Confidence: ${(confidence * 100).toFixed(0)}%`,
      containerWidth - 10,
      containerHeight - 14
    );

    lastRenderedTimeRef.current = currentTime;
  }, [currentTime, overlayData]);

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      animationFrameRef.current = requestAnimationFrame(drawFrame);
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [drawFrame]);

  // Draw on time change
  useEffect(() => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    animationFrameRef.current = requestAnimationFrame(drawFrame);
  }, [currentTime, drawFrame]);

  // Continuous animation loop when playing
  useEffect(() => {
    if (!isPlaying) return;

    let running = true;
    const animate = () => {
      if (!running) return;
      drawFrame();
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      running = false;
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying, drawFrame]);

  if (isLoading) {
    return (
      <div className="stick-figure-canvas-container stick-figure-loading">
        <div className="stick-figure-loading-spinner" />
        <p>Loading pose data...</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="stick-figure-canvas-container">
      <canvas ref={canvasRef} className="stick-figure-canvas" />
    </div>
  );
};

export default StickFigureCanvas;
