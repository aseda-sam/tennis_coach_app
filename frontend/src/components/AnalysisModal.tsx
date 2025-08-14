import React, { useEffect, useState, useCallback } from 'react';
import { analysisApi, AnalysisData } from '../services/api';
import './AnalysisModal.css';

interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  videoId: number;
}

const AnalysisModal: React.FC<AnalysisModalProps> = ({
  isOpen,
  onClose,
  videoId,
}) => {
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAnalysis = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const analysisData = await analysisApi.getAnalysis(videoId);
      setAnalysis(analysisData);
    } catch (err: any) {
      setError('Failed to load analysis results. Please try again.');
      console.error('Error loading analysis:', err);
    } finally {
      setLoading(false);
    }
  }, [videoId]);

  useEffect(() => {
    if (isOpen && videoId) {
      loadAnalysis();
    }
  }, [isOpen, videoId, loadAnalysis]);

  if (!isOpen) return null;

  return (
    <div className="analysis-modal-overlay" onClick={onClose}>
      <div className="analysis-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>📊 Analysis Results</h2>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-content">
          <div className="video-info">
            <h3>Video ID: {videoId}</h3>
          </div>

          {loading && (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Loading analysis results...</p>
            </div>
          )}

          {error && (
            <div className="error-state">
              <h3>❌ Error</h3>
              <p>{error}</p>
            </div>
          )}

          {analysis && !loading && (
            <div className="analysis-details">
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
                    {(analysis.detection_rate * 100).toFixed(1)}%
                  </div>
                  <div className="metric-label">Detection Rate</div>
                </div>

                {analysis.frames_with_pose && (
                  <div className="metric-card">
                    <div className="metric-value">{analysis.frames_with_pose}</div>
                    <div className="metric-label">Frames with Pose</div>
                  </div>
                )}

                {analysis.pose_detection_rate && (
                  <div className="metric-card">
                    <div className="metric-value">
                      {(analysis.pose_detection_rate * 100).toFixed(1)}%
                    </div>
                    <div className="metric-label">Pose Detection Rate</div>
                  </div>
                )}
              </div>

              <div className="analysis-summary">
                <h4>Analysis Summary</h4>
                <p>
                  Processed {analysis.total_frames} frames in {analysis.processing_time.toFixed(2)} seconds.
                  Detected balls in {analysis.frames_with_balls} frames with an average of{' '}
                  {analysis.average_detections_per_frame.toFixed(2)} detections per frame.
                </p>
                {analysis.frames_with_pose && (
                  <p>
                    Pose detection was performed on {analysis.frames_with_pose} frames with a{' '}
                    {(analysis.pose_detection_rate! * 100).toFixed(1)}% detection rate.
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalysisModal;
