import React from 'react';

interface MetricDistributionStripProps {
  values: number[];
  currentValue: number;
  orientation?: 'horizontal' | 'vertical';
}

/** Fraction (0–1) representing how far up the vertical gauge the current value sits. */
export function currentValuePosition(
  values: number[],
  currentValue: number
): number {
  const allValues = [...values, currentValue];
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = max - min;
  if (range === 0) return 0.5;
  return (currentValue - min) / range;
}

const MetricDistributionStrip: React.FC<MetricDistributionStripProps> = ({
  values,
  currentValue,
  orientation = 'horizontal',
}) => {
  if (values.length < 3) return null;

  const allValues = [...values, currentValue];
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  const range = max - min;

  const toPos = (v: number) => {
    if (range === 0) return 50;
    return ((v - min) / range) * 100;
  };

  const formatLabel = (v: number) => {
    if (Math.abs(v) >= 100) return v.toFixed(0);
    if (Math.abs(v) >= 10) return v.toFixed(1);
    return v.toFixed(2);
  };

  if (orientation === 'vertical') {
    // Vertical gauge. Uses a tall narrow viewBox with xMidYMid meet
    // so circles stay round. The parent stretches this vertically via CSS.
    const trackX = 8;
    const trackTop = 8;
    const trackBottom = 192;
    const trackLen = trackBottom - trackTop;
    const toY = (v: number) => trackBottom - (toPos(v) / 100) * trackLen;

    return (
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 16 200"
        preserveAspectRatio="xMidYMid meet"
        style={{ display: 'block' }}
        role="img"
        aria-label="Toss height distribution"
      >
        {/* Track line */}
        <line
          x1={trackX}
          y1={trackTop}
          x2={trackX}
          y2={trackBottom}
          stroke="var(--color-border-dark)"
          strokeWidth="0.5"
        />
        {/* Past serves */}
        {values.map((v, i) => (
          <circle
            key={i}
            cx={trackX}
            cy={toY(v)}
            r={2.5}
            fill="var(--color-text-muted)"
            opacity={0.45}
          />
        ))}
        {/* Current serve — tennis ball */}
        <circle
          cx={trackX}
          cy={toY(currentValue)}
          r={5}
          fill="var(--color-arc)"
          stroke="var(--color-arc-dim)"
          strokeWidth="1.2"
        />
      </svg>
    );
  }

  // Horizontal strip
  return (
    <svg
      width="100%"
      height="32"
      viewBox="0 0 200 32"
      preserveAspectRatio="none"
      style={{ display: 'block' }}
      role="img"
      aria-label="Distribution of past values"
    >
      {/* Track line */}
      <line
        x1="10"
        y1="10"
        x2="190"
        y2="10"
        stroke="var(--color-border-dark)"
        strokeWidth="1"
      />
      {/* Past serves */}
      {values.map((v, i) => (
        <circle
          key={i}
          cx={10 + (toPos(v) / 100) * 180}
          cy={10}
          r={3}
          fill="var(--color-text-muted)"
          opacity={0.4}
        />
      ))}
      {/* Current serve — tennis ball */}
      <circle
        cx={10 + (toPos(currentValue) / 100) * 180}
        cy={10}
        r={5}
        fill="var(--color-arc)"
        stroke="var(--color-arc-dim)"
        strokeWidth="1.5"
      />
      {/* Min label */}
      <text
        x="10"
        y="28"
        fontSize="9"
        fontFamily="var(--font-mono)"
        fill="var(--color-text-muted)"
        textAnchor="start"
      >
        {formatLabel(min)}
      </text>
      {/* Max label */}
      <text
        x="190"
        y="28"
        fontSize="9"
        fontFamily="var(--font-mono)"
        fill="var(--color-text-muted)"
        textAnchor="end"
      >
        {formatLabel(max)}
      </text>
    </svg>
  );
};

export default MetricDistributionStrip;
