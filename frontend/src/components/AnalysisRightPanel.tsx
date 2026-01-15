import React, { useMemo } from 'react';
import { useBallContacts } from '../hooks/useBallContacts';
import { formatTime } from '../utils/validation';
import { STROKE_TYPE_LABELS } from '../constants/shotTypes';
import './AnalysisRightPanel.css';

interface AnalysisRightPanelProps {
  videoId: number;
  videoFilename: string;
  analysisStatus?: {
    has_analysis?: boolean;
  };
  onContactClick?: (contactId: number) => void; // Callback when contact is clicked
}

const AnalysisRightPanel: React.FC<AnalysisRightPanelProps> = ({
  videoId,
  videoFilename,
  analysisStatus,
  onContactClick,
}) => {
  const { contacts: ballContacts } = useBallContacts({
    videoId,
    autoRefresh: true,
  });

  const getAngleColor = (angle?: number): string => {
    if (angle === undefined || angle === null) return '#6b7280'; // gray-500
    if (angle < 90) return '#ef4444'; // red-500 - very bent
    if (angle < 120) return '#f59e0b'; // amber-500 - moderately bent
    if (angle < 150) return '#10b981'; // emerald-500 - good range
    return '#3b82f6'; // blue-500 - straight
  };

  const getAngleDescription = (angle?: number): string => {
    if (angle === undefined || angle === null) return 'Not analyzed';
    if (angle < 90) return 'Very bent';
    if (angle < 120) return 'Bent';
    if (angle < 150) return 'Good range';
    return 'Straight';
  };

  const contactsWithMetrics = useMemo(() => {
    return ballContacts
      .filter((contact) => contact.elbow_angle !== undefined)
      .sort((a, b) => a.video_timestamp - b.video_timestamp);
  }, [ballContacts]);

  return (
    <div className="analysis-right-panel">
      {/* Serve Info Card */}
      <div className="analysis-right-panel__card">
        <div className="analysis-right-panel__serve-info">
          <div className="analysis-right-panel__serve-badge">Serve 1</div>
          <div className="analysis-right-panel__serve-side">Deuce Side</div>
          <div className="analysis-right-panel__serve-status">
            <span className="analysis-right-panel__status-indicator"></span>
            <span>In</span>
          </div>
        </div>
      </div>

      {/* Elbow Angle Metrics Card */}
      {analysisStatus?.has_analysis && (
        <div className="analysis-right-panel__card">
          <div className="analysis-right-panel__trajectory-header">
            <div className="analysis-right-panel__trajectory-title-group">
              <h3 className="analysis-right-panel__card-title">
                Elbow Angle Metrics
              </h3>
            </div>
          </div>
          <div className="analysis-right-panel__metrics-list">
            {contactsWithMetrics.length > 0 ? (
              contactsWithMetrics.map((contact) => {
                const angle = contact.elbow_angle;
                const angleColor = getAngleColor(angle);
                const angleDesc = getAngleDescription(angle);
                const strokeTypeColor = (() => {
                  switch (contact.stroke_type?.toLowerCase()) {
                    case 'ground_stroke':
                      return '#10b981';
                    case 'serve':
                      return '#3b82f6';
                    case 'return':
                      return '#f59e0b';
                    case 'volley':
                      return '#a855f7';
                    case 'overhead':
                      return '#ef4444';
                    default:
                      return '#6b7280';
                  }
                })();

                return (
                  <div
                    key={contact.id}
                    className="analysis-right-panel__metric-item"
                    onClick={() => onContactClick?.(contact.id)}
                    style={{ cursor: onContactClick ? 'pointer' : 'default' }}
                  >
                    <div className="analysis-right-panel__metric-header">
                      <div
                        className="analysis-right-panel__metric-dot"
                        style={{ backgroundColor: strokeTypeColor }}
                      />
                      <div className="analysis-right-panel__metric-time">
                        {formatTime(contact.video_timestamp)}
                      </div>
                      <div className="analysis-right-panel__metric-stroke">
                        {contact.stroke_type
                          ? STROKE_TYPE_LABELS[contact.stroke_type] ||
                            contact.stroke_type
                          : 'Unknown'}
                      </div>
                    </div>
                    <div className="analysis-right-panel__metric-angle">
                      <span
                        className="analysis-right-panel__angle-value"
                        style={{ color: angleColor }}
                      >
                        {Math.round(angle || 0)}°
                      </span>
                      <span className="analysis-right-panel__angle-desc">
                        {angleDesc}
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="analysis-right-panel__metrics-empty">
                <p>No contact metrics available</p>
                <p className="analysis-right-panel__metrics-hint">
                  Add contacts and run pose analysis to see metrics
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Ball Toss Trajectory Card */}
      <div className="analysis-right-panel__card analysis-right-panel__card--coming-soon">
        <div className="analysis-right-panel__trajectory-header">
          <div className="analysis-right-panel__trajectory-title-group">
            <h3 className="analysis-right-panel__card-title">
              Ball Toss Trajectory
            </h3>
            <p className="analysis-right-panel__card-subtitle">Coming soon</p>
          </div>
        </div>
        <div className="analysis-right-panel__trajectory-chart">
          <div className="analysis-right-panel__chart-placeholder">
            <div className="analysis-right-panel__chart-blurred">
              <svg
                className="analysis-right-panel__chart-svg"
                viewBox="0 0 300 180"
                preserveAspectRatio="none"
              >
                {/* Y-axis */}
                <line
                  x1="40"
                  y1="20"
                  x2="40"
                  y2="160"
                  stroke="#e0e0e0"
                  strokeWidth="1"
                />
                {/* X-axis */}
                <line
                  x1="40"
                  y1="160"
                  x2="280"
                  y2="160"
                  stroke="#e0e0e0"
                  strokeWidth="1"
                />
                {/* Y-axis labels */}
                <text x="35" y="25" fill="#999" fontSize="10" textAnchor="end">
                  300
                </text>
                <text x="35" y="90" fill="#999" fontSize="10" textAnchor="end">
                  200
                </text>
                <text x="35" y="155" fill="#999" fontSize="10" textAnchor="end">
                  100
                </text>
                {/* Ball trajectory curve */}
                <path
                  d="M 50 140 Q 100 80, 150 60 Q 200 40, 250 50"
                  fill="none"
                  stroke="#2b7fff"
                  strokeWidth="2"
                />
                {/* Release point */}
                <circle cx="50" cy="140" r="4" fill="#00b8db" />
                {/* Contact point */}
                <circle cx="250" cy="50" r="4" fill="#ff6900" />
                {/* Target zone */}
                <rect
                  x="40"
                  y="40"
                  width="240"
                  height="30"
                  fill="#00bc7d"
                  opacity="0.1"
                />
              </svg>
            </div>
            <p className="analysis-right-panel__chart-note">
              Visualize your ball's trajectory and optimize your toss height
            </p>
          </div>
        </div>
      </div>

    </div>
  );
};

export default AnalysisRightPanel;
