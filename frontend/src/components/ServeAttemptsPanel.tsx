import React, { useMemo } from 'react';
import { useServeAttempts } from '../hooks/useServeAttempts';
import { formatTime } from '../utils/validation';
import './AnalysisRightPanel.css'; // Reuse styles

interface ServeAttemptsPanelProps {
  videoId: number;
  onServeAttemptClick?: (serveAttemptId: number) => void;
  isDemo?: boolean;
}

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

  const serveAttemptsWithMetrics = useMemo(() => {
    return serveAttempts
      .filter((sa) => sa.elbow_angle_at_contact !== null)
      .sort((a, b) => a.start_timestamp - b.start_timestamp);
  }, [serveAttempts]);

  const allServeAttempts = useMemo(() => {
    return serveAttempts.sort((a, b) => a.start_timestamp - b.start_timestamp);
  }, [serveAttempts]);

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
      {/* Serve Attempts with Metrics Card */}
      {serveAttemptsWithMetrics.length > 0 && (
        <div className="analysis-right-panel__card">
          <div className="analysis-right-panel__trajectory-header">
            <div className="analysis-right-panel__trajectory-title-group">
              <h3 className="analysis-right-panel__card-title">
                Serve Analysis
              </h3>
            </div>
          </div>
          <div className="analysis-right-panel__metrics-list">
            {serveAttemptsWithMetrics.map((serveAttempt) => {
              const angle = serveAttempt.elbow_angle_at_contact;
              const displayLabel = serveAttempt.serve_subtype
                ? serveAttempt.serve_subtype.charAt(0).toUpperCase() +
                  serveAttempt.serve_subtype.slice(1)
                : serveAttempt.court_side
                  ? `${serveAttempt.court_side.charAt(0).toUpperCase() + serveAttempt.court_side.slice(1)} Court`
                  : 'Serve';

              return (
                <div
                  key={serveAttempt.id}
                  className="analysis-right-panel__metric-item"
                  onClick={() => onServeAttemptClick?.(serveAttempt.id)}
                  style={{ cursor: onServeAttemptClick ? 'pointer' : 'default' }}
                >
                  <div className="analysis-right-panel__metric-header">
                    <div className="analysis-right-panel__metric-dot" />
                    <div className="analysis-right-panel__metric-time">
                      {formatTime(serveAttempt.contact_timestamp || serveAttempt.start_timestamp)}
                    </div>
                    <div className="analysis-right-panel__metric-stroke">
                      {displayLabel}
                    </div>
                  </div>
                  <div className="analysis-right-panel__metric-angle">
                    <span className="analysis-right-panel__angle-value">
                      {Math.round(angle as number)}°
                    </span>
                    <span className="analysis-right-panel__angle-label">
                      Elbow Angle
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* All Serve Attempts List */}
      <div className="analysis-right-panel__card">
        <div className="analysis-right-panel__trajectory-header">
          <div className="analysis-right-panel__trajectory-title-group">
            <h3 className="analysis-right-panel__card-title">
              Serve Attempts ({allServeAttempts.length})
            </h3>
          </div>
        </div>
        <div className="analysis-right-panel__metrics-list">
          {allServeAttempts.length > 0 ? (
            allServeAttempts.map((serveAttempt) => {
              const hasMetrics = serveAttempt.elbow_angle_at_contact !== null;
              const displayLabel = serveAttempt.serve_subtype
                ? serveAttempt.serve_subtype.charAt(0).toUpperCase() +
                  serveAttempt.serve_subtype.slice(1)
                : serveAttempt.court_side
                  ? `${serveAttempt.court_side.charAt(0).toUpperCase() + serveAttempt.court_side.slice(1)} Court`
                  : 'Serve';

              return (
                <div
                  key={serveAttempt.id}
                  className="analysis-right-panel__metric-item"
                  onClick={() => onServeAttemptClick?.(serveAttempt.id)}
                  style={{ cursor: onServeAttemptClick ? 'pointer' : 'default' }}
                >
                  <div className="analysis-right-panel__metric-header">
                    <div className="analysis-right-panel__metric-dot" />
                    <div className="analysis-right-panel__metric-time">
                      {formatTime(serveAttempt.start_timestamp)} - {formatTime(serveAttempt.end_timestamp)}
                    </div>
                    <div className="analysis-right-panel__metric-stroke">
                      {displayLabel}
                    </div>
                  </div>
                  {hasMetrics ? (
                    <div className="analysis-right-panel__metric-angle">
                      <span className="analysis-right-panel__angle-value">
                        {Math.round(serveAttempt.elbow_angle_at_contact as number)}°
                      </span>
                      <span className="analysis-right-panel__angle-label">
                        Elbow Angle
                      </span>
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
