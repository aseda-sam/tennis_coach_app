import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import CollapsibleSection from './CollapsibleSection';
import { TossDropSession } from '../hooks/useTossDropProgress';
import './TossDropProgressSection.css';

interface FlatPoint {
  serveWindowId: number;
  value: number;
  sessionLabel: string;
  sessionIndex: number;
}

interface TossDropProgressSectionProps {
  sessions: TossDropSession[];
  mean: number | null;
  isLoading: boolean;
  currentServeWindowId: number | null;
  expanded: boolean;
  onToggle: () => void;
}

function computeTrend(values: number[]): {
  label: string;
  direction: 'down' | 'up' | 'flat';
} {
  if (values.length < 4) return { label: 'not enough data', direction: 'flat' };
  const recentN = Math.max(3, Math.floor(values.length * 0.3));
  const recent = values.slice(-recentN);
  const earlier = values.slice(0, -recentN);
  const recentMean = recent.reduce((a, b) => a + b, 0) / recent.length;
  const earlierMean = earlier.reduce((a, b) => a + b, 0) / earlier.length;
  const pct = Math.round(
    (Math.abs(recentMean - earlierMean) / earlierMean) * 100
  );
  if (pct < 5) return { label: 'consistent', direction: 'flat' };
  if (recentMean < earlierMean)
    return { label: `${pct}% less drop recently`, direction: 'down' };
  return { label: `${pct}% more drop recently`, direction: 'up' };
}

const DOT_R = 3.5;
const DOT_R_CURRENT = 5.5;
const PADDING_X = 8;
const PADDING_Y = 8;

function renderChart(
  flatPoints: FlatPoint[],
  mean: number,
  currentServeWindowId: number | null,
  chartH: number,
  maxVal: number
) {
  const n = flatPoints.length;

  const toY = (v: number) =>
    PADDING_Y + (chartH - PADDING_Y * 2) * (1 - v / maxVal);

  const meanY = toY(mean);

  const allSessionBoundaries: { label: string; xIndex: number }[] = [];
  let lastSessionIdx = -1;
  flatPoints.forEach((pt, i) => {
    if (pt.sessionIndex !== lastSessionIdx) {
      allSessionBoundaries.push({ label: pt.sessionLabel, xIndex: i });
      lastSessionIdx = pt.sessionIndex;
    }
  });

  // Filter out labels that would overlap — keep only those with ≥8% gap from the previous shown label
  const MIN_LABEL_GAP_PCT = 8;
  const sessionBoundaries: { label: string; xIndex: number }[] = [];
  let lastShownXPct = -Infinity;
  for (const b of allSessionBoundaries) {
    const xPct =
      n === 1 ? 50 : PADDING_X + ((100 - PADDING_X * 2) / (n - 1)) * b.xIndex;
    if (xPct - lastShownXPct >= MIN_LABEL_GAP_PCT) {
      sessionBoundaries.push(b);
      lastShownXPct = xPct;
    }
  }

  // Find which session the current serve window belongs to
  const currentSessionIndex =
    currentServeWindowId != null
      ? (flatPoints.find((p) => p.serveWindowId === currentServeWindowId)
          ?.sessionIndex ?? null)
      : null;

  // x% bounds of the current session for the highlight band
  const toXPct = (i: number) =>
    n === 1 ? 50 : PADDING_X + ((100 - PADDING_X * 2) / (n - 1)) * i;

  let highlightBand: { x1Pct: number; x2Pct: number } | null = null;
  if (currentSessionIndex != null) {
    const sessionIndices = flatPoints
      .map((pt, i) => (pt.sessionIndex === currentSessionIndex ? i : -1))
      .filter((i) => i >= 0);
    if (sessionIndices.length > 0) {
      const stepPct = n > 1 ? (100 - PADDING_X * 2) / (n - 1) : 0;
      const pad = Math.max(stepPct * 0.6, 2);
      highlightBand = {
        x1Pct: toXPct(sessionIndices[0]) - pad,
        x2Pct: toXPct(sessionIndices[sessionIndices.length - 1]) + pad,
      };
    }
  }

  const polylinePoints = flatPoints
    .map((pt, i) => {
      const x = toXPct(i);
      const y = toY(pt.value);
      return `${x}%,${y}`;
    })
    .join(' ');

  return (
    <svg
      width="100%"
      height={chartH + 18}
      className="toss-drop-progress__svg"
      aria-label="Ball drop trend across serves"
    >
      {/* Current-session highlight band */}
      {highlightBand && (
        <rect
          x={`${highlightBand.x1Pct}%`}
          y={PADDING_Y - 4}
          width={`${highlightBand.x2Pct - highlightBand.x1Pct}%`}
          height={chartH - PADDING_Y * 2 + 8}
          rx="6"
          className="toss-drop-progress__session-band"
        />
      )}

      {/* Mean reference line — split so it's visible both inside and outside the band */}
      {highlightBand ? (
        <>
          <line
            x1={`${PADDING_X}%`}
            y1={meanY}
            x2={`${highlightBand.x1Pct}%`}
            y2={meanY}
            className="toss-drop-progress__mean-line"
          />
          <line
            x1={`${highlightBand.x1Pct}%`}
            y1={meanY}
            x2={`${highlightBand.x2Pct}%`}
            y2={meanY}
            className="toss-drop-progress__mean-line toss-drop-progress__mean-line--on-dark"
          />
          <line
            x1={`${highlightBand.x2Pct}%`}
            y1={meanY}
            x2={`${100 - PADDING_X}%`}
            y2={meanY}
            className="toss-drop-progress__mean-line"
          />
        </>
      ) : (
        <line
          x1={`${PADDING_X}%`}
          y1={meanY}
          x2={`${100 - PADDING_X}%`}
          y2={meanY}
          className="toss-drop-progress__mean-line"
        />
      )}

      {/* Connecting line */}
      {n > 1 && (
        <polyline
          points={polylinePoints}
          className="toss-drop-progress__line"
        />
      )}

      {/* Dots */}
      {flatPoints.map((pt, i) => {
        const isCurrent = pt.serveWindowId === currentServeWindowId;
        const cx = toXPct(i);
        const cy = toY(pt.value);
        const r = isCurrent ? DOT_R_CURRENT : DOT_R;
        return (
          <circle
            key={pt.serveWindowId}
            cx={`${cx}%`}
            cy={cy}
            r={r}
            className={(() => {
              if (isCurrent)
                return 'toss-drop-progress__dot toss-drop-progress__dot--current';
              if (
                currentSessionIndex != null &&
                pt.sessionIndex === currentSessionIndex
              )
                return 'toss-drop-progress__dot toss-drop-progress__dot--in-session';
              return 'toss-drop-progress__dot';
            })()}
          >
            <title>{`${pt.sessionLabel}: ${pt.value.toFixed(2)}`}</title>
          </circle>
        );
      })}

      {/* Session boundary labels */}
      {sessionBoundaries.map(({ label, xIndex }) => {
        const cx = toXPct(xIndex);
        return (
          <text
            key={`${label}-${xIndex}`}
            x={`${cx}%`}
            y={chartH + 14}
            className="toss-drop-progress__session-tick"
            textAnchor="middle"
          >
            {label}
          </text>
        );
      })}
    </svg>
  );
}

const ExpandIcon: React.FC = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 14 14"
    fill="none"
    aria-hidden="true"
  >
    <path
      d="M1 5V1h4M9 1h4v4M13 9v4H9M5 13H1V9"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const CollapseIcon: React.FC = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 14 14"
    fill="none"
    aria-hidden="true"
  >
    <path
      d="M5 1v4H1M13 5H9V1M9 13v-4h4M1 9h4v4"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const TossDropProgressSection: React.FC<TossDropProgressSectionProps> = ({
  sessions,
  mean,
  isLoading,
  currentServeWindowId,
  expanded,
  onToggle,
}) => {
  const [fullscreen, setFullscreen] = useState(false);

  if (isLoading || sessions.length === 0 || mean == null) return null;

  // Flatten sessions into a single chronological list, skip nulls
  const flatPoints: FlatPoint[] = [];
  sessions.forEach((session, si) => {
    session.points.forEach((pt) => {
      if (pt.value != null) {
        flatPoints.push({
          serveWindowId: pt.serveWindowId,
          value: pt.value,
          sessionLabel: session.dateLabel,
          sessionIndex: si,
        });
      }
    });
  });

  if (flatPoints.length < 3) return null;

  const allValues = flatPoints.map((p) => p.value);
  const trend = computeTrend(allValues);
  const maxVal = Math.max(...allValues) * 1.1;

  const trendEl = (
    <p
      className={`toss-drop-progress__trend toss-drop-progress__trend--${trend.direction}`}
    >
      {trend.direction === 'down' && '↓ '}
      {trend.direction === 'up' && '↑ '}
      {trend.direction === 'flat' && '→ '}
      {trend.label}
    </p>
  );

  const legendEl = (
    <p className="toss-drop-progress__legend">
      <svg
        width="10"
        height="10"
        className="toss-drop-progress__legend-dot-svg"
      >
        <circle
          cx="5"
          cy="5"
          r="4"
          className="toss-drop-progress__dot--current"
        />
      </svg>{' '}
      This Serve ·{' '}
      <svg
        width="16"
        height="10"
        className="toss-drop-progress__legend-dot-svg"
      >
        <rect
          x="0"
          y="0"
          width="16"
          height="10"
          rx="2"
          className="toss-drop-progress__session-band"
        />
      </svg>{' '}
      This Video ·{' '}
      <svg
        width="12"
        height="4"
        className="toss-drop-progress__legend-line-svg"
      >
        <line
          x1="0"
          y1="2"
          x2="12"
          y2="2"
          className="toss-drop-progress__mean-line"
        />
      </svg>{' '}
      Avg {mean.toFixed(2)}
    </p>
  );

  return (
    <>
      <CollapsibleSection
        title="Ball Drop Trend"
        expanded={expanded}
        onToggle={onToggle}
        headerActions={
          <button
            type="button"
            className="toss-drop-progress__expand-btn"
            onClick={(e) => {
              e.stopPropagation();
              setFullscreen(true);
            }}
            aria-label="Expand chart"
            title="Expand"
          >
            <ExpandIcon />
          </button>
        }
      >
        <div className="toss-drop-progress">
          {trendEl}
          {renderChart(flatPoints, mean, currentServeWindowId, 60, maxVal)}
          {legendEl}
        </div>
      </CollapsibleSection>

      {fullscreen &&
        createPortal(
          <div
            className="toss-drop-progress__overlay"
            onClick={() => setFullscreen(false)}
          >
            <div
              className="toss-drop-progress__overlay-panel"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="toss-drop-progress__overlay-header">
                <span className="toss-drop-progress__overlay-title">
                  Ball Drop Trend
                </span>
                <button
                  type="button"
                  className="toss-drop-progress__expand-btn toss-drop-progress__expand-btn--close"
                  onClick={() => setFullscreen(false)}
                  aria-label="Close expanded view"
                >
                  <CollapseIcon />
                </button>
              </div>
              <div className="toss-drop-progress__overlay-body">
                {trendEl}
                {renderChart(
                  flatPoints,
                  mean,
                  currentServeWindowId,
                  360,
                  maxVal
                )}
                {legendEl}
              </div>
            </div>
          </div>,
          document.body
        )}
    </>
  );
};

export default TossDropProgressSection;
