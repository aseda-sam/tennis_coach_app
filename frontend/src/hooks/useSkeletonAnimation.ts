import { useCallback, useEffect, useRef } from 'react';
import { MetricValue } from '../types/biomechanics';
import { OverlayData } from '../types/video';
import {
  BALL_TRAIL_LENGTH,
  NormalizationRef,
  SKELETON_COLOR,
  computeNormalizationRef,
  drawGrid,
  drawGroundPlane,
  drawGroundPlaneFixed,
  drawHead,
  drawJoints,
  drawStickBallTrail,
  drawStickHud,
  drawStickSkeleton,
  drawTossHeightAnnotation,
  normalizePose,
  normalizePoseFixed,
} from '../utils/canvasDrawing';

interface UseSkeletonAnimationParams {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  containerRef: React.RefObject<HTMLDivElement | null>;
  overlayData: OverlayData | undefined;
  currentTime: number;
  isPlaying: boolean;
  phaseColor?: string;
  phaseLabel?: string;
  annotations?: MetricValue[];
  serveStartTime?: number;
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
  annotations,
  serveStartTime,
}: UseSkeletonAnimationParams): void {
  const animationFrameRef = useRef<number | null>(null);
  const lastRenderedTimeRef = useRef<number>(-1);
  const ballTrailRef = useRef<{ x: number; y: number }[]>([]);
  const framesSinceBallRef = useRef<number>(0);
  const normRefRef = useRef<NormalizationRef | null>(null);
  const normRefServeStartRef = useRef<number | undefined>(undefined);

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

    // Compute or reuse fixed normalization reference
    if (
      normRefServeStartRef.current !== serveStartTime ||
      normRefRef.current === null
    ) {
      normRefRef.current = computeNormalizationRef(
        overlayData.frames,
        serveStartTime,
        overlayData.fps
      );
      normRefServeStartRef.current = serveStartTime;
    }
    const ref = normRefRef.current;

    // Normalize pose — fixed when ref available, per-frame fallback otherwise
    const normalizedPose = ref
      ? normalizePoseFixed(
          frame.keypoints,
          containerWidth,
          containerHeight,
          ref
        )
      : normalizePose(frame.keypoints, containerWidth, containerHeight);
    if (!normalizedPose) return;

    // Ground plane → skeleton → joints → head
    const boneColor = phaseColor || SKELETON_COLOR;
    if (ref) {
      drawGroundPlaneFixed(ctx, containerWidth, containerHeight, ref);
    } else {
      drawGroundPlane(ctx, normalizedPose, containerWidth);
    }
    drawStickSkeleton(ctx, normalizedPose, boneColor);
    drawJoints(ctx, normalizedPose, boneColor);
    drawHead(ctx, normalizedPose, boneColor);

    // Clear ball trail on seek (time jump > 0.1s)
    const timeDelta = Math.abs(currentTime - lastRenderedTimeRef.current);
    if (lastRenderedTimeRef.current >= 0 && timeDelta > 0.1) {
      ballTrailRef.current = [];
      framesSinceBallRef.current = 0;
    }

    // Ball trail — track frames since last detection to fade when stale
    const trail = ballTrailRef.current;
    if (frame.ball_position && frame.ball_position.length >= 2) {
      const ballKps = { ...frame.keypoints, _ball: frame.ball_position };
      const ballNorm = ref
        ? normalizePoseFixed(ballKps, containerWidth, containerHeight, ref)
        : normalizePose(ballKps, containerWidth, containerHeight);
      if (ballNorm && ballNorm._ball) {
        trail.push({ x: ballNorm._ball.x, y: ballNorm._ball.y });
        if (trail.length > BALL_TRAIL_LENGTH) {
          trail.splice(0, trail.length - BALL_TRAIL_LENGTH);
        }
        framesSinceBallRef.current = 0;
      }
    } else {
      framesSinceBallRef.current++;
    }
    drawStickBallTrail(ctx, trail, framesSinceBallRef.current);

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

    // Metric annotations (toss height / laterality)
    if (annotations && annotations.length > 0) {
      for (const metric of annotations) {
        if (metric.timestamp == null || metric.value == null) continue;

        // Look up the frame at the annotation's timestamp
        const peakFrameIndex = Math.round(metric.timestamp * overlayData.fps);
        const peakFrame =
          overlayData.frames[
            Math.max(0, Math.min(peakFrameIndex, overlayData.frames.length - 1))
          ];
        if (!peakFrame?.keypoints || !peakFrame.ball_position) continue;

        // Compute shoulder midpoint for annotations
        const ls = peakFrame.keypoints['left_shoulder'];
        const rs = peakFrame.keypoints['right_shoulder'];
        if (!ls || !rs) continue;

        const shoulderMid = [(ls[0] + rs[0]) / 2, (ls[1] + rs[1]) / 2];

        // Normalize the peak frame's ball + keypoints
        const peakKps = {
          ...peakFrame.keypoints,
          _ball: peakFrame.ball_position,
          _shoulder_mid: shoulderMid,
        };
        const peakNorm = ref
          ? normalizePoseFixed(peakKps, containerWidth, containerHeight, ref)
          : normalizePose(peakKps, containerWidth, containerHeight);
        if (!peakNorm?._ball || !peakNorm?._shoulder_mid) continue;

        if (metric.metric_name === 'toss_peak_height') {
          drawTossHeightAnnotation({
            ctx,
            ballY: peakNorm._ball.y,
            shoulderY: peakNorm._shoulder_mid.y,
            canvasWidth: containerWidth,
            canvasHeight: containerHeight,
            value: metric.value,
            opacity: 1,
          });
        }
      }
    }

    lastRenderedTimeRef.current = currentTime;
  }, [
    currentTime,
    overlayData,
    phaseColor,
    phaseLabel,
    annotations,
    canvasRef,
    containerRef,
    serveStartTime,
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

  // Draw on time change when paused. Call synchronously so the canvas always
  // reflects the latest state — scheduling a RAF here would let rapid seek
  // updates cancel each other before the browser ever paints.
  // The continuous loop below handles drawing during playback.
  useEffect(() => {
    if (isPlaying) return;
    drawFrame();
  }, [currentTime, drawFrame, isPlaying]);

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
