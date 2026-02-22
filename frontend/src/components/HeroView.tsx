import React, { useCallback, useEffect, useRef, useState } from 'react';
import { MetricValue } from '../types/biomechanics';
import StickFigureCanvas from './StickFigureCanvas';
import './HeroView.css';

type ViewMode = 'video' | 'analysis';

interface HeroViewProps {
  videoUrl: string;
  videoId: number;
  serveStart: number;
  serveEnd: number;
  currentTime: number;
  isPlaying: boolean;
  phaseLabel?: string;
  onTimeUpdate: (time: number) => void;
  onPlayPause: () => void;
  onSeek: (time: number) => void;
  annotations?: MetricValue[];
}

const HeroView: React.FC<HeroViewProps> = ({
  videoUrl,
  videoId,
  serveStart,
  serveEnd,
  currentTime,
  isPlaying,
  phaseLabel,
  onTimeUpdate,
  onPlayPause,
  onSeek,
  annotations,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>('analysis');
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (viewMode !== 'video' || !videoRef.current) return;
    const video = videoRef.current;

    const handleTimeUpdate = () => {
      onTimeUpdate(video.currentTime);
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => video.removeEventListener('timeupdate', handleTimeUpdate);
  }, [viewMode, onTimeUpdate]);

  useEffect(() => {
    if (viewMode !== 'video' || !videoRef.current) return;
    if (isPlaying) {
      videoRef.current.play().catch(() => {});
    } else {
      videoRef.current.pause();
    }
  }, [isPlaying, viewMode]);

  useEffect(() => {
    if (viewMode !== 'video' || !videoRef.current) return;
    // Keep native video playback in sync with phase seeks/loop jumps.
    if (Math.abs(videoRef.current.currentTime - currentTime) > 0.04) {
      videoRef.current.currentTime = currentTime;
    }
  }, [currentTime, viewMode]);

  const handleVideoSeek = useCallback(
    (time: number) => {
      if (videoRef.current) {
        videoRef.current.currentTime = time;
      }
      onSeek(time);
    },
    [onSeek]
  );

  const toggleView = useCallback(() => {
    setViewMode((prev) => (prev === 'video' ? 'analysis' : 'video'));
  }, []);

  return (
    <div className="hero-view">
      <div className="hero-view__display">
        {viewMode === 'video' ? (
          <video
            ref={videoRef}
            className="hero-view__video"
            src={videoUrl}
            onClick={onPlayPause}
          />
        ) : (
          <div className="hero-view__canvas-wrapper">
            <StickFigureCanvas
              videoId={videoId}
              currentTime={currentTime}
              isPlaying={isPlaying}
              phaseColor="#00ff88"
              phaseLabel={phaseLabel}
              annotations={annotations}
            />
          </div>
        )}
      </div>

      <div className="hero-view__controls">
        <button
          className="hero-view__play-btn"
          onClick={onPlayPause}
          type="button"
        >
          {isPlaying ? 'Pause' : 'Play'}
        </button>

        <input
          type="range"
          className="hero-view__scrubber"
          min={serveStart}
          max={serveEnd}
          step={0.001}
          value={currentTime}
          onChange={(e) => handleVideoSeek(parseFloat(e.target.value))}
          aria-label="Serve timeline"
        />

        <button
          className="hero-view__toggle-btn"
          onClick={toggleView}
          type="button"
        >
          {viewMode === 'video' ? 'Show Analysis' : 'Show Video'}
        </button>
      </div>
    </div>
  );
};

export default HeroView;
