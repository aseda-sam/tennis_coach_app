import React, { useCallback, useEffect, useMemo, useRef } from 'react';
import { MetricValue } from '../types/biomechanics';
import { ViewMode } from './AnalysisViewToggle';
import { ChevronsRight, Keyboard, Pause, Pencil, Play } from 'lucide-react';
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
  playbackSpeed?: number;
  onPlaybackSpeedChange?: (speed: number) => void;
  speedOptions?: readonly number[];
  loopActive?: boolean;
  loopDisabled?: boolean;
  loopPhaseLabel?: string;
  onLoopToggle?: () => void;
  autoAdvanceActive?: boolean;
  autoAdvanceDisabled?: boolean;
  onAutoAdvanceToggle?: () => void;
  contactTimestamp?: number | null;
  onSetContact?: (timestamp: number) => Promise<void>;
  pendingContactTime?: number | null;
  onArmContact?: (time: number) => void;
  onConfirmContact?: () => void;
  onCancelContact?: () => void;
  onOpenShortcuts?: () => void;
  onEditWindow?: () => void;
  onWheelScrub?: (deltaY: number) => void;
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
  playbackSpeed = 1,
  onPlaybackSpeedChange,
  speedOptions,
  loopActive = false,
  loopDisabled = true,
  loopPhaseLabel,
  onLoopToggle,
  autoAdvanceActive = false,
  autoAdvanceDisabled = false,
  onAutoAdvanceToggle,
  contactTimestamp = null,
  onSetContact,
  pendingContactTime = null,
  onArmContact,
  onConfirmContact,
  onCancelContact,
  onOpenShortcuts,
  onEditWindow,
  onWheelScrub,
}) => {
  const displayRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const pipVideoRef = useRef<HTMLVideoElement>(null);

  // Auto-dismiss pending contact after 4 seconds of no action
  useEffect(() => {
    if (pendingContactTime == null || !onCancelContact) return;
    const timer = setTimeout(onCancelContact, 4000);
    return () => clearTimeout(timer);
  }, [pendingContactTime, onCancelContact]);

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

  // Sync playback rate on video elements
  useEffect(() => {
    if (videoRef.current) videoRef.current.playbackRate = playbackSpeed;
    if (pipVideoRef.current) pipVideoRef.current.playbackRate = playbackSpeed;
  }, [playbackSpeed]);

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

  const duration = serveEnd - serveStart;
  const toPercent = useCallback(
    (t: number) =>
      duration > 0
        ? Math.max(0, Math.min(100, ((t - serveStart) / duration) * 100))
        : 0,
    [serveStart, duration]
  );

  const contactPct = useMemo(() => {
    if (
      contactTimestamp != null &&
      contactTimestamp >= serveStart &&
      contactTimestamp <= serveEnd
    ) {
      return toPercent(contactTimestamp);
    }
    return null;
  }, [contactTimestamp, serveStart, serveEnd, toPercent]);

  // Scroll wheel frame scrub — only on the video display area
  useEffect(() => {
    if (!onWheelScrub) return;
    const el = displayRef.current;
    if (!el) return;
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      onWheelScrub(e.deltaY);
    };
    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, [onWheelScrub]);

  return (
    <div className="hero-view" data-tour-step="hero-view">
      <div
        className="hero-view__display"
        data-tour-step="hero-display"
        ref={displayRef}
      >
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
              phaseLabel={phaseLabel}
              annotations={annotations}
              serveStartTime={serveStart}
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
          data-tooltip={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
        >
          {isPlaying ? <Pause size={18} /> : <Play size={18} />}
        </button>

        <span className="hero-view__timestamp">{formatTime(currentTime)}</span>

        <div className="hero-view__scrubber-container">
          <div className="hero-view__scrubber-track" aria-hidden="true">
            {contactPct != null && (
              <div
                className="hero-view__contact-marker"
                style={{ left: `${contactPct}%` }}
              />
            )}
          </div>
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
        </div>

        <span className="hero-view__timestamp hero-view__timestamp--end">
          {formatTime(serveEnd)}
        </span>

        {speedOptions && onPlaybackSpeedChange && (
          <div
            className="hero-view__speed-selector"
            role="group"
            aria-label="Playback speed"
          >
            {speedOptions.map((speed) => (
              <button
                key={speed}
                type="button"
                className={`hero-view__speed-btn${
                  playbackSpeed === speed ? ' hero-view__speed-btn--active' : ''
                }`}
                onClick={() => onPlaybackSpeedChange(speed)}
              >
                {speed}x
              </button>
            ))}
          </div>
        )}

        {onLoopToggle && (
          <button
            type="button"
            className={`hero-view__loop-btn${loopActive ? ' hero-view__loop-btn--active' : ''}`}
            onClick={onLoopToggle}
            disabled={loopDisabled}
            aria-label={
              loopActive ? 'Stop looping phase' : 'Loop current phase'
            }
            data-tooltip={
              loopActive
                ? `Stop looping ${loopPhaseLabel ?? 'phase'}`
                : 'Loop phase'
            }
          >
            &#x21bb;
          </button>
        )}

        {onAutoAdvanceToggle && (
          <button
            type="button"
            className={`hero-view__auto-advance-btn${autoAdvanceActive ? ' hero-view__auto-advance-btn--active' : ''}`}
            onClick={onAutoAdvanceToggle}
            disabled={autoAdvanceDisabled}
            aria-label={
              autoAdvanceActive
                ? 'Stop auto-advancing serves'
                : 'Auto-advance to next serve'
            }
            data-tooltip={
              autoAdvanceActive ? 'Stop auto-advance (A)' : 'Auto-advance (A)'
            }
          >
            <ChevronsRight size={14} />
          </button>
        )}

        {(onArmContact || onSetContact) &&
          (pendingContactTime !== null ? (
            <div className="hero-view__contact-confirm" role="group">
              <span className="hero-view__contact-confirm-label">
                <span className="hero-view__contact-diamond">◆</span>
                {pendingContactTime.toFixed(2)}s?
              </span>
              <button
                type="button"
                className="hero-view__contact-confirm-btn hero-view__contact-confirm-btn--yes"
                onClick={onConfirmContact}
                data-tooltip="Confirm"
              >
                ✓
              </button>
              <button
                type="button"
                className="hero-view__contact-confirm-btn hero-view__contact-confirm-btn--no"
                onClick={onCancelContact}
                data-tooltip="Cancel"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="hero-view__contact-btn"
              onClick={() =>
                onArmContact
                  ? onArmContact(currentTime)
                  : onSetContact!(currentTime)
              }
              data-tooltip="Set contact (C)"
            >
              <span className="hero-view__contact-diamond">◆</span>
              {contactTimestamp !== null
                ? contactTimestamp.toFixed(2) + 's'
                : 'Contact'}
            </button>
          ))}
        {onOpenShortcuts && (
          <button
            type="button"
            className="hero-view__shortcuts-hint"
            onClick={onOpenShortcuts}
            data-tooltip="Shortcuts (?)"
            aria-label="Show keyboard shortcuts"
          >
            <Keyboard size={13} />
          </button>
        )}
        {onEditWindow && (
          <button
            type="button"
            className="hero-view__shortcuts-hint"
            onClick={onEditWindow}
            data-tooltip="Edit window"
            aria-label="Edit serve window"
          >
            <Pencil size={13} />
          </button>
        )}
      </div>
    </div>
  );
};

export default HeroView;
