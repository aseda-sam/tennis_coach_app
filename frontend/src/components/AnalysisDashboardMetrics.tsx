import React from 'react';
import { MetricValue, PhaseWindow } from '../types/biomechanics';
import { ServeWindow } from '../types/serveWindow';
import './AnalysisDashboard.css';
import ServePhaseTimeline from './ServePhaseTimeline';

const METRIC_DISPLAY_NAMES: Record<string, string> = {
  knee_flexion_min_deg: 'Knee Flexion',
  toss_peak_height: 'Toss Peak Height',
  toss_laterality: 'Toss Position',
};

function formatMetricValue(value: number | null, unit: string): string {
  if (value === null) return 'N/A';
  if (unit === 'deg' || unit === 'degrees') return `${Math.round(value)}\u00b0`;
  if (unit === 'normalized') return value.toFixed(2);
  if (unit === 'ms') return `${value} ms`;
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(2);
}

interface AnalysisDashboardMetricsProps {
  currentServe: ServeWindow;
  phases: PhaseWindow[];
  currentPhase: PhaseWindow | undefined;
  metrics: MetricValue[];
  filteredMetrics: MetricValue[];
  currentTime: number;
  loopCurrentPhase: boolean;
  onSeek: (t: number) => void;
  onPhaseJump: (phase: PhaseWindow) => void;
  onContactJump: (contactTimestamp: number) => void;
  onToggleLoopCurrentPhase: () => void;
  onMetricClick?: (metric: MetricValue) => void;
}

const AnalysisDashboardMetrics: React.FC<AnalysisDashboardMetricsProps> = ({
  currentServe,
  phases,
  currentPhase,
  metrics,
  filteredMetrics,
  currentTime,
  loopCurrentPhase,
  onSeek,
  onPhaseJump,
  onContactJump,
  onToggleLoopCurrentPhase,
  onMetricClick,
}) => {
  return (
    <div className="analysis-dashboard__right-panel">
      {phases.length > 0 && (
        <div className="analysis-dashboard__timeline-wrapper">
          <ServePhaseTimeline
            phases={phases}
            currentTime={currentTime}
            serveStart={currentServe.start_timestamp}
            serveEnd={currentServe.end_timestamp}
            onSeek={onSeek}
            contactTimestamp={currentServe.contact_timestamp ?? null}
          />
        </div>
      )}

      {phases.length > 0 && (
        <div className="analysis-dashboard__phase-controls">
          <div className="analysis-dashboard__phase-chip-row">
            {phases.map((phase) => (
              <button
                key={phase.phase}
                type="button"
                className={`analysis-dashboard__phase-chip ${
                  currentPhase?.phase === phase.phase
                    ? 'analysis-dashboard__phase-chip--active'
                    : ''
                }`}
                onClick={() => onPhaseJump(phase)}
              >
                {phase.phase_label}
              </button>
            ))}
          </div>
          <div className="analysis-dashboard__phase-actions">
            {currentServe.contact_timestamp != null && (
              <button
                type="button"
                className="analysis-dashboard__goto-contact-btn"
                onClick={() => onContactJump(currentServe.contact_timestamp!)}
              >
                Go to Contact
              </button>
            )}
            <button
              type="button"
              className={`analysis-dashboard__loop-btn ${
                loopCurrentPhase ? 'analysis-dashboard__loop-btn--active' : ''
              }`}
              onClick={onToggleLoopCurrentPhase}
              disabled={!currentPhase}
            >
              {loopCurrentPhase
                ? 'Looping Current Stage'
                : 'Loop Current Stage'}
            </button>
          </div>
        </div>
      )}

      {/* Metrics Strip -- filtered by active phase */}
      {metrics.length > 0 && (
        <div className="analysis-dashboard__metrics-strip">
          {filteredMetrics.length > 0 ? (
            filteredMetrics.map((m) => {
              const isClickable =
                m.timestamp != null && m.value != null && onMetricClick;
              return (
                <div
                  key={m.metric_name}
                  className={`analysis-dashboard__metric-card${isClickable ? ' analysis-dashboard__metric-card--clickable' : ''}`}
                  onClick={isClickable ? () => onMetricClick(m) : undefined}
                  role={isClickable ? 'button' : undefined}
                  tabIndex={isClickable ? 0 : undefined}
                  onKeyDown={
                    isClickable
                      ? (e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            onMetricClick(m);
                          }
                        }
                      : undefined
                  }
                >
                  <span className="analysis-dashboard__metric-label">
                    {METRIC_DISPLAY_NAMES[m.metric_name] ??
                      m.metric_name.replace(/_/g, ' ')}
                  </span>
                  <span className="analysis-dashboard__metric-value">
                    {formatMetricValue(m.value, m.unit)}
                  </span>
                </div>
              );
            })
          ) : (
            <p className="analysis-dashboard__metrics-empty">
              No metrics for this phase
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalysisDashboardMetrics;
