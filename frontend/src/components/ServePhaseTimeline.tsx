import React from 'react';
import { PhaseWindow } from '../types/biomechanics';
import './ServePhaseTimeline.css';

interface ServePhaseTimelineProps {
  phases: PhaseWindow[];
  currentTime: number;
  serveStart: number;
  serveEnd: number;
  onSeek: (timestamp: number) => void;
}

const NEUTRAL_SEGMENT_COLOR = 'var(--color-border-dark)';
const ACTIVE_SEGMENT_COLOR = 'var(--color-primary)';

const ServePhaseTimeline: React.FC<ServePhaseTimelineProps> = ({
  phases,
  currentTime,
  serveStart,
  serveEnd,
  onSeek,
}) => {
  const duration = serveEnd - serveStart;
  if (duration <= 0) return null;

  const toPercent = (t: number) =>
    Math.max(0, Math.min(100, ((t - serveStart) / duration) * 100));

  const playheadPct = toPercent(currentTime);

  const currentPhase = phases.find(
    (p) => currentTime >= p.start_timestamp && currentTime <= p.end_timestamp
  );

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    onSeek(serveStart + pct * duration);
  };

  return (
    <div className="phase-timeline">
      {currentPhase && (
        <div className="phase-timeline__current-label">
          {currentPhase.phase_label}
        </div>
      )}
      <div className="phase-timeline__track" onClick={handleClick}>
        {phases.map((phase) => {
          const left = toPercent(phase.start_timestamp);
          const width = toPercent(phase.end_timestamp) - left;
          const isActive = phase === currentPhase;
          const color = isActive ? ACTIVE_SEGMENT_COLOR : NEUTRAL_SEGMENT_COLOR;

          return (
            <div
              key={phase.phase}
              className={`phase-timeline__segment ${isActive ? 'phase-timeline__segment--active' : ''}`}
              style={{
                left: `${left}%`,
                width: `${width}%`,
                backgroundColor: color,
                opacity: isActive ? 1 : 0.5,
              }}
              title={phase.phase_label}
            />
          );
        })}
        <div
          className="phase-timeline__playhead"
          style={{ left: `${playheadPct}%` }}
        />
      </div>
      <div className="phase-timeline__labels">
        {phases
          .filter((p) => p.detected)
          .map((phase) => {
            const left = toPercent(
              (phase.start_timestamp + phase.end_timestamp) / 2
            );
            return (
              <span
                key={phase.phase}
                className="phase-timeline__label"
                style={{ left: `${left}%` }}
              >
                {phase.phase_label}
              </span>
            );
          })}
      </div>
    </div>
  );
};

export default ServePhaseTimeline;
