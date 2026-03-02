import React, { useCallback, useMemo } from 'react';
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { DetectionMeta, PhaseWindow } from '../types/biomechanics';
import './DetectionDetailsPanel.css';

/** Custom dot renderer: draws a playback circle and/or a contact diamond at their respective frames. */
const ChartDot: React.FC<{
  cx?: number;
  cy?: number;
  payload?: { frame: number };
  currentFrame: number | null;
  contactFrame: number | null;
  lineColor: string;
}> = ({ cx, cy, payload, currentFrame, contactFrame, lineColor }) => {
  if (cx == null || cy == null || payload == null) return null;
  const frame = payload.frame;
  const isPlayback = frame === currentFrame;
  const isContact = frame === contactFrame;
  if (!isPlayback && !isContact) return null;
  const s = 7;
  return (
    <g>
      {isContact && (
        <polygon
          points={`${cx},${cy - s} ${cx + s},${cy} ${cx},${cy + s} ${cx - s},${cy}`}
          fill="#f5a623"
          stroke="white"
          strokeWidth={1.5}
        />
      )}
      {isPlayback && (
        <circle cx={cx} cy={cy} r={4} fill={lineColor} stroke="none" />
      )}
    </g>
  );
};

const KTP_DISPLAY_NAMES: Record<string, string> = {
  ball_release: 'Ball Release',
  trophy_position: 'Trophy Position',
  racket_low_point: 'Racket Low Point',
  ball_impact: 'Ball Impact',
};

const KTP_ORDER = [
  'ball_release',
  'trophy_position',
  'racket_low_point',
  'ball_impact',
];

/** Format extra KTP fields into a readable string. */
function formatKTPDetails(
  ktpKey: string,
  ktp: Record<string, unknown>
): string {
  const parts: string[] = [];

  if (ktp.search_window) {
    const sw = ktp.search_window as [number, number];
    parts.push(`search [${sw[0]}, ${sw[1]}]`);
  }
  if (typeof ktp.wrist_height === 'number') {
    parts.push(`height ${(ktp.wrist_height as number).toFixed(2)}`);
  }
  if (typeof ktp.wrist_y === 'number') {
    parts.push(`wrist_y ${(ktp.wrist_y as number).toFixed(2)}`);
  }
  if (typeof ktp.knee_validation === 'boolean') {
    parts.push(`knee ${ktp.knee_validation ? '\u2713' : '\u2717'}`);
  }
  if (typeof ktp.candidates_tried === 'number') {
    parts.push(`${ktp.candidates_tried} candidates`);
  }

  return parts.length > 0 ? parts.join(', ') : '\u2014';
}

function formatMethod(method: string): string {
  return method.replace(/_/g, ' ');
}

interface FeatureChartProps {
  data: number[];
  label: string;
  hint?: string;
  fps: number;
  contactFrame: number | null;
  currentFrame: number | null;
  color: string;
  onFrameClick: (frame: number) => void;
  frameRange?: [number, number] | null;
}

const FeatureChart: React.FC<FeatureChartProps> = ({
  data,
  label,
  hint,
  contactFrame,
  currentFrame,
  color,
  onFrameClick,
  frameRange,
}) => {
  const chartData = useMemo(() => {
    const startFrame = frameRange ? frameRange[0] : 0;
    const endFrame = frameRange ? frameRange[1] : data.length - 1;
    return data
      .slice(startFrame, endFrame + 1)
      .map((value, i) => ({ frame: startFrame + i, value }));
  }, [data, frameRange]);

  const handleClick = useCallback(
    (state: { activeLabel?: string | number } | null) => {
      if (state?.activeLabel != null) {
        onFrameClick(Number(state.activeLabel));
      }
    },
    [onFrameClick]
  );

  return (
    <div className="detection-details__chart">
      <span className="detection-details__chart-label">
        {label}
        {hint && <span className="detection-details__chart-hint">{hint}</span>}
      </span>
      <ResponsiveContainer width="100%" height={100}>
        <LineChart
          data={chartData}
          margin={{ top: 4, right: 4, bottom: 4, left: 4 }}
          onClick={handleClick}
          style={{ cursor: 'crosshair' }}
        >
          <XAxis dataKey="frame" hide />
          <YAxis hide domain={['auto', 'auto']} />
          <Tooltip
            cursor={{ stroke: 'var(--color-text)', strokeOpacity: 0.4 }}
            content={() => null}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={
              <ChartDot
                currentFrame={currentFrame}
                contactFrame={contactFrame}
                lineColor={color}
              />
            }
            activeDot={{ r: 4, fill: color, stroke: 'none' }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Shared helpers for sub-components                                  */
/* ------------------------------------------------------------------ */

function useDetectionHelpers(detectionMeta: DetectionMeta, serveStart: number) {
  const { ktps, fps, total_frames } = detectionMeta;

  const ktpFrameMarkers = useMemo(() => {
    const markers: { frame: number; label: string }[] = [];
    for (const key of KTP_ORDER) {
      const ktp = ktps[key];
      if (ktp && ktp.frame != null) {
        markers.push({
          frame: ktp.frame,
          label: KTP_DISPLAY_NAMES[key] ?? key,
        });
      }
    }
    return markers;
  }, [ktps]);

  return { fps, total_frames, ktpFrameMarkers, serveStart };
}

/* ------------------------------------------------------------------ */
/*  KTPTable                                                           */
/* ------------------------------------------------------------------ */

interface KTPTableProps {
  detectionMeta: DetectionMeta;
  serveStart: number;
  onSeek: (t: number) => void;
}

export const KTPTable: React.FC<KTPTableProps> = ({
  detectionMeta,
  serveStart,
  onSeek,
}) => {
  const { ktps, fps } = detectionMeta;

  const handleRowClick = (frame: number | null) => {
    if (frame == null || fps <= 0) return;
    const timestamp = serveStart + frame / fps;
    onSeek(timestamp);
  };

  return (
    <div className="detection-details__section">
      <table className="detection-details__table">
        <thead>
          <tr>
            <th>KTP</th>
            <th>Frame</th>
            <th>Time</th>
            <th>Method</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {KTP_ORDER.map((key) => {
            const ktp = ktps[key];
            if (!ktp) return null;
            const frame = ktp.frame;
            const timestamp =
              frame != null && fps > 0 ? serveStart + frame / fps : null;
            return (
              <tr
                key={key}
                className={`detection-details__row${frame != null ? ' detection-details__row--clickable' : ''}`}
                onClick={() => handleRowClick(frame)}
              >
                <td className="detection-details__cell-ktp">
                  {KTP_DISPLAY_NAMES[key] ?? key}
                </td>
                <td className="detection-details__cell-mono">
                  {frame ?? '\u2014'}
                </td>
                <td className="detection-details__cell-mono">
                  {timestamp != null ? `${timestamp.toFixed(2)}s` : '\u2014'}
                </td>
                <td className="detection-details__cell-method">
                  {formatMethod(ktp.method)}
                </td>
                <td className="detection-details__cell-details">
                  {formatKTPDetails(key, ktp as Record<string, unknown>)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  FeatureChartsSection                                               */
/* ------------------------------------------------------------------ */

interface FeatureChartsSectionProps {
  detectionMeta: DetectionMeta;
  currentTime: number;
  serveStart: number;
  contactTimestamp: number | null;
  onSeek: (t: number) => void;
  loopPhaseWindow?: PhaseWindow | null;
}

export const FeatureChartsSection: React.FC<FeatureChartsSectionProps> = ({
  detectionMeta,
  currentTime,
  serveStart,
  contactTimestamp,
  onSeek,
  loopPhaseWindow,
}) => {
  const { fps, total_frames } = useDetectionHelpers(detectionMeta, serveStart);
  const { feature_curves } = detectionMeta;

  const frameRange = useMemo<[number, number] | null>(() => {
    if (!loopPhaseWindow || fps <= 0) return null;
    const start = Math.max(
      0,
      Math.round((loopPhaseWindow.start_timestamp - serveStart) * fps)
    );
    const end = Math.min(
      total_frames - 1,
      Math.round((loopPhaseWindow.end_timestamp - serveStart) * fps)
    );
    return [start, end];
  }, [loopPhaseWindow, fps, serveStart, total_frames]);

  const currentFrame = useMemo(() => {
    if (fps <= 0) return null;
    const frame = Math.round((currentTime - serveStart) * fps);
    if (frame < 0 || frame >= total_frames) return null;
    return frame;
  }, [currentTime, serveStart, fps, total_frames]);

  const contactFrame = useMemo(() => {
    if (contactTimestamp === null || fps <= 0) return null;
    const frame = Math.round((contactTimestamp - serveStart) * fps);
    if (frame < 0 || frame >= total_frames) return null;
    return frame;
  }, [contactTimestamp, serveStart, fps, total_frames]);

  // When looping, only show contact marker if it falls within the looped range.
  const visibleContactFrame = useMemo(() => {
    if (contactFrame === null || frameRange === null) return contactFrame;
    return contactFrame >= frameRange[0] && contactFrame <= frameRange[1]
      ? contactFrame
      : null;
  }, [contactFrame, frameRange]);

  const showContactFooter =
    contactTimestamp !== null && visibleContactFrame !== null;

  const handleFrameClick = useCallback(
    (frame: number) => {
      if (fps <= 0) return;
      onSeek(serveStart + frame / fps);
    },
    [fps, serveStart, onSeek]
  );

  return (
    <div className="detection-details__section">
      <FeatureChart
        data={feature_curves.max_wrist_height}
        label="Higher Wrist Height"
        fps={fps}
        contactFrame={visibleContactFrame}
        currentFrame={currentFrame}
        color="var(--color-court-blue-light)"
        onFrameClick={handleFrameClick}
        frameRange={frameRange}
      />
      <hr className="detection-details__separator" />
      <FeatureChart
        data={feature_curves.knee_hip_ratio.map((v) => -v)}
        label="Knee Bend"
        hint="higher = deeper bend"
        fps={fps}
        contactFrame={visibleContactFrame}
        currentFrame={currentFrame}
        color="var(--color-court-clay)"
        onFrameClick={handleFrameClick}
        frameRange={frameRange}
      />
      <hr className="detection-details__separator" />
      <FeatureChart
        data={feature_curves.max_wrist_velocity}
        label="Faster Wrist Speed"
        fps={fps}
        contactFrame={visibleContactFrame}
        currentFrame={currentFrame}
        color="var(--color-primary-dark)"
        onFrameClick={handleFrameClick}
        frameRange={frameRange}
      />
      {showContactFooter && (
        <div className="detection-details__contact-footer">
          <svg
            className="detection-details__legend-diamond"
            width="10"
            height="10"
            viewBox="-6 -6 12 12"
          >
            <polygon
              points="0,-5 5,0 0,5 -5,0"
              fill="#f5a623"
              stroke="white"
              strokeWidth="1.5"
            />
          </svg>
          <span className="detection-details__legend-label">Ball contact</span>
          <span className="detection-details__contact-current">
            {contactTimestamp!.toFixed(2)}s
          </span>
        </div>
      )}
    </div>
  );
};
