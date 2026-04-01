import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import KneeFrameOverlay from './KneeFrameOverlay';
import MetricDistributionStrip from './MetricDistributionStrip';
import './MetricCard.css';

const DISPLAY_NAMES: Record<string, string> = {
  knee_flexion_min_deg: 'Knee Bend',
  toss_peak_height: 'Toss Height',
};

const UNITS: Record<string, string> = {
  knee_flexion_min_deg: '°',
  toss_peak_height: '',
};

const NULL_EXPLANATIONS: Record<string, string> = {
  knee_flexion_min_deg: 'Knee angle could not be measured',
  toss_peak_height: 'Ball toss was not detected',
};

const DESCRIPTIONS: Record<string, string> = {
  knee_flexion_min_deg: 'Lowest point of your knee bend',
  toss_peak_height: 'How high your toss went',
};

const INFO_DETAILS: Record<string, string[]> = {
  knee_flexion_min_deg: [
    'The angle between your thigh and shin. A straight leg is 180°, a deep squat is closer to 90°.',
    'Lower numbers mean a deeper bend.',
  ],
  toss_peak_height: [
    'Measured as a multiple of your body height. 2.0 means the ball peaked at twice your height.',
    'The gray dots show your toss heights from other serves. The green dot is this serve.',
  ],
};

/** Metrics shown in the sidebar. Everything else from the API is hidden. */
export const VISIBLE_METRICS = new Set(Object.keys(DISPLAY_NAMES));

const InfoPopover: React.FC<{ lines: string[] }> = ({ lines }) => {
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  const updatePosition = useCallback(() => {
    if (!btnRef.current) return;
    const rect = btnRef.current.getBoundingClientRect();
    const popoverWidth = 220;
    // Center popover under the button; clamp so it doesn't overflow viewport
    let left = rect.left + rect.width / 2 - popoverWidth / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - popoverWidth - 8));
    setPos({ top: rect.bottom + 6, left });
  }, []);

  useEffect(() => {
    if (!open) return;
    updatePosition();
    const handleClick = (e: MouseEvent) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        btnRef.current &&
        !btnRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    const handleScroll = () => setOpen(false);
    document.addEventListener('mousedown', handleClick);
    window.addEventListener('scroll', handleScroll, true);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      window.removeEventListener('scroll', handleScroll, true);
    };
  }, [open, updatePosition]);

  return (
    <>
      <button
        ref={btnRef}
        className="metric-card__info-btn"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
        type="button"
        aria-label="More info"
      >
        <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.4" />
          <path
            d="M8 7v4M8 5.5v-.01"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      </button>
      {open &&
        createPortal(
          <div
            ref={popoverRef}
            className="metric-card__info-popover"
            style={{ top: pos.top, left: pos.left }}
          >
            {lines.map((line, i) => (
              <p key={i}>{line}</p>
            ))}
          </div>,
          document.body
        )}
    </>
  );
};

const TALL_METRICS = new Set(['toss_peak_height']);

interface MetricCardProps {
  metricName: string;
  value: number | null;
  timestamp?: number | null;
  historyValues?: number[];
  onScrubTo?: (timestamp: number) => void;
  serveWindowId?: number | null;
}

const MetricCard: React.FC<MetricCardProps> = ({
  metricName,
  value,
  timestamp,
  historyValues = [],
  onScrubTo,
  serveWindowId,
}) => {
  const displayName = DISPLAY_NAMES[metricName] ?? metricName;
  const unit = UNITS[metricName] ?? '';
  const isNull = value == null;
  const isClickable = !isNull && timestamp != null && onScrubTo != null;
  const isTall = TALL_METRICS.has(metricName);
  const hasStrip = !isNull && historyValues.length >= 3;

  const handleClick = () => {
    if (isClickable && timestamp != null && onScrubTo) {
      onScrubTo(timestamp);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      handleClick();
    }
  };

  const formatValue = (v: number) => {
    if (Math.abs(v) >= 100) return v.toFixed(0);
    if (Math.abs(v) >= 10) return v.toFixed(1);
    return v.toFixed(2);
  };

  // Tall card: value at top, vertical gauge fills remaining height
  if (isTall) {
    return (
      <div
        className={`metric-card metric-card--tall${isNull ? ' metric-card--null' : ''}${isClickable ? ' metric-card--clickable' : ''}`}
        onClick={isClickable ? handleClick : undefined}
        role={isClickable ? 'button' : undefined}
        tabIndex={isClickable ? 0 : undefined}
        onKeyDown={isClickable ? handleKeyDown : undefined}
        title={isClickable ? `Scrub to ${displayName}` : undefined}
      >
        <div className="metric-card__header">
          <p className="metric-card__label">{displayName}</p>
          {!isNull && INFO_DETAILS[metricName] && (
            <InfoPopover lines={INFO_DETAILS[metricName]} />
          )}
        </div>
        {!isNull && DESCRIPTIONS[metricName] && (
          <p className="metric-card__description">{DESCRIPTIONS[metricName]}</p>
        )}
        <p className="metric-card__value">
          {isNull ? '—' : formatValue(value)}
          {!isNull && unit && <span className="metric-card__unit">{unit}</span>}
        </p>
        {isNull && (
          <p className="metric-card__null-text">
            {NULL_EXPLANATIONS[metricName] ?? 'Not available'}
          </p>
        )}
        {hasStrip && (
          <div className="metric-card__tall-gauge">
            <MetricDistributionStrip
              values={historyValues}
              currentValue={value!}
              orientation="vertical"
            />
          </div>
        )}
      </div>
    );
  }

  const showFrame = metricName === 'knee_flexion_min_deg' && !isNull;

  // Standard card
  return (
    <div
      className={`metric-card${isNull ? ' metric-card--null' : ''}${isClickable ? ' metric-card--clickable' : ''}`}
      onClick={isClickable ? handleClick : undefined}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? handleKeyDown : undefined}
      title={isClickable ? `Scrub to ${displayName}` : undefined}
    >
      <div className="metric-card__header">
        <p className="metric-card__label">{displayName}</p>
        {!isNull && INFO_DETAILS[metricName] && (
          <InfoPopover lines={INFO_DETAILS[metricName]} />
        )}
      </div>
      {!isNull && DESCRIPTIONS[metricName] && (
        <p className="metric-card__description">{DESCRIPTIONS[metricName]}</p>
      )}
      <p className="metric-card__value">
        {isNull ? '—' : formatValue(value)}
        {!isNull && unit && <span className="metric-card__unit">{unit}</span>}
      </p>
      {isNull && (
        <p className="metric-card__null-text">
          {NULL_EXPLANATIONS[metricName] ?? 'Not available'}
        </p>
      )}
      {showFrame && serveWindowId && timestamp != null && (
        <div className="metric-card__frame">
          <KneeFrameOverlay
            serveWindowId={serveWindowId}
            timestamp={timestamp}
            angle={value}
          />
        </div>
      )}
    </div>
  );
};

export default MetricCard;
