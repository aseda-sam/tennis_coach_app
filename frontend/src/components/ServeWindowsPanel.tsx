import React, { useMemo } from 'react';
import { useServeWindows } from '../hooks/useServeWindows';
import {
  useStartBallDetection,
  useVideoAnalysisStatus,
} from '../hooks/useVideos';
import { getApiErrorMessage } from '../utils/apiError';
import { formatTime } from '../utils/validation';
import './AnalysisRightPanel.css';
import LoadingIndicator from './LoadingIndicator';

interface ServeWindowsPanelProps {
  videoId: number;
  onServeWindowClick?: (serveWindowId: number) => void;
  isDemo?: boolean;
}

const ServeWindowsPanel: React.FC<ServeWindowsPanelProps> = ({
  videoId,
  onServeWindowClick,
  isDemo = false,
}) => {
  const { serveWindows, loading, error } = useServeWindows({
    videoId,
    filters: { video_id: videoId },
    autoRefresh: true,
  });
  const { data: analysisStatus } = useVideoAnalysisStatus(videoId);
  const startBallDetection = useStartBallDetection();
  const isStale = !!analysisStatus?.is_ball_detection_stale;
  const isRunning =
    startBallDetection.isPending ||
    analysisStatus?.ball_detection_status === 'processing' ||
    analysisStatus?.ball_detection_status === 'queued';

  const sortedServeWindows = useMemo(() => {
    return serveWindows.sort((a, b) => a.start_timestamp - b.start_timestamp);
  }, [serveWindows]);

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
              Key Moments ({sortedServeWindows.length})
            </h3>
            {analysisStatus?.has_ball_detection &&
              analysisStatus.ball_detection_rate !== null && (
                <span
                  className="analysis-right-panel__ball-detection-badge"
                  title={`Ball detected in ${Math.round(analysisStatus.ball_detection_rate * 100)}% of frames`}
                >
                  <span
                    className="analysis-right-panel__ball-detection-dot"
                    style={{
                      backgroundColor:
                        analysisStatus.ball_detection_rate >= 0.5
                          ? 'var(--color-success)'
                          : analysisStatus.ball_detection_rate >= 0.25
                            ? 'var(--color-warning)'
                            : 'var(--color-error)',
                    }}
                  />
                  Ball tracking{' '}
                  {Math.round(analysisStatus.ball_detection_rate * 100)}%
                </span>
              )}
            {!isDemo && isStale && (
              <span
                className="analysis-right-panel__ball-detection-stale"
                title="Serve windows have changed since the last ball detection run"
              >
                Stale
              </span>
            )}
            {!isDemo && (
              <button
                type="button"
                className="analysis-right-panel__ball-detection-rerun"
                disabled={isRunning || sortedServeWindows.length === 0}
                onClick={() => startBallDetection.mutate(videoId)}
              >
                {isRunning
                  ? 'Running…'
                  : analysisStatus?.has_ball_detection
                    ? 'Re-run ball detection'
                    : 'Run ball detection'}
              </button>
            )}
          </div>
        </div>
        {startBallDetection.isError && (
          <p className="analysis-right-panel__ball-detection-error">
            {getApiErrorMessage(
              startBallDetection.error,
              'Failed to start ball detection'
            )}
          </p>
        )}
        <div className="analysis-right-panel__metrics-list">
          {sortedServeWindows.length > 0 ? (
            sortedServeWindows.map((serveWindow) => {
              const displayLabel = serveWindow.serve_subtype
                ? serveWindow.serve_subtype.charAt(0).toUpperCase() +
                  serveWindow.serve_subtype.slice(1)
                : serveWindow.court_side
                  ? `${serveWindow.court_side.charAt(0).toUpperCase() + serveWindow.court_side.slice(1)} Court`
                  : 'Serve';

              const timeDisplay =
                serveWindow.contact_timestamp !== null
                  ? formatTime(serveWindow.contact_timestamp)
                  : `${formatTime(serveWindow.start_timestamp)} - ${formatTime(serveWindow.end_timestamp)}`;

              return (
                <div
                  key={serveWindow.id}
                  className="analysis-right-panel__metric-item"
                  onClick={() => onServeWindowClick?.(serveWindow.id)}
                  style={{
                    cursor: onServeWindowClick ? 'pointer' : 'default',
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

export default ServeWindowsPanel;
