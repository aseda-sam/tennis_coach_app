import React, { useEffect, useState, useCallback } from 'react';
import { analysisApi } from '../services/api';
import './AnalysisModal.css';
import { AnalysisData } from './AnalysisResults';

interface AnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  videoFilename: string;
}

const AnalysisModal: React.FC<AnalysisModalProps> = ({
  isOpen,
  onClose,
  videoFilename,
}) => {
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAnalysis = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const analysisData = await analysisApi.getAnalysis(videoFilename);
      setAnalysis(analysisData);
    } catch (err: any) {
      setError('Failed to load analysis results. Please try again.');
      console.error('Error loading analysis:', err);
    } finally {
      setLoading(false);
    }
  }, [videoFilename]);

  useEffect(() => {
    if (isOpen && videoFilename) {
      loadAnalysis();
    }
  }, [isOpen, videoFilename, loadAnalysis]);

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
            <h3>{videoFilename}</h3>
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

                <div className="metric-card">
                  <div className="metric-value">
                    {(analysis.confidence_threshold * 100).toFixed(0)}%
                  </div>
                  <div className="metric-label">Confidence Threshold</div>
                </div>
              </div>

              <div className="analysis-summary">
                <h4>Analysis Summary</h4>
                <p>
                  The analysis detected <strong>{analysis.total_ball_detections}</strong> tennis
                  balls across <strong>{analysis.total_frames}</strong> frames. Balls were
                  found in <strong>{analysis.frames_with_balls}</strong> frames, giving a
                  detection rate of <strong>{(analysis.detection_rate * 100).toFixed(1)}%</strong>.
                </p>
                <p>
                  Processing took <strong>{analysis.processing_time.toFixed(2)}s</strong> using
                  the <strong>{analysis.model_used || 'YOLO'}</strong> model.
                </p>
              </div>

              <div className="analysis-details">
                <h4>Technical Details</h4>
                <div className="details-grid">
                  <div className="detail-item">
                    <span className="label">Analysis Type:</span>
                    <span className="value">{analysis.analysis_type}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Model Used:</span>
                    <span className="value">{analysis.model_used || 'Not specified'}</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Processing Time:</span>
                    <span className="value">{analysis.processing_time.toFixed(2)}s</span>
                  </div>
                  <div className="detail-item">
                    <span className="label">Analysis ID:</span>
                    <span className="value">{analysis.id}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalysisModal;
