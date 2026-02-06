import React, { useMemo } from 'react';
import { useServeAttempts } from '../hooks/useServeAttempts';
import { formatTime } from '../utils/validation';
import './AnalysisRightPanel.css'; // Reuse styles

interface ServeAttemptsPanelProps {
  videoId: number;
  onServeAttemptClick?: (serveAttemptId: number) => void;
  isDemo?: boolean;
}

interface ElbowAngleFeedback {
  level: 'great' | 'solid' | 'focus';
  pillText: string;
  coachNote: string;
}

/**
 * Maps elbow angle (in degrees) to feedback level, pill text, and coach note.
 * Frontend-only heuristic for MVP - will be replaced with LLM-based recommendations.
 *
 * Based on tennis biomechanics: a slight bend is natural and allows for good
 * pronation. Only flag very bent arms (closer to 90°) as needing attention.
 */
const getElbowAngleFeedback = (angleDeg: number): ElbowAngleFeedback => {
  // Only flag if arm is very bent (closer to 90°)
  if (angleDeg < 120) {
    return {
      level: 'focus',
      pillText: 'Needs Work',
      coachNote: 'Arm is quite bent. Try reaching up more at contact.',
    };
  }
  // Everything else is fine - don't over-coach natural arm positions
  return {
    level: 'great',
    pillText: 'Good',
    coachNote: 'Good arm extension at contact.',
  };
};

const ServeAttemptsPanel: React.FC<ServeAttemptsPanelProps> = ({
  videoId,
  onServeAttemptClick,
  isDemo = false,
}) => {
  const { serveAttempts, loading, error } = useServeAttempts({
    videoId,
    filters: { video_id: videoId },
    autoRefresh: true,
  });

  const sortedServeAttempts = useMemo(() => {
    return serveAttempts.sort((a, b) => a.start_timestamp - b.start_timestamp);
  }, [serveAttempts]);

  const serveAttemptsWithMetrics = useMemo(() => {
    return sortedServeAttempts.filter(
      (sa) => sa.elbow_angle_at_contact !== null
    );
  }, [sortedServeAttempts]);

  if (loading) {
    return (
      <div className="analysis-right-panel">
        <div className="analysis-right-panel__card">
          <p>Loading serve attempts...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analysis-right-panel">
        <div className="analysis-right-panel__card">
          <p style={{ color: 'red' }}>Error: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="analysis-right-panel">
      {/* Single consolidated card showing all serve attempts */}
      <div className="analysis-right-panel__card">
        <div className="analysis-right-panel__trajectory-header">
          <div className="analysis-right-panel__trajectory-title-group">
            <h3 className="analysis-right-panel__card-title">
              Serve Attempts ({sortedServeAttempts.length})
            </h3>
            {serveAttemptsWithMetrics.length > 0 && (
              <p className="analysis-right-panel__card-subtitle">
                {serveAttemptsWithMetrics.length} with analysis
              </p>
            )}
          </div>
        </div>
        <div className="analysis-right-panel__metrics-list">
          {sortedServeAttempts.length > 0 ? (
            sortedServeAttempts.map((serveAttempt) => {
              const hasMetrics = serveAttempt.elbow_angle_at_contact !== null;
              const displayLabel = serveAttempt.serve_subtype
                ? serveAttempt.serve_subtype.charAt(0).toUpperCase() +
                  serveAttempt.serve_subtype.slice(1)
                : serveAttempt.court_side
                  ? `${serveAttempt.court_side.charAt(0).toUpperCase() + serveAttempt.court_side.slice(1)} Court`
                  : 'Serve';

              // Show contact timestamp if available, otherwise show range
              const timeDisplay =
                serveAttempt.contact_timestamp !== null
                  ? formatTime(serveAttempt.contact_timestamp)
                  : `${formatTime(serveAttempt.start_timestamp)} - ${formatTime(serveAttempt.end_timestamp)}`;

              return (
                <div
                  key={serveAttempt.id}
                  className="analysis-right-panel__metric-item"
                  onClick={() => onServeAttemptClick?.(serveAttempt.id)}
                  style={{
                    cursor: onServeAttemptClick ? 'pointer' : 'default',
                  }}
                >
                  <div className="analysis-right-panel__metric-header">
                    <div className="analysis-right-panel__metric-dot" />
                    <div className="analysis-right-panel__metric-time">
                      {timeDisplay}
                    </div>
                    <div className="analysis-right-panel__metric-stroke">
                      {displayLabel}
                    </div>
                  </div>
                  {hasMetrics ? (
                    (() => {
                      const feedback = getElbowAngleFeedback(
                        serveAttempt.elbow_angle_at_contact as number
                      );
                      return (
                        <>
                          <div className="analysis-right-panel__metric-angle">
                            <div className="analysis-right-panel__metric-angle-main">
                              <span className="analysis-right-panel__angle-value">
                                {Math.round(
                                  serveAttempt.elbow_angle_at_contact as number
                                )}
                                °
                              </span>
                              <span className="analysis-right-panel__angle-label">
                                Elbow Angle
                              </span>
                            </div>
                            <span
                              className={`analysis-right-panel__feedback-pill analysis-right-panel__feedback-pill--${feedback.level}`}
                            >
                              {feedback.pillText}
                            </span>
                          </div>
                          <div className="analysis-right-panel__coach-note">
                            {feedback.coachNote}
                          </div>
                        </>
                      );
                    })()
                  ) : (
                    <div className="analysis-right-panel__metric-angle">
                      <span className="analysis-right-panel__angle-label">
                        No metrics yet
                      </span>
                    </div>
                  )}
                </div>
              );
            })
          ) : (
            <div className="analysis-right-panel__metrics-empty">
              <p>No serve attempts tagged yet</p>
              <p className="analysis-right-panel__metrics-hint">
                Tag serve attempts and run analysis to see metrics
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ServeAttemptsPanel;
