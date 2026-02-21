import { useQuery } from '@tanstack/react-query';
import React, { useRef } from 'react';
import { useCanvasOverlay } from '../hooks/useCanvasOverlay';
import { videoApi } from '../services/api';
import { OverlayData } from '../types/video';
import './VideoOverlay.css';

interface VideoOverlayProps {
  videoId: number;
  videoElement: HTMLVideoElement | null;
  showOverlay: boolean;
  hasPoseData: boolean;
  currentTime?: number; // Current video time to trigger updates on keyboard navigation
  zoomLevel?: number; // Current zoom level for transform sync
}

const VideoOverlay: React.FC<VideoOverlayProps> = ({
  videoId,
  videoElement,
  showOverlay,
  hasPoseData,
  currentTime,
  zoomLevel = 1,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Fetch overlay data using React Query
  const { data: overlayData } = useQuery<OverlayData>({
    queryKey: ['overlay-data', videoId],
    queryFn: () => videoApi.getOverlayData(videoId),
    enabled: showOverlay && hasPoseData,
    staleTime: 5 * 60 * 1000, // 5 minutes - overlay data doesn't change often
  });

  // All rendering logic lives in the hook
  useCanvasOverlay({
    canvasRef,
    videoElement,
    overlayData,
    showOverlay,
    currentTime,
  });

  if (!showOverlay) {
    return null;
  }

  return (
    <canvas
      ref={canvasRef}
      className="video-overlay-canvas"
      style={{
        transform: zoomLevel !== 1 ? `scale(${zoomLevel})` : 'none',
        transformOrigin: 'center center',
        transition: 'transform 0.2s ease-out',
      }}
    />
  );
};

export default VideoOverlay;
