import React, { useMemo } from 'react';
import { useServeAttempts } from '../hooks/useServeAttempts';
import { formatTime } from '../utils/validation';
import './AnalysisRightPanel.css';
import LoadingIndicator from './LoadingIndicator';

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

  const sortedServeAttempts = useMemo(() => {
    return serveAttempts.sort((a, b) => a.start_timestamp - b.start_timestamp);
  }, [serveAttempts]);

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
      <div className="analysis-right-panel__card">
        <div className="analysis-right-panel__trajectory-header">
          <div className="analysis-right-panel__trajectory-title-group">
            <h3 className="analysis-right-panel__card-title">
              Key Moments ({sortedServeAttempts.length})
            </h3>
          </div>
        </div>
        <div className="analysis-right-panel__metrics-list">
          {sortedServeAttempts.length > 0 ? (
            sortedServeAttempts.map((serveAttempt) => {
              const displayLabel = serveAttempt.serve_subtype
                ? serveAttempt.serve_subtype.charAt(0).toUpperCase() +
                  serveAttempt.serve_subtype.slice(1)
                : serveAttempt.court_side
                  ? `${serveAttempt.court_side.charAt(0).toUpperCase() + serveAttempt.court_side.slice(1)} Court`
                  : 'Serve';

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
                </div>
              );
            })
          ) : (
            <div className="analysis-right-panel__metrics-empty">
              <p>No key moments tagged yet</p>
              <p className="analysis-right-panel__metrics-hint">
                Tag key moments and select a serve to view biomechanics
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ServeAttemptsPanel;
