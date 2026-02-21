import { useCallback, useEffect, useRef } from 'react';
import { OverlayData } from '../types/video';
import {
  BALL_TRAIL_LENGTH,
  STICK_FIGURE_SKELETON_COLOR,
  drawGrid,
  drawJoints,
  drawStickBallTrail,
  drawStickHud,
  drawStickSkeleton,
  normalizePose,
} from '../utils/canvasDrawing';

interface UseSkeletonAnimationParams {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  containerRef: React.RefObject<HTMLDivElement | null>;
  overlayData: OverlayData | undefined;
  currentTime: number;
  isPlaying: boolean;
  phaseColor?: string;
  phaseLabel?: string;
}

/**
 * Manages the stick-figure rendering loop: draws the normalized skeleton,
 * ball trail, HUD, and handles resize / playback animation scheduling.
 */
export function useSkeletonAnimation({
  canvasRef,
  containerRef,
  overlayData,
  currentTime,
  isPlaying,
  phaseColor,
  phaseLabel,
}: UseSkeletonAnimationParams): void {
  const animationFrameRef = useRef<number | null>(null);
  const lastRenderedTimeRef = useRef<number>(-1);
  const ballTrailRef = useRef<{ x: number; y: number }[]>([]);

  const drawFrame = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container || !overlayData) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const containerWidth = container.offsetWidth;
    const containerHeight = container.offsetHeight;

    // Set canvas size with device pixel ratio for sharpness
    const dpr = window.devicePixelRatio || 1;
    canvas.width = containerWidth * dpr;
    canvas.height = containerHeight * dpr;
    canvas.style.width = `${containerWidth}px`;
    canvas.style.height = `${containerHeight}px`;
    ctx.scale(dpr, dpr);

    // Background + grid
    drawGrid(ctx, containerWidth, containerHeight);

    // Get frame
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
      return;
    }

    // Normalize pose
    const normalizedPose = normalizePose(
      frame.keypoints,
      containerWidth,
      containerHeight
    );
    if (!normalizedPose) return;

    // Skeleton + joints
    const baseColor = phaseColor || STICK_FIGURE_SKELETON_COLOR;
    drawStickSkeleton(ctx, normalizedPose, baseColor);
    drawJoints(ctx, normalizedPose);

    // Clear ball trail on seek (time jump > 0.1s)
    const timeDelta = Math.abs(currentTime - lastRenderedTimeRef.current);
    if (lastRenderedTimeRef.current >= 0 && timeDelta > 0.1) {
      ballTrailRef.current = [];
    }

    // Ball trail
    const trail = ballTrailRef.current;
    if (frame.ball_position && frame.ball_position.length >= 2) {
      const ballNorm = normalizePose(
        { _ball: frame.ball_position },
        containerWidth,
        containerHeight
      );
      if (ballNorm && ballNorm._ball) {
        trail.push({ x: ballNorm._ball.x, y: ballNorm._ball.y });
        if (trail.length > BALL_TRAIL_LENGTH) {
          trail.splice(0, trail.length - BALL_TRAIL_LENGTH);
        }
      }
    }
    drawStickBallTrail(ctx, trail);

    // HUD
    drawStickHud({
      ctx,
      containerWidth,
      containerHeight,
      frameIndex,
      currentTime,
      confidence: frame.confidence || 0,
      phaseLabel,
      phaseColor,
    });

    lastRenderedTimeRef.current = currentTime;
  }, [
    currentTime,
    overlayData,
    phaseColor,
    phaseLabel,
    canvasRef,
    containerRef,
  ]);

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

  // Clear ball trail when playback stops
  useEffect(() => {
    if (!isPlaying) {
      ballTrailRef.current = [];
    }
  }, [isPlaying]);

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
}
