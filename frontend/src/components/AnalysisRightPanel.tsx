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
            <h3 className="analysis-right-panel__card-title">Ball Toss Trajectory</h3>
            <p className="analysis-right-panel__card-subtitle">Coming soon</p>
          </div>
        </div>
        <div className="analysis-right-panel__trajectory-chart">
          <div className="analysis-right-panel__chart-placeholder">
            <div className="analysis-right-panel__chart-blurred">
              <svg className="analysis-right-panel__chart-svg" viewBox="0 0 300 180" preserveAspectRatio="none">
                {/* Y-axis */}
                <line x1="40" y1="20" x2="40" y2="160" stroke="#e0e0e0" strokeWidth="1"/>
                {/* X-axis */}
                <line x1="40" y1="160" x2="280" y2="160" stroke="#e0e0e0" strokeWidth="1"/>
                {/* Y-axis labels */}
                <text x="35" y="25" fill="#999" fontSize="10" textAnchor="end">300</text>
                <text x="35" y="90" fill="#999" fontSize="10" textAnchor="end">200</text>
                <text x="35" y="155" fill="#999" fontSize="10" textAnchor="end">100</text>
                {/* Ball trajectory curve */}
                <path d="M 50 140 Q 100 80, 150 60 Q 200 40, 250 50" 
                      fill="none" 
                      stroke="#2b7fff" 
                      strokeWidth="2"/>
                {/* Release point */}
                <circle cx="50" cy="140" r="4" fill="#00b8db"/>
                {/* Contact point */}
                <circle cx="250" cy="50" r="4" fill="#ff6900"/>
                {/* Target zone */}
                <rect x="40" y="40" width="240" height="30" fill="#00bc7d" opacity="0.1"/>
              </svg>
            </div>
            <p className="analysis-right-panel__chart-note">
              Visualize your ball's trajectory and optimize your toss height
            </p>
          </div>
        </div>
      </div>

      {/* Measurements Card */}
      <div className="analysis-right-panel__card">
        <h3 className="analysis-right-panel__measurements-title">Measurements</h3>
        <div className="analysis-right-panel__measurements-list">
          {/* Ball Heights */}
          <div className="analysis-right-panel__measurement-group">
            <div className="analysis-right-panel__measurement-header">
              <div className="analysis-right-panel__measurement-icon">📊</div>
              <span className="analysis-right-panel__measurement-label">Ball Heights</span>
              <span className="analysis-right-panel__measurement-check">✓</span>
            </div>
            <div className="analysis-right-panel__measurement-items">
              <div className="analysis-right-panel__measurement-item">
                <div className="analysis-right-panel__measurement-name">
                  <span className="analysis-right-panel__measurement-dot analysis-right-panel__measurement-dot--toss"></span>
                  <span>Toss</span>
                </div>
                <div className="analysis-right-panel__measurement-value">
                  <span>315</span>
                  <span className="analysis-right-panel__measurement-unit">cm</span>
                </div>
              </div>
              <div className="analysis-right-panel__measurement-item">
                <div className="analysis-right-panel__measurement-name">
                  <span className="analysis-right-panel__measurement-dot analysis-right-panel__measurement-dot--contact"></span>
                  <span>Contact</span>
                </div>
                <div className="analysis-right-panel__measurement-value">
                  <span>305</span>
                  <span className="analysis-right-panel__measurement-unit">cm</span>
                </div>
              </div>
            </div>
            <div className="analysis-right-panel__measurement-timing">
              <span className="analysis-right-panel__timing-label">Timing</span>
              <span className="analysis-right-panel__timing-value">10 cm falling</span>
            </div>
            <div className="analysis-right-panel__measurement-target">
              <p className="analysis-right-panel__target-text">Target toss: 300–350 cm</p>
              <div className="analysis-right-panel__target-bar">
                <div className="analysis-right-panel__target-progress"></div>
                <div className="analysis-right-panel__target-marker"></div>
              </div>
            </div>
          </div>

          {/* Elbow Angle */}
          <div className="analysis-right-panel__measurement-group">
            <div className="analysis-right-panel__measurement-header">
              <div className="analysis-right-panel__measurement-icon">📐</div>
              <span className="analysis-right-panel__measurement-label">Elbow Angle at Contact</span>
            </div>
            <div className="analysis-right-panel__measurement-value-large">
              <span>142</span>
              <span className="analysis-right-panel__measurement-unit">°</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalysisRightPanel;
