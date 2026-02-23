import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { MetricValue, PhaseWindow } from '../types/biomechanics';
import { ViewMode } from './AnalysisViewToggle';
import { Keyboard, Pause, Play } from 'lucide-react';
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
  onLoopToggle?: () => void;
  phases?: PhaseWindow[];
  activePhase?: string | null;
  contactTimestamp?: number | null;
  onSetContact?: (timestamp: number) => Promise<void>;
  pendingContactTime?: number | null;
  onArmContact?: (time: number) => void;
  onConfirmContact?: () => void;
  onCancelContact?: () => void;
  onOpenShortcuts?: () => void;
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
  onLoopToggle,
  phases = [],
  activePhase = null,
  contactTimestamp = null,
  onSetContact,
  pendingContactTime = null,
  onArmContact,
  onConfirmContact,
  onCancelContact,
  onOpenShortcuts,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const pipVideoRef = useRef<HTMLVideoElement>(null);

  // One-time keyboard shortcut hint tooltip
  const [showKbdTip, setShowKbdTip] = useState(false);
  useEffect(() => {
    if (!onOpenShortcuts) return;
    if (localStorage.getItem('kbd-hint-seen')) return;
    const show = setTimeout(() => setShowKbdTip(true), 800);
    return () => clearTimeout(show);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!showKbdTip) return;
    const hide = setTimeout(() => {
      setShowKbdTip(false);
      localStorage.setItem('kbd-hint-seen', '1');
    }, 4000);
    return () => clearTimeout(hide);
  }, [showKbdTip]);

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

  const hasPhases = phases.length > 0;

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
          {isPlaying ? <Pause size={18} /> : <Play size={18} />}
        </button>

        <span className="hero-view__timestamp">{formatTime(currentTime)}</span>

        <div className="hero-view__scrubber-container">
          {hasPhases && (
            <div className="hero-view__phase-track" aria-hidden="true">
              {phases.map((phase) => {
                const left = toPercent(phase.start_timestamp);
                const width = toPercent(phase.end_timestamp) - left;
                const isActive = activePhase === phase.phase;
                return (
                  <div
                    key={phase.phase}
                    className={`hero-view__phase-segment${isActive ? ' hero-view__phase-segment--active' : ''}`}
                    style={{ left: `${left}%`, width: `${width}%` }}
                    title={phase.phase_label}
                  />
                );
              })}
              {contactPct != null && (
                <div
                  className="hero-view__contact-marker"
                  style={{ left: `${contactPct}%` }}
                  title={`Contact: ${contactTimestamp!.toFixed(2)}s`}
                />
              )}
            </div>
          )}
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
            title={loopActive ? 'Stop looping phase' : 'Loop current phase'}
          >
            &#x21bb;
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
                title="Confirm contact timestamp"
              >
                ✓
              </button>
              <button
                type="button"
                className="hero-view__contact-confirm-btn hero-view__contact-confirm-btn--no"
                onClick={onCancelContact}
                title="Cancel"
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
              title="Set ball contact at current time (C)"
            >
              <span className="hero-view__contact-diamond">◆</span>
              {contactTimestamp !== null
                ? contactTimestamp.toFixed(2) + 's'
                : 'Contact'}
            </button>
          ))}

        {onOpenShortcuts && (
          <div className="hero-view__shortcuts-hint-wrap">
            {showKbdTip && (
              <div className="hero-view__kbd-tip" role="tooltip">
                Press <kbd>?</kbd> for keyboard shortcuts
              </div>
            )}
            <button
              type="button"
              className="hero-view__shortcuts-hint"
              onClick={() => {
                setShowKbdTip(false);
                localStorage.setItem('kbd-hint-seen', '1');
                onOpenShortcuts();
              }}
              title="Keyboard shortcuts (?)"
              aria-label="Show keyboard shortcuts"
            >
              <Keyboard size={13} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default HeroView;
