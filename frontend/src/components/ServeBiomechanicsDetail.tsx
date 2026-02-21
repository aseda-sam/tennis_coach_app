import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useServeBiomechanicsReport } from '../hooks/useServeBiomechanicsReport';
import { PhaseWindow } from '../types/biomechanics';
import LoadingIndicator from './LoadingIndicator';
import MetricsByPhasePanel from './MetricsByPhasePanel';
import ServePhaseTimeline from './ServePhaseTimeline';
import StickFigureCanvas from './StickFigureCanvas';
import './ServeBiomechanicsDetail.css';

interface ServeBiomechanicsDetailProps {
  serveWindowId: number;
  videoId: number;
  serveStart: number;
  serveEnd: number;
  contactTimestamp: number | null;
  onClose: () => void;
}

function findCurrentPhase(
  phases: PhaseWindow[],
  time: number
): PhaseWindow | undefined {
  return phases.find(
    (p) => time >= p.start_timestamp && time <= p.end_timestamp
  );
}

const NEUTRAL_SKELETON_COLOR = '#00ff88';

const ServeBiomechanicsDetail: React.FC<ServeBiomechanicsDetailProps> = ({
  serveWindowId,
  videoId,
  serveStart,
  serveEnd,
  contactTimestamp,
  onClose,
}) => {
  const {
    data: report,
    isLoading,
    error,
  } = useServeBiomechanicsReport(serveWindowId);
  const [currentTime, setCurrentTime] = useState(serveStart);
  const [isPlaying, setIsPlaying] = useState(false);
  const playIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!isPlaying) {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
        playIntervalRef.current = null;
      }
      return;
    }

    playIntervalRef.current = setInterval(() => {
      setCurrentTime((t) => {
        const next = t + 1 / 30;
        if (next > serveEnd) {
          setIsPlaying(false);
          return serveStart;
        }
        return next;
      });
    }, 1000 / 30);

    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    };
  }, [isPlaying, serveStart, serveEnd]);

  const handleSeek = useCallback(
    (t: number) => {
      setCurrentTime(Math.max(serveStart, Math.min(serveEnd, t)));
    },
    [serveStart, serveEnd]
  );

  const handlePlayPause = useCallback(() => {
    setIsPlaying((p) => !p);
  }, []);

  const handleJumpToContact = useCallback(() => {
    if (contactTimestamp !== null) {
      setCurrentTime(contactTimestamp);
      setIsPlaying(false);
    }
  }, [contactTimestamp]);

  const phases = report?.phase_segmentation ?? [];
  const currentPhase = findCurrentPhase(phases, currentTime);

  if (isLoading) {
    return (
      <div className="serve-biomechanics-detail serve-biomechanics-detail--loading">
        <LoadingIndicator size="md" label="Computing biomechanics..." />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="serve-biomechanics-detail serve-biomechanics-detail--error">
        <p>Could not load biomechanics for this serve.</p>
        <button
          className="serve-biomechanics-detail__close-btn"
          onClick={onClose}
        >
          Dismiss
        </button>
      </div>
    );
  }

  return (
    <div className="serve-biomechanics-detail">
      <div className="serve-biomechanics-detail__header">
        <div className="serve-biomechanics-detail__title-row">
          <h3 className="serve-biomechanics-detail__title">
            Serve Biomechanics
          </h3>
        </div>
        <button
          className="serve-biomechanics-detail__close-btn"
          onClick={onClose}
          aria-label="Close biomechanics detail"
        >
          &times;
        </button>
      </div>

      <div className="serve-biomechanics-detail__content">
        <div className="serve-biomechanics-detail__silhouette">
          <div className="serve-biomechanics-detail__canvas-wrapper">
            <StickFigureCanvas
              videoId={videoId}
              currentTime={currentTime}
              isPlaying={isPlaying}
              phaseColor={NEUTRAL_SKELETON_COLOR}
              phaseLabel={currentPhase?.phase_label}
            />
          </div>

          <ServePhaseTimeline
            phases={phases}
            currentTime={currentTime}
            serveStart={serveStart}
            serveEnd={serveEnd}
            onSeek={handleSeek}
          />

          <div className="serve-biomechanics-detail__controls">
            <button
              className="serve-biomechanics-detail__play-btn"
              onClick={handlePlayPause}
            >
              {isPlaying ? 'Pause' : 'Play'}
            </button>
            {contactTimestamp !== null && (
              <button
                className="serve-biomechanics-detail__jump-btn"
                onClick={handleJumpToContact}
              >
                Jump to Contact
              </button>
            )}
          </div>
        </div>

        <div className="serve-biomechanics-detail__metrics-scroll">
          <MetricsByPhasePanel metrics={report.metrics} />
        </div>
      </div>
      <div className="serve-biomechanics-detail__footer">
        <button
          type="button"
          className="serve-biomechanics-detail__back-btn"
          onClick={onClose}
        >
          Back to Serves
        </button>
      </div>
    </div>
  );
};

export default ServeBiomechanicsDetail;
