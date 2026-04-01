import React, { useState } from 'react';
import CollapsibleSection from './CollapsibleSection';
import { TossDropSession } from '../hooks/useTossDropProgress';
import './TossDropProgressSection.css';

interface TossDropProgressSectionProps {
  sessions: TossDropSession[];
  mean: number | null;
  isLoading: boolean;
}

const BAR_MAX_HEIGHT = 48;
const BAR_WIDTH = 8;
const BAR_GAP = 4;
const SVG_PADDING = 4;

function SessionChart({
  session,
  globalMax,
  mean,
}: {
  session: TossDropSession;
  globalMax: number;
  mean: number;
}) {
  const n = session.points.length;
  const svgWidth = n * (BAR_WIDTH + BAR_GAP) - BAR_GAP + SVG_PADDING * 2;
  const svgHeight = BAR_MAX_HEIGHT + SVG_PADDING * 2;
  const meanY =
    SVG_PADDING + BAR_MAX_HEIGHT - (mean / globalMax) * BAR_MAX_HEIGHT;

  return (
    <div className="toss-drop-progress__session">
      <p className="toss-drop-progress__session-label">{session.dateLabel}</p>
      <svg
        width={svgWidth}
        height={svgHeight}
        style={{ width: svgWidth, height: svgHeight, flexShrink: 0 }}
        className="toss-drop-progress__chart"
        aria-label={`Ball drop trend for ${session.dateLabel}`}
      >
        {/* Mean reference line */}
        <line
          x1={SVG_PADDING}
          y1={meanY}
          x2={svgWidth - SVG_PADDING}
          y2={meanY}
          stroke="var(--color-text-muted)"
          strokeWidth="1"
          strokeDasharray="3 2"
        />

        {session.points.map((pt, i) => {
          const x = SVG_PADDING + i * (BAR_WIDTH + BAR_GAP);
          if (pt.value == null) {
            // Null slot: empty bar outline
            return (
              <rect
                key={pt.serveWindowId}
                x={x}
                y={SVG_PADDING}
                width={BAR_WIDTH}
                height={BAR_MAX_HEIGHT}
                rx={2}
                fill="var(--color-surface-tertiary)"
                stroke="var(--color-border)"
                strokeWidth="0.5"
              />
            );
          }

          const barHeight = Math.max(
            2,
            (pt.value / globalMax) * BAR_MAX_HEIGHT
          );
          const barY = SVG_PADDING + BAR_MAX_HEIGHT - barHeight;
          // Color: above mean = worse (more orange), below mean = better (primary green)
          const aboveMean = pt.value > mean;
          const fill = aboveMean
            ? 'var(--color-clay, #d4784a)'
            : 'var(--color-primary)';

          return (
            <rect
              key={pt.serveWindowId}
              x={x}
              y={barY}
              width={BAR_WIDTH}
              height={barHeight}
              rx={2}
              fill={fill}
              opacity={0.85}
            >
              <title>{`Ball drop: ${pt.value.toFixed(2)}`}</title>
            </rect>
          );
        })}
      </svg>
    </div>
  );
}

const TossDropProgressSection: React.FC<TossDropProgressSectionProps> = ({
  sessions,
  mean,
  isLoading,
}) => {
  const [expanded, setExpanded] = useState(false);

  if (isLoading || sessions.length === 0 || mean == null) return null;

  // Global max across all sessions so bars are on the same scale
  const allValues = sessions
    .flatMap((s) => s.points.map((p) => p.value))
    .filter((v): v is number => v != null);
  const globalMax = Math.max(...allValues) * 1.1; // 10% headroom

  return (
    <CollapsibleSection
      title="Ball Drop Trend"
      expanded={expanded}
      onToggle={() => setExpanded(!expanded)}
      variant="muted"
    >
      <div className="toss-drop-progress">
        <p className="toss-drop-progress__legend">
          <span className="toss-drop-progress__legend-above" />
          above avg &nbsp;
          <span className="toss-drop-progress__legend-below" />
          below avg &nbsp;
          <span className="toss-drop-progress__legend-mean" />
          your mean ({mean.toFixed(2)})
        </p>
        <div className="toss-drop-progress__sessions">
          {sessions.map((session, i) => (
            <SessionChart
              key={session.videoId ?? i}
              session={session}
              globalMax={globalMax}
              mean={mean}
            />
          ))}
        </div>
      </div>
    </CollapsibleSection>
  );
};

export default TossDropProgressSection;
