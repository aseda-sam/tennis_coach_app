import { useQuery } from '@tanstack/react-query';
import React, { useRef } from 'react';
import { useSkeletonAnimation } from '../hooks/useSkeletonAnimation';
import { videoApi } from '../services/api';
import { OverlayData } from '../types/video';
import LoadingIndicator from './LoadingIndicator';
import './StickFigureCanvas.css';

interface StickFigureCanvasProps {
  videoId: number;
  currentTime: number;
  fps?: number;
  isPlaying: boolean;
  /** Override skeleton color (hex). Used for phase-based color-coding. */
  phaseColor?: string;
  /** Phase label to display in top-left corner. */
  phaseLabel?: string;
}

const StickFigureCanvas: React.FC<StickFigureCanvasProps> = ({
  videoId,
  currentTime,
  isPlaying,
  phaseColor,
  phaseLabel,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch overlay data using React Query
  const { data: overlayData, isLoading } = useQuery<OverlayData>({
    queryKey: ['overlay-data', videoId],
    queryFn: () => videoApi.getOverlayData(videoId),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // All rendering logic lives in the hook
  useSkeletonAnimation({
    canvasRef,
    containerRef,
    overlayData,
    currentTime,
    isPlaying,
    phaseColor,
    phaseLabel,
  });

  if (isLoading) {
    return (
      <div className="stick-figure-canvas-container stick-figure-loading">
        <LoadingIndicator
          size="md"
          tone="light"
          label="Loading pose overlay..."
        />
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
