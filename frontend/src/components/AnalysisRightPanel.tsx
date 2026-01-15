import React from 'react';
import './AnalysisRightPanel.css';

interface AnalysisRightPanelProps {
  videoId: number;
  videoFilename: string;
  analysisStatus?: {
    has_analysis?: boolean;
  };
}

const AnalysisRightPanel: React.FC<AnalysisRightPanelProps> = ({
  videoId,
  videoFilename,
  analysisStatus,
}) => {
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

      {/* Measurements Card */}
      <div className="analysis-right-panel__card analysis-right-panel__card--coming-soon">
        <div className="analysis-right-panel__trajectory-header">
          <div className="analysis-right-panel__trajectory-title-group">
            <h3 className="analysis-right-panel__card-title">
              Measurements
            </h3>
            <p className="analysis-right-panel__card-subtitle">Coming soon</p>
          </div>
        </div>
        <div className="analysis-right-panel__trajectory-chart">
          <div className="analysis-right-panel__chart-placeholder">
            <div className="analysis-right-panel__chart-blurred">
              <div className="analysis-right-panel__measurements-preview">
                <div className="analysis-right-panel__measurement-preview-item">
                  <span className="analysis-right-panel__preview-label">Toss</span>
                  <span className="analysis-right-panel__preview-value">315 cm</span>
                </div>
                <div className="analysis-right-panel__measurement-preview-item">
                  <span className="analysis-right-panel__preview-label">Contact</span>
                  <span className="analysis-right-panel__preview-value">305 cm</span>
                </div>
                <div className="analysis-right-panel__measurement-preview-item">
                  <span className="analysis-right-panel__preview-label">Elbow Angle</span>
                  <span className="analysis-right-panel__preview-value">142°</span>
                </div>
              </div>
            </div>
            <p className="analysis-right-panel__chart-note">
              Track key metrics and improve your serve technique
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalysisRightPanel;
