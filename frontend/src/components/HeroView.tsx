import React, { useCallback, useEffect, useRef } from 'react';
import { MetricValue } from '../types/biomechanics';
import { ViewMode } from './AnalysisViewToggle';
import { PauseIcon, PlayIcon } from './Icons';
import StickFigureCanvas from './StickFigureCanvas';
import './HeroView.css';

interface HeroViewProps {
  videoUrl: string;
  videoId: number;
  serveStart: number;
  serveEnd: number;
  currentTime: number;
  isPlaying: boolean;
  phaseLabel?: string;
  viewMode: ViewMode;
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
  viewMode,
  onTimeUpdate,
  onPlayPause,
  onSeek,
  annotations,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const pipVideoRef = useRef<HTMLVideoElement>(null);

  const isVideoMode = viewMode === 'video-focus';
  const activeVideoRef = isVideoMode ? videoRef : pipVideoRef;

  // Sync timeupdate from whichever video element is active
  useEffect(() => {
    const video = activeVideoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      onTimeUpdate(video.currentTime);
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => video.removeEventListener('timeupdate', handleTimeUpdate);
  }, [activeVideoRef, onTimeUpdate, viewMode]);

  // Sync play/pause state
  useEffect(() => {
    const video = activeVideoRef.current;
    if (!video) return;
    if (isPlaying) {
      video.play().catch(() => {});
    } else {
      video.pause();
    }
  }, [isPlaying, activeVideoRef, viewMode]);

  // Keep video in sync with external time changes (phase jumps, loop resets)
  useEffect(() => {
    const video = activeVideoRef.current;
    if (!video) return;
    if (Math.abs(video.currentTime - currentTime) > 0.04) {
      video.currentTime = currentTime;
    }
  }, [currentTime, activeVideoRef, viewMode]);

  const handleVideoSeek = useCallback(
    (time: number) => {
      if (videoRef.current) videoRef.current.currentTime = time;
      if (pipVideoRef.current) pipVideoRef.current.currentTime = time;
      onSeek(time);
    },
    [onSeek]
  );

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    return `${m}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
  };

  return (
    <div className="hero-view">
      <div className="hero-view__display">
        {isVideoMode ? (
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
            <video
              ref={pipVideoRef}
              className="hero-view__pip-video"
              src={videoUrl}
              muted
              onClick={onPlayPause}
            />
          </div>
        )}
      </div>

      <div className="hero-view__controls">
        <button
          className="hero-view__play-btn"
          onClick={onPlayPause}
          type="button"
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? <PauseIcon size={18} /> : <PlayIcon size={18} />}
        </button>

        <span className="hero-view__timestamp">{formatTime(currentTime)}</span>

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

        <span className="hero-view__timestamp hero-view__timestamp--end">
          {formatTime(serveEnd)}
        </span>
      </div>
    </div>
  );
};

export default HeroView;
