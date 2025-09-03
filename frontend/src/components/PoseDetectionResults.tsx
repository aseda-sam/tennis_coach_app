import React from 'react';
import { PoseDetectionInfo } from '../services/poseDetectionApi';
import './AnalysisResults.css';

interface PoseDetectionResultsProps {
  poseDetection: PoseDetectionInfo | null;
  isLoading?: boolean;
  error?: string | null;
}

const PoseDetectionResults: React.FC<PoseDetectionResultsProps> = ({
  poseDetection,
  isLoading = false,
  error = null,
}) => {
  if (isLoading) {
    return (
      <div className="analysis-section">
        <h3>Pose Detection Results</h3>
        <div className="loading-state">
          <div className="spinner"></div>
          <span>Loading pose detection results...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="analysis-section">
        <h3>Pose Detection Results</h3>
        <div className="error-state">
          <span className="error-message">Error: {error}</span>
        </div>
      </div>
    );
  }

  if (!poseDetection) {
    return (
      <div className="analysis-section">
        <h3>Pose Detection Results</h3>
        <div className="no-data">
          <span>No pose detection data available</span>
        </div>
      </div>
    );
  }

  const { metrics } = poseDetection;

  const formatPercentage = (value: number): string => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatDuration = (seconds: number): string => {
    return `${seconds.toFixed(2)}s`;
  };

  const formatConfidence = (value?: number): string => {
    if (value === undefined || value === null) return 'N/A';
    return `${(value * 100).toFixed(1)}%`;
  };

  const getStatusBadge = (status: string) => {
    const statusClass =
      status === 'completed'
        ? 'success'
        : status === 'failed'
          ? 'error'
          : 'warning';
    return <span className={`status-badge ${statusClass}`}>{status}</span>;
  };

  return (
    <div className="analysis-section">
      <div className="section-header">
        <h3>Pose Detection Results</h3>
        {getStatusBadge(poseDetection.status)}
      </div>

      {poseDetection.error_message && (
        <div className="error-message">
          <strong>Error:</strong> {poseDetection.error_message}
        </div>
      )}

      <div className="metrics-grid">
        {/* Detection Summary */}
        <div className="metric-group">
          <h4>Detection Summary</h4>
          <div className="metric-row">
            <span className="metric-label">Total Frames:</span>
            <span className="metric-value">
              {metrics.total_frames.toLocaleString()}
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-label">Frames with Poses:</span>
            <span className="metric-value">
              {metrics.frames_with_poses.toLocaleString()}
              <span className="metric-secondary">
                ({formatPercentage(metrics.detection_rate)})
              </span>
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-label">Total Detections:</span>
            <span className="metric-value">
              {metrics.total_pose_detections.toLocaleString()}
            </span>
          </div>
        </div>

        {/* Quality Metrics */}
        <div className="metric-group">
          <h4>Quality Metrics</h4>
          <div className="metric-row">
            <span className="metric-label">Average Confidence:</span>
            <span className="metric-value">
              {formatConfidence(metrics.average_pose_confidence)}
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-label">Confidence Range:</span>
            <span className="metric-value">
              {formatConfidence(metrics.min_pose_confidence)} -{' '}
              {formatConfidence(metrics.max_pose_confidence)}
            </span>
          </div>
          {metrics.pose_stability_score && (
            <div className="metric-row">
              <span className="metric-label">Stability Score:</span>
              <span className="metric-value">
                {formatConfidence(metrics.pose_stability_score)}
              </span>
            </div>
          )}
        </div>

        {/* Configuration */}
        <div className="metric-group">
          <h4>Configuration</h4>
          <div className="metric-row">
            <span className="metric-label">Confidence Threshold:</span>
            <span className="metric-value">
              {formatConfidence(metrics.confidence_threshold)}
            </span>
          </div>
          <div className="metric-row">
            <span className="metric-label">Detection Threshold:</span>
            <span className="metric-value">
              {formatConfidence(metrics.detection_threshold)}
            </span>
          </div>
        </div>

        {/* Performance */}
        <div className="metric-group">
          <h4>Performance</h4>
          <div className="metric-row">
            <span className="metric-label">Processing Time:</span>
            <span className="metric-value">
              {formatDuration(metrics.processing_time_seconds)}
            </span>
          </div>
          {metrics.frame_processing_rate && (
            <div className="metric-row">
              <span className="metric-label">Processing Rate:</span>
              <span className="metric-value">
                {metrics.frame_processing_rate.toFixed(1)} fps
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Timestamps */}
      <div className="timestamps">
        <div className="timestamp">
          <span className="timestamp-label">Created:</span>
          <span className="timestamp-value">
            {new Date(poseDetection.created_at).toLocaleString()}
          </span>
        </div>
        {poseDetection.completed_at && (
          <div className="timestamp">
            <span className="timestamp-label">Completed:</span>
            <span className="timestamp-value">
              {new Date(poseDetection.completed_at).toLocaleString()}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default PoseDetectionResults;
