import React from 'react';
import KneeFrameOverlay from './KneeFrameOverlay';
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
  knee_flexion_min_deg: 'Deepest knee angle before contact',
  toss_peak_height: 'Ball peak relative to body height',
};

/** Metrics shown in the sidebar. Everything else from the API is hidden. */
export const VISIBLE_METRICS = new Set(Object.keys(DISPLAY_NAMES));

interface MetricCardProps {
  metricName: string;
  value: number | null;
  timestamp?: number | null;
  onScrubTo?: (timestamp: number) => void;
  serveWindowId?: number | null;
}

const MetricCard: React.FC<MetricCardProps> = ({
  metricName,
  value,
  timestamp,
  onScrubTo,
  serveWindowId,
}) => {
  const displayName = DISPLAY_NAMES[metricName] ?? metricName;
  const unit = UNITS[metricName] ?? '';
  const isNull = value == null;
  const isClickable = !isNull && timestamp != null && onScrubTo != null;

  const handleClick = () => {
    if (isClickable && timestamp != null && onScrubTo) {
      onScrubTo(timestamp);
    }
  };

  const formatValue = (v: number) => {
    if (Math.abs(v) >= 100) return v.toFixed(0);
    if (Math.abs(v) >= 10) return v.toFixed(1);
    return v.toFixed(2);
  };

  const Tag = isClickable ? 'button' : 'div';
  const showFrame = metricName === 'knee_flexion_min_deg' && !isNull;

  return (
    <Tag
      className={`metric-card${isNull ? ' metric-card--null' : ''}${isClickable ? ' metric-card--clickable' : ''}`}
      onClick={isClickable ? handleClick : undefined}
      type={isClickable ? 'button' : undefined}
      title={isClickable ? `Scrub to ${displayName}` : undefined}
    >
      <p className="metric-card__label">{displayName}</p>
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
    </Tag>
  );
};

export default MetricCard;
