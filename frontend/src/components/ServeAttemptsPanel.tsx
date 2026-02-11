import React, { useMemo } from 'react';
import { useServeAttempts } from '../hooks/useServeAttempts';
import { formatTime } from '../utils/validation';
import './AnalysisRightPanel.css'; // Reuse styles
import LoadingIndicator from './LoadingIndicator';

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

interface KneeBendFeedback {
  level: 'great' | 'solid' | 'focus' | 'unavailable';
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

/**
 * Maps knee bend detection and confidence to feedback level, pill text, and coach note.
 * Frontend-only heuristic for MVP - will be replaced with LLM-based recommendations.
 */
const getKneeBendFeedback = (
  detected: boolean | null,
  confidence: number | null
): KneeBendFeedback => {
  if (detected === null || confidence === null) {
    return {
      level: 'unavailable',
      pillText: 'Not Available',
      coachNote:
        'Knee bend analysis not available. May need better camera angle or pose data.',
    };
  }

  if (confidence < 0.5) {
    return {
      level: 'unavailable',
      pillText: 'Low Confidence',
      coachNote:
        'Knee bend detected but confidence is low. Camera angle or pose quality may be limiting.',
    };
  }

  if (detected) {
    return {
      level: 'great',
      pillText: 'Good Bend',
      coachNote:
        'Good knee bend during loading phase. This helps generate power.',
    };
  }

  return {
    level: 'focus',
    pillText: 'Needs Work',
    coachNote:
      'Limited knee bend detected. Try bending knees more during the loading phase for better power.',
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
      (sa) =>
        sa.elbow_angle_at_contact !== null || sa.knee_bend_detected !== null
    );
  }, [sortedServeAttempts]);

  if (loading) {
    return (
      <div className="analysis-right-panel">
        <div className="analysis-right-panel__card">
          <LoadingIndicator size="md" label="Loading key moments..." />
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
              Key Moments ({sortedServeAttempts.length})
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
              const hasElbowMetrics =
                serveAttempt.elbow_angle_at_contact !== null;
              const hasKneeMetrics = serveAttempt.knee_bend_detected !== null;
              const hasMetrics = hasElbowMetrics || hasKneeMetrics;

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
                    <div className="analysis-right-panel__metrics-group">
                      {/* Elbow Angle Metric */}
                      {hasElbowMetrics && (
                        <div className="analysis-right-panel__metric-section">
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
                              className={`analysis-right-panel__feedback-pill analysis-right-panel__feedback-pill--${getElbowAngleFeedback(serveAttempt.elbow_angle_at_contact as number).level}`}
                            >
                              {
                                getElbowAngleFeedback(
                                  serveAttempt.elbow_angle_at_contact as number
                                ).pillText
                              }
                            </span>
                          </div>
                          <div className="analysis-right-panel__coach-note">
                            {
                              getElbowAngleFeedback(
                                serveAttempt.elbow_angle_at_contact as number
                              ).coachNote
                            }
                          </div>
                        </div>
                      )}

                      {/* Knee Bend Metric */}
                      {hasKneeMetrics && (
                        <div className="analysis-right-panel__metric-section">
                          <div className="analysis-right-panel__metric-angle">
                            <div className="analysis-right-panel__metric-angle-main">
                              <span className="analysis-right-panel__angle-value">
                                {serveAttempt.knee_bend_detected
                                  ? '✓'
                                  : serveAttempt.knee_bend_confidence !==
                                        null &&
                                      serveAttempt.knee_bend_confidence < 0.5
                                    ? '?'
                                    : '✗'}
                              </span>
                              <span className="analysis-right-panel__angle-label">
                                Knee Bend
                                {serveAttempt.knee_bend_confidence !== null &&
                                  ` (${Math.round(
                                    serveAttempt.knee_bend_confidence * 100
                                  )}%)`}
                              </span>
                            </div>
                            <span
                              className={`analysis-right-panel__feedback-pill analysis-right-panel__feedback-pill--${getKneeBendFeedback(serveAttempt.knee_bend_detected, serveAttempt.knee_bend_confidence).level}`}
                            >
                              {
                                getKneeBendFeedback(
                                  serveAttempt.knee_bend_detected,
                                  serveAttempt.knee_bend_confidence
                                ).pillText
                              }
                            </span>
                          </div>
                          <div className="analysis-right-panel__coach-note">
                            {
                              getKneeBendFeedback(
                                serveAttempt.knee_bend_detected,
                                serveAttempt.knee_bend_confidence
                              ).coachNote
                            }
                          </div>
                        </div>
                      )}
                    </div>
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
              <p>No key moments tagged yet</p>
              <p className="analysis-right-panel__metrics-hint">
                Tag key moments and run analysis to see metrics
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ServeAttemptsPanel;
