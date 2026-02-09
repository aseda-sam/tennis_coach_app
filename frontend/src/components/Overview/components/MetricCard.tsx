import { useEffect, useState } from 'react';
import './MetricCard.css';

interface MetricCardProps {
  title: string;
  value: number;
  unit: string;
  trend: 'improving' | 'declining' | 'stable';
  consistencyLabel?: string;
  consistencyRating?: 'excellent' | 'good' | 'fair' | 'needs_work';
  delay?: number;
}

const TREND_CONFIG = {
  improving: { arrow: '\u2191', className: 'trend-improving', label: 'Improving' },
  declining: { arrow: '\u2193', className: 'trend-declining', label: 'Declining' },
  stable: { arrow: '\u2192', className: 'trend-stable', label: 'Stable' },
} as const;

function MetricCard({
  title,
  value,
  unit,
  trend,
  consistencyLabel,
  consistencyRating,
  delay = 0,
}: MetricCardProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  useEffect(() => {
    if (!visible) return;

    const duration = 600;
    const steps = 30;
    const increment = value / steps;
    let current = 0;
    let step = 0;

    const interval = setInterval(() => {
      step++;
      current = Math.min(current + increment, value);
      setDisplayValue(Number(current.toFixed(1)));
      if (step >= steps) clearInterval(interval);
    }, duration / steps);

    return () => clearInterval(interval);
  }, [value, visible]);

  const trendInfo = TREND_CONFIG[trend];

  return (
    <div className={`metric-card ${visible ? 'metric-card-visible' : ''}`}>
      <h3 className="metric-card-title">{title}</h3>
      <div className="metric-card-value-row">
        <span className="metric-card-value">{displayValue}</span>
        <span className="metric-card-unit">{unit}</span>
        <span className={`metric-card-trend ${trendInfo.className}`} title={trendInfo.label}>
          {trendInfo.arrow}
        </span>
      </div>
      {consistencyLabel && consistencyRating && (
        <div className="metric-card-footer">
          <span className="metric-card-consistency-label">{consistencyLabel}</span>
          <span className={`metric-card-rating rating-${consistencyRating}`}>
            {consistencyRating.replace('_', ' ')}
          </span>
        </div>
      )}
    </div>
  );
}

export default MetricCard;
