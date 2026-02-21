import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useServeBiomechanicsReport } from '../hooks/useServeBiomechanicsReport';
import { MetricValue, PhaseWindow } from '../types/biomechanics';
import LoadingIndicator from './LoadingIndicator';
import ServePhaseTimeline from './ServePhaseTimeline';
import StickFigureCanvas from './StickFigureCanvas';
import './ServeBiomechanicsDetail.css';

interface ServeBiomechanicsDetailProps {
  serveWindowId: number;
  videoId: number;
  serveStart: number;
  serveEnd: number;
  contactTimestamp: number | null;
  onClose: () => void;
}

const METRIC_DISPLAY_NAMES: Record<string, string> = {
  knee_flexion_min_deg: 'Knee Flexion',
  toss_peak_height: 'Toss Peak Height',
  toss_laterality: 'Toss Position',
};

function findCurrentPhase(
  phases: PhaseWindow[],
  time: number
): PhaseWindow | undefined {
  return phases.find(
    (p) => time >= p.start_timestamp && time <= p.end_timestamp
  );
}

function formatMetricValue(metric: MetricValue): string {
  if (metric.value === null) return 'N/A';
  if (metric.unit === 'deg' || metric.unit === 'degrees')
    return `${Math.round(metric.value)}\u00b0`;
  if (metric.unit === 'normalized') return metric.value.toFixed(2);
  if (metric.unit === 'ms') return `${metric.value} ms`;
  if (typeof metric.value === 'number' && Number.isInteger(metric.value))
    return String(metric.value);
  if (typeof metric.value === 'number') return metric.value.toFixed(2);
  return String(metric.value);
}

/** Group metrics by phase for collapsible sections. */
function groupMetricsByPhase(
  metrics: MetricValue[]
): Map<string | null, MetricValue[]> {
  const map = new Map<string | null, MetricValue[]>();
  for (const m of metrics) {
    const key = m.phase ?? null;
    const list = map.get(key) ?? [];
    list.push(m);
    map.set(key, list);
  }
  return map;
}

interface MetricsByPhasePanelProps {
  metrics: MetricValue[];
}

const MetricsByPhasePanel: React.FC<MetricsByPhasePanelProps> = ({
  metrics,
}) => {
  const grouped = useMemo(() => groupMetricsByPhase(metrics), [metrics]);
  const [expandedPhases, setExpandedPhases] = useState<Set<string | null>>(
    () => new Set()
  );

  const toggle = (key: string | null) => {
    setExpandedPhases((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const phaseOrder = [
    'start',
    'release',
    'loading',
    'cocking',
    'acceleration',
    'contact',
    'deceleration',
    'finish',
    null,
  ];
  const phaseLabelMap: Record<string, string> = {
    start: 'Start',
    release: 'Release',
    loading: 'Loading',
    cocking: 'Cocking',
    acceleration: 'Acceleration',
    contact: 'Contact',
    deceleration: 'Deceleration',
    finish: 'Finish',
  };
  const sortedKeys = phaseOrder.filter((k) => grouped.has(k));

  return (
    <div className="serve-biomechanics-detail__metrics-panel">
      <h4 className="serve-biomechanics-detail__metrics-title">
        Metrics by Phase
      </h4>
      <div className="serve-biomechanics-detail__metrics-groups">
        {sortedKeys.map((phaseKey) => {
          const list = grouped.get(phaseKey) ?? [];
          const label =
            phaseKey === null
              ? 'Unassigned'
              : (phaseLabelMap[phaseKey] ??
                phaseKey
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, (c) => c.toUpperCase()));
          const isExpanded = expandedPhases.has(phaseKey);

          return (
            <div
              key={phaseKey ?? 'null'}
              className="serve-biomechanics-detail__phase-group"
            >
              <button
                type="button"
                className="serve-biomechanics-detail__phase-group-header"
                onClick={() => toggle(phaseKey)}
                aria-expanded={isExpanded}
              >
                <span className="serve-biomechanics-detail__phase-group-heading">
                  <span className="serve-biomechanics-detail__phase-group-label">
                    {label}
                  </span>
                  {!isExpanded && list.length > 0 && (
                    <span className="serve-biomechanics-detail__phase-group-summary">
                      {METRIC_DISPLAY_NAMES[list[0].metric_name] ??
                        list[0].metric_name.replace(/_/g, ' ')}
                      : {formatMetricValue(list[0])}
                    </span>
                  )}
                </span>
                <span
                  className="serve-biomechanics-detail__phase-group-chevron"
                  data-expanded={isExpanded}
                  aria-hidden
                >
                  &#9662;
                </span>
              </button>
              {isExpanded && (
                <div className="serve-biomechanics-detail__phase-group-body">
                  <table className="serve-biomechanics-detail__metrics-table">
                    <thead>
                      <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Unit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.map((m) => (
                        <tr key={m.metric_name}>
                          <td>
                            {METRIC_DISPLAY_NAMES[m.metric_name] ??
                              m.metric_name.replace(/_/g, ' ')}
                          </td>
                          <td>{formatMetricValue(m)}</td>
                          <td>{m.unit || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const NEUTRAL_SKELETON_COLOR = '#00ff88';

const ServeBiomechanicsDetail: React.FC<ServeBiomechanicsDetailProps> = ({
  serveWindowId,
  videoId,
  serveStart,
  serveEnd,
  contactTimestamp,
  onClose,
}) => {
  const {
    data: report,
    isLoading,
    error,
  } = useServeBiomechanicsReport(serveWindowId);
  const [currentTime, setCurrentTime] = useState(serveStart);
  const [isPlaying, setIsPlaying] = useState(false);
  const playIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!isPlaying) {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
        playIntervalRef.current = null;
      }
      return;
    }

    playIntervalRef.current = setInterval(() => {
      setCurrentTime((t) => {
        const next = t + 1 / 30;
        if (next > serveEnd) {
          setIsPlaying(false);
          return serveStart;
        }
        return next;
      });
    }, 1000 / 30);

    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    };
  }, [isPlaying, serveStart, serveEnd]);

  const handleSeek = useCallback(
    (t: number) => {
      setCurrentTime(Math.max(serveStart, Math.min(serveEnd, t)));
    },
    [serveStart, serveEnd]
  );

  const handlePlayPause = useCallback(() => {
    setIsPlaying((p) => !p);
  }, []);

  const handleJumpToContact = useCallback(() => {
    if (contactTimestamp !== null) {
      setCurrentTime(contactTimestamp);
      setIsPlaying(false);
    }
  }, [contactTimestamp]);

  const phases = report?.phase_segmentation ?? [];
  const currentPhase = findCurrentPhase(phases, currentTime);

  if (isLoading) {
    return (
      <div className="serve-biomechanics-detail serve-biomechanics-detail--loading">
        <LoadingIndicator size="md" label="Computing biomechanics..." />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="serve-biomechanics-detail serve-biomechanics-detail--error">
        <p>Could not load biomechanics for this serve.</p>
        <button
          className="serve-biomechanics-detail__close-btn"
          onClick={onClose}
        >
          Dismiss
        </button>
      </div>
    );
  }

  return (
    <div className="serve-biomechanics-detail">
      <div className="serve-biomechanics-detail__header">
        <div className="serve-biomechanics-detail__title-row">
          <h3 className="serve-biomechanics-detail__title">
            Serve Biomechanics
          </h3>
        </div>
        <button
          className="serve-biomechanics-detail__close-btn"
          onClick={onClose}
          aria-label="Close biomechanics detail"
        >
          &times;
        </button>
      </div>

      <div className="serve-biomechanics-detail__content">
        <div className="serve-biomechanics-detail__silhouette">
          <div className="serve-biomechanics-detail__canvas-wrapper">
            <StickFigureCanvas
              videoId={videoId}
              currentTime={currentTime}
              isPlaying={isPlaying}
              phaseColor={NEUTRAL_SKELETON_COLOR}
              phaseLabel={currentPhase?.phase_label}
            />
          </div>

          <ServePhaseTimeline
            phases={phases}
            currentTime={currentTime}
            serveStart={serveStart}
            serveEnd={serveEnd}
            onSeek={handleSeek}
          />

          <div className="serve-biomechanics-detail__controls">
            <button
              className="serve-biomechanics-detail__play-btn"
              onClick={handlePlayPause}
            >
              {isPlaying ? 'Pause' : 'Play'}
            </button>
            {contactTimestamp !== null && (
              <button
                className="serve-biomechanics-detail__jump-btn"
                onClick={handleJumpToContact}
              >
                Jump to Contact
              </button>
            )}
          </div>
        </div>

        <div className="serve-biomechanics-detail__metrics-scroll">
          <MetricsByPhasePanel metrics={report.metrics} />
        </div>
      </div>
      <div className="serve-biomechanics-detail__footer">
        <button
          type="button"
          className="serve-biomechanics-detail__back-btn"
          onClick={onClose}
        >
          Back to Serves
        </button>
      </div>
    </div>
  );
};

export default ServeBiomechanicsDetail;
