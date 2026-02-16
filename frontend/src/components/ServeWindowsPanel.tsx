import React, { useMemo } from 'react';
import { useServeWindows } from '../hooks/useServeWindows';
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
          </div>
        </div>
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
