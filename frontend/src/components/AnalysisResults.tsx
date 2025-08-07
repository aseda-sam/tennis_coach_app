import React from 'react';
import './AnalysisResults.css';

export interface AnalysisData {
  id: number;
  video_filename: string;
  analysis_type: string;
  total_frames: number;
  frames_with_balls: number;
  total_ball_detections: number;
  average_detections_per_frame: number;
  detection_rate: number;
  processing_time: number;
  model_used: string | null;
  confidence_threshold: number;
}

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

  const formatTime = (seconds: number): string => {
    return `${seconds.toFixed(2)}s`;
  };

  const formatPercentage = (value: number): string => {
    return `${(value * 100).toFixed(1)}%`;
  };

  return (
    <div className="analysis-results">
      <div className="analysis-header">
        <h3>📊 Analysis Results</h3>
        <div className="analysis-meta">
          <span className="model-info">
            Model: {analysis.model_used || 'Not specified'}
          </span>
          <span className="processing-time">
            Processing: {formatTime(analysis.processing_time)}
          </span>
        </div>
      </div>

      <div className="analysis-metrics">
        <div className="metric-card">
          <div className="metric-value">{analysis.total_frames}</div>
          <div className="metric-label">Total Frames</div>
        </div>

        <div className="metric-card">
          <div className="metric-value">{analysis.frames_with_balls}</div>
          <div className="metric-label">Frames with Balls</div>
        </div>

        <div className="metric-card">
          <div className="metric-value">{analysis.total_ball_detections}</div>
          <div className="metric-label">Total Detections</div>
        </div>

        <div className="metric-card">
          <div className="metric-value">
            {analysis.average_detections_per_frame.toFixed(2)}
          </div>
          <div className="metric-label">Avg Detections/Frame</div>
        </div>

        <div className="metric-card">
          <div className="metric-value">
            {formatPercentage(analysis.detection_rate)}
          </div>
          <div className="metric-label">Detection Rate</div>
        </div>

        <div className="metric-card">
          <div className="metric-value">
            {formatPercentage(analysis.confidence_threshold)}
          </div>
          <div className="metric-label">Confidence Threshold</div>
        </div>
      </div>

      <div className="analysis-summary">
        <h4>Summary</h4>
        <p>
          The analysis detected <strong>{analysis.total_ball_detections}</strong> tennis
          balls across <strong>{analysis.total_frames}</strong> frames. Balls were
          found in <strong>{analysis.frames_with_balls}</strong> frames, giving a
          detection rate of <strong>{formatPercentage(analysis.detection_rate)}</strong>.
        </p>
        <p>
          Processing took <strong>{formatTime(analysis.processing_time)}</strong> using
          the <strong>{analysis.model_used || 'YOLO'}</strong> model.
        </p>
      </div>
    </div>
  );
};

export default AnalysisResults;
