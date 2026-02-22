import React, { useMemo, useState } from 'react';
import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from 'recharts';
import { DetectionMeta } from '../types/biomechanics';
import './DetectionDetailsPanel.css';

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
  fps: number;
  ktpFrames: { frame: number; label: string }[];
  currentFrame: number | null;
  color: string;
}

const FeatureChart: React.FC<FeatureChartProps> = ({
  data,
  label,
  fps,
  ktpFrames,
  currentFrame,
  color,
}) => {
  const chartData = useMemo(
    () => data.map((value, i) => ({ frame: i, value })),
    [data]
  );

  return (
    <div className="detection-details__chart">
      <span className="detection-details__chart-label">{label}</span>
      <ResponsiveContainer width="100%" height={100}>
        <LineChart
          data={chartData}
          margin={{ top: 4, right: 4, bottom: 4, left: 4 }}
        >
          <XAxis dataKey="frame" hide />
          <YAxis hide domain={['auto', 'auto']} />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          {ktpFrames.map(({ frame, label: ktpLabel }) => (
            <ReferenceLine
              key={ktpLabel}
              x={frame}
              stroke="var(--color-court-blue)"
              strokeWidth={1}
              strokeDasharray="3 3"
            />
          ))}
          {currentFrame !== null && (
            <ReferenceLine
              x={currentFrame}
              stroke="var(--color-text)"
              strokeWidth={1.5}
              strokeOpacity={0.6}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

interface DetectionDetailsPanelProps {
  detectionMeta: DetectionMeta;
  currentTime: number;
  serveStart: number;
  onSeek: (t: number) => void;
}

const DetectionDetailsPanel: React.FC<DetectionDetailsPanelProps> = ({
  detectionMeta,
  currentTime,
  serveStart,
  onSeek,
}) => {
  const [expanded, setExpanded] = useState(false);

  const { ktps, feature_curves, fps, total_frames } = detectionMeta;

  const currentFrame = useMemo(() => {
    if (fps <= 0) return null;
    const frame = Math.round((currentTime - serveStart) * fps);
    if (frame < 0 || frame >= total_frames) return null;
    return frame;
  }, [currentTime, serveStart, fps, total_frames]);

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

  const handleRowClick = (frame: number | null) => {
    if (frame == null || fps <= 0) return;
    const timestamp = serveStart + frame / fps;
    onSeek(timestamp);
  };

  return (
    <div className="detection-details">
      <button
        type="button"
        className="detection-details__toggle"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <svg
          className={`detection-details__chevron${expanded ? ' detection-details__chevron--open' : ''}`}
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
        >
          <path
            d="M6 4l4 4-4 4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span className="detection-details__toggle-label">
          Detection Details
        </span>
      </button>

      {expanded && (
        <div className="detection-details__content">
          {/* KTP Summary Table */}
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
                        {timestamp != null
                          ? `${timestamp.toFixed(2)}s`
                          : '\u2014'}
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

          {/* Feature Curves */}
          <div className="detection-details__section">
            <FeatureChart
              data={feature_curves.max_wrist_height}
              label="Wrist Height"
              fps={fps}
              ktpFrames={ktpFrameMarkers}
              currentFrame={currentFrame}
              color="var(--color-court-blue-light)"
            />
            <FeatureChart
              data={feature_curves.knee_hip_ratio}
              label="Knee Bend"
              fps={fps}
              ktpFrames={ktpFrameMarkers.filter(
                (m) => m.label === 'Trophy Position'
              )}
              currentFrame={currentFrame}
              color="var(--color-court-clay)"
            />
            <FeatureChart
              data={feature_curves.max_wrist_velocity}
              label="Wrist Velocity"
              fps={fps}
              ktpFrames={ktpFrameMarkers.filter(
                (m) => m.label === 'Ball Impact'
              )}
              currentFrame={currentFrame}
              color="var(--color-primary-dark)"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default DetectionDetailsPanel;
