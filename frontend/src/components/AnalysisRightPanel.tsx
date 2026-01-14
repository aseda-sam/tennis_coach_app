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
      <div className="analysis-right-panel__card">
        <div className="analysis-right-panel__trajectory-header">
          <div className="analysis-right-panel__trajectory-title-group">
            <h3 className="analysis-right-panel__card-title">Ball Toss Trajectory</h3>
            <p className="analysis-right-panel__card-subtitle">Vertical height only</p>
          </div>
        </div>
        <div className="analysis-right-panel__trajectory-chart">
          {/* Placeholder chart - will be replaced with actual chart component later */}
          <div className="analysis-right-panel__chart-placeholder">
            <p>Chart placeholder</p>
            <p className="analysis-right-panel__chart-note">
              Ball trajectory visualization will appear here once analysis is complete
            </p>
          </div>
        </div>
        <div className="analysis-right-panel__trajectory-legend">
          <div className="analysis-right-panel__legend-item">
            <span className="analysis-right-panel__legend-line analysis-right-panel__legend-line--ball"></span>
            <span>Ball Path</span>
          </div>
          <div className="analysis-right-panel__legend-item">
            <span className="analysis-right-panel__legend-dot analysis-right-panel__legend-dot--release"></span>
            <span>Release</span>
          </div>
          <div className="analysis-right-panel__legend-item">
            <span className="analysis-right-panel__legend-dot analysis-right-panel__legend-dot--contact"></span>
            <span>Contact</span>
          </div>
          <div className="analysis-right-panel__legend-item">
            <span className="analysis-right-panel__legend-zone"></span>
            <span>Target Zone</span>
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
