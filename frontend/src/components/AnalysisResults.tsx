import React, { useState } from 'react';
import { AnalysisData } from '../services/api';
import './AnalysisResults.css';
import TimingPerformance from './TimingPerformance';

interface AnalysisResultsProps {
  analysis: AnalysisData | null;
  isLoading?: boolean;
  error?: string | null;
}

const AnalysisResults: React.FC<AnalysisResultsProps> = ({
  analysis,
  isLoading = false,
  error = null,
}) => {
  const [expandedSections, setExpandedSections] = useState<{
    pose: boolean;
    ball: boolean;
    timing: boolean;
  }>({
    pose: false,
    ball: false,
    timing: false,
  });

  const toggleSection = (section: 'pose' | 'ball' | 'timing') => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const formatPercentage = (value: number): string => {
    return `${(value * 100).toFixed(1)}%`;
  };

  if (isLoading) {
    return (
      <div className="analysis-results">
        <div className="analysis-loading">
          <div className="loading-spinner"></div>
          <p>Analyzing video...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analysis-results">
        <div className="analysis-error">
          <h3>❌ Analysis Error</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="analysis-results">
        <div className="analysis-empty">
          <h3>📊 Analysis Results</h3>
          <p>No analysis data available. Start an analysis to see results.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="analysis-results">
      <div className="analysis-header">
        <h3>🎾 Tennis Coach Analysis Results</h3>
      </div>

      {/* Performance Timing Section */}
      {(analysis.timing || analysis.processing_time) && (
        <div className="analysis-section">
          <div 
            className="section-header clickable" 
            onClick={() => toggleSection('timing')}
          >
            <span className="section-icon">⚡</span>
            <h4>Performance Metrics</h4>
            <div className="status-badge info">
              {analysis.timing ? 'Detailed' : 'Basic'} timing
            </div>
            <span className="toggle-icon">
              {expandedSections.timing ? '▼' : '▶'}
            </span>
          </div>
          
          {expandedSections.timing && (
            <TimingPerformance 
              timing={analysis.timing}
              processingTime={analysis.processing_time}
            />
          )}
        </div>
      )}

      {/* Pose Detection Results */}
      {analysis.frames_with_pose !== undefined && (
        <div className="analysis-section">
          <div 
            className="section-header clickable" 
            onClick={() => toggleSection('pose')}
          >
            <span className="section-icon">👤</span>
            <h4>Pose Detection</h4>
            <div className="status-badge success">
              {formatPercentage(analysis.pose_detection_rate || 0)} detected
            </div>
            <span className="toggle-icon">
              {expandedSections.pose ? '▼' : '▶'}
            </span>
          </div>
          
          {expandedSections.pose && (
            <div className="analysis-metrics">
              <div className="metric-card">
                <div className="metric-value">{analysis.total_frames}</div>
                <div className="metric-label">Frames Analyzed</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">{analysis.frames_with_pose}</div>
                <div className="metric-label">Pose Detected</div>
              </div>
              <div className="metric-card">
                <div className="metric-value">
                  {formatPercentage(analysis.pose_detection_rate || 0)}
                </div>
                <div className="metric-label">Detection Rate</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Ball Detection Results */}
      <div className="analysis-section">
        <div 
          className="section-header clickable" 
          onClick={() => toggleSection('ball')}
        >
          <span className="section-icon">🎾</span>
          <h4>Ball Detection</h4>
          <div className="status-badge success">
            {formatPercentage(analysis.detection_rate)} detected
          </div>
          <span className="toggle-icon">
            {expandedSections.ball ? '▼' : '▶'}
          </span>
        </div>
        
        {expandedSections.ball && (
          <div className="analysis-metrics">
            <div className="metric-card">
              <div className="metric-value">{analysis.total_ball_detections}</div>
              <div className="metric-label">Ball Detections</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{analysis.frames_with_balls}</div>
              <div className="metric-label">Frames with Balls</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">
                {analysis.average_detections_per_frame.toFixed(2)}
              </div>
              <div className="metric-label">Avg per Frame</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalysisResults;
