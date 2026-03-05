import React from 'react';
import KneeAngleArc from './KneeAngleArc';
import KneeFrameOverlay from './KneeFrameOverlay';
import MetricDistributionStrip from './MetricDistributionStrip';
import './MetricCard.css';

const DISPLAY_NAMES: Record<string, string> = {
  knee_flexion_min_deg: 'Knee Bend',
  toss_peak_height: 'Toss Height',
  toss_laterality: 'Toss Laterality',
  toss_drop: 'Toss Drop',
};

const UNITS: Record<string, string> = {
  knee_flexion_min_deg: '°',
  toss_peak_height: '',
  toss_laterality: '',
  toss_drop: '',
};

const NULL_EXPLANATIONS: Record<string, string> = {
  knee_flexion_min_deg: 'Knee angle could not be measured',
  toss_peak_height: 'Ball toss was not detected',
  toss_laterality: 'Requires behind-the-player camera angle',
  toss_drop: 'Ball tracking too sparse to measure drop',
};

const TALL_METRICS = new Set(['toss_peak_height']);

interface MetricCardProps {
  metricName: string;
  value: number | null;
  timestamp?: number | null;
  historyValues: number[];
  onScrubTo?: (timestamp: number) => void;
  serveWindowId?: number | null;
}

const MetricCard: React.FC<MetricCardProps> = ({
  metricName,
  value,
  timestamp,
  historyValues,
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

  const formatValue = (v: number) => {
    if (Math.abs(v) >= 100) return v.toFixed(0);
    if (Math.abs(v) >= 10) return v.toFixed(1);
    return v.toFixed(2);
  };

  const Tag = isClickable ? 'button' : 'div';

  // Tall card: value at top, gauge fills remaining height
  if (isTall) {
    return (
      <Tag
        className={`metric-card metric-card--tall${isNull ? ' metric-card--null' : ''}${isClickable ? ' metric-card--clickable' : ''}`}
        onClick={isClickable ? handleClick : undefined}
        type={isClickable ? 'button' : undefined}
        title={isClickable ? `Scrub to ${displayName}` : undefined}
      >
        <p className="metric-card__label">{displayName}</p>
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
      </Tag>
    );
  }

  const showAngleArc = metricName === 'knee_flexion_min_deg' && !isNull;

  // Standard card
  return (
    <Tag
      className={`metric-card${isNull ? ' metric-card--null' : ''}${isClickable ? ' metric-card--clickable' : ''}`}
      onClick={isClickable ? handleClick : undefined}
      type={isClickable ? 'button' : undefined}
      title={isClickable ? `Scrub to ${displayName}` : undefined}
    >
      <p className="metric-card__label">{displayName}</p>
      {showAngleArc ? (
        <div className="metric-card__angle-row">
          <p className="metric-card__value">
            {formatValue(value)}
            {unit && <span className="metric-card__unit">{unit}</span>}
          </p>
          <div className="metric-card__angle-arc">
            {serveWindowId && timestamp != null ? (
              <KneeFrameOverlay
                serveWindowId={serveWindowId}
                timestamp={timestamp}
                angle={value}
              />
            ) : (
              <KneeAngleArc angle={value} />
            )}
          </div>
        </div>
      ) : (
        <p className="metric-card__value">
          {isNull ? '—' : formatValue(value)}
          {!isNull && unit && <span className="metric-card__unit">{unit}</span>}
        </p>
      )}
      {isNull && (
        <p className="metric-card__null-text">
          {NULL_EXPLANATIONS[metricName] ?? 'Not available'}
        </p>
      )}
      {hasStrip && (
        <div className="metric-card__strip">
          <MetricDistributionStrip
            values={historyValues}
            currentValue={value!}
          />
        </div>
      )}
    </Tag>
  );
};

export default MetricCard;
