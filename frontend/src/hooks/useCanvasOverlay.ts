import { useEffect, useMemo, useRef } from 'react';
import { OverlayData } from '../types/video';
import {
  computeVideoContentRect,
  drawOverlayBallTrail,
  drawOverlaySkeleton,
} from '../utils/canvasDrawing';

interface UseCanvasOverlayParams {
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  videoElement: HTMLVideoElement | null;
  overlayData: OverlayData | undefined;
  showOverlay: boolean;
  currentTime: number | undefined;
}

/**
 * Manages the video-overlay rendering loop: event listeners, frame drawing,
 * animation-frame scheduling, and cleanup.
 */
export function useCanvasOverlay({
  canvasRef,
  videoElement,
  overlayData,
  showOverlay,
  currentTime,
}: UseCanvasOverlayParams): void {
  const lastRenderedFrameRef = useRef<number>(-1);
  const lastRenderedTimeRef = useRef<number>(-1);
  const animationFrameRef = useRef<number | null>(null);
  const currentTimeRef = useRef<number | undefined>(currentTime);
  const ballTrailRef = useRef<{ x: number; y: number }[]>([]);

  // Detect rotation once when overlay data and video element are available
  const needsRotation = useMemo(() => {
    if (!overlayData || !videoElement) return false;

    const videoNaturalWidth = videoElement.videoWidth;
    const videoNaturalHeight = videoElement.videoHeight;

    if (
      !videoNaturalWidth ||
      !videoNaturalHeight ||
      videoNaturalWidth <= 0 ||
      videoNaturalHeight <= 0 ||
      !Number.isFinite(videoNaturalWidth) ||
      !Number.isFinite(videoNaturalHeight)
    ) {
      return false;
    }

    return (
      overlayData.width === videoNaturalHeight &&
      overlayData.height === videoNaturalWidth
    );
  }, [overlayData, videoElement]);

  // Store drawFrame in a ref so it can be called from multiple effects
  const drawFrameRef = useRef<(() => void) | null>(null);

  // Clear canvas when overlay is disabled
  useEffect(() => {
    if (!showOverlay && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (ctx && canvas.width > 0 && canvas.height > 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      lastRenderedFrameRef.current = -1;
      lastRenderedTimeRef.current = -1;
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    }
  }, [showOverlay, canvasRef]);

  // Main draw effect
  useEffect(() => {
    if (!showOverlay || !overlayData || !videoElement || !canvasRef.current) {
      if (!showOverlay && canvasRef.current) {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (ctx && canvas.width > 0 && canvas.height > 0) {
          ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
      }
      drawFrameRef.current = null;
      return;
    }

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      drawFrameRef.current = null;
      return;
    }

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
        !elementHeight ||
        videoNaturalWidth <= 0 ||
        videoNaturalHeight <= 0 ||
        elementWidth <= 0 ||
        elementHeight <= 0 ||
        !Number.isFinite(videoNaturalWidth) ||
        !Number.isFinite(videoNaturalHeight) ||
        !Number.isFinite(elementWidth) ||
        !Number.isFinite(elementHeight)
      ) {
        return;
      }

      const computedStyle = window.getComputedStyle(videoElement);
      const objectFit = (
        computedStyle.objectFit === 'cover' ? 'cover' : 'contain'
      ) as 'contain' | 'cover';

      const contentRect = computeVideoContentRect(
        elementWidth,
        elementHeight,
        videoNaturalWidth,
        videoNaturalHeight,
        objectFit
      );

      canvas.width = elementWidth;
      canvas.height = elementHeight;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const videoTime =
        currentTimeRef.current !== undefined
          ? currentTimeRef.current
          : videoElement.currentTime;

      const timeTolerance = 0.01;
      if (Math.abs(videoTime - lastRenderedTimeRef.current) < timeTolerance) {
        return;
      }

      let frameIndex = Math.round(videoTime * overlayData.fps);
      if (frameIndex < 0) frameIndex = 0;
      if (frameIndex >= overlayData.frames.length) {
        frameIndex = overlayData.frames.length - 1;
      }

      lastRenderedTimeRef.current = videoTime;
      lastRenderedFrameRef.current = frameIndex;

      const frame = overlayData.frames[frameIndex];
      if (
        !frame ||
        !frame.keypoints ||
        Object.keys(frame.keypoints).length === 0
      ) {
        return;
      }

      const overlayWidth = needsRotation
        ? overlayData.height
        : overlayData.width;
      const overlayHeight = needsRotation
        ? overlayData.width
        : overlayData.height;

      const scaleX = contentRect.contentWidth / overlayWidth;
      const scaleY = contentRect.contentHeight / overlayHeight;

      // Draw skeleton
      drawOverlaySkeleton({
        ctx,
        keypoints: frame.keypoints,
        confidence: frame.confidence,
        scaleX,
        scaleY,
        contentX: contentRect.contentX,
        contentY: contentRect.contentY,
        needsRotation,
        overlayWidth: overlayData.width,
        overlayHeight: overlayData.height,
      });

      // Draw ball trail
      drawOverlayBallTrail({
        ctx,
        ballPosition: frame.ball_position,
        trail: ballTrailRef.current,
        scaleX,
        scaleY,
        contentX: contentRect.contentX,
        contentY: contentRect.contentY,
        contentWidth: contentRect.contentWidth,
        contentHeight: contentRect.contentHeight,
        needsRotation,
        overlayWidth: overlayData.width,
        overlayHeight: overlayData.height,
      });

      // Reset line dash
      ctx.setLineDash([]);
    };

    drawFrameRef.current = drawFrame;

    const handleTimeUpdate = () => {
      if (animationFrameRef.current === null) {
        animationFrameRef.current = requestAnimationFrame(() => {
          drawFrame();
          animationFrameRef.current = null;
        });
      }
    };

    const handleResize = () => {
      lastRenderedFrameRef.current = -1;
      drawFrame();
    };

    const handleSeeked = () => {
      lastRenderedFrameRef.current = -1;
      lastRenderedTimeRef.current = -1;
      ballTrailRef.current = [];
      requestAnimationFrame(() => {
        drawFrame();
      });
    };

    videoElement.addEventListener('timeupdate', handleTimeUpdate);
    videoElement.addEventListener('seeked', handleSeeked);
    window.addEventListener('resize', handleResize);
    drawFrame();

    return () => {
      videoElement.removeEventListener('timeupdate', handleTimeUpdate);
      videoElement.removeEventListener('seeked', handleSeeked);
      window.removeEventListener('resize', handleResize);
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      lastRenderedFrameRef.current = -1;
      lastRenderedTimeRef.current = -1;
      drawFrameRef.current = null;
    };
  }, [showOverlay, overlayData, videoElement, needsRotation, canvasRef]);

  // Keep currentTime ref in sync
  useEffect(() => {
    currentTimeRef.current = currentTime;
  }, [currentTime]);

  // Redraw on currentTime prop change (keyboard navigation, seeking)
  useEffect(() => {
    if (!showOverlay || !overlayData || !videoElement || !canvasRef.current) {
      return;
    }

    if (currentTime !== undefined && drawFrameRef.current) {
      lastRenderedFrameRef.current = -1;
      lastRenderedTimeRef.current = -1;

      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }

      animationFrameRef.current = requestAnimationFrame(() => {
        if (drawFrameRef.current) {
          drawFrameRef.current();
        }
        animationFrameRef.current = null;
      });
    }
  }, [currentTime, showOverlay, overlayData, videoElement, canvasRef]);
}
