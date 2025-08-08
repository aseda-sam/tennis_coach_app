import React, { useEffect, useState, useCallback } from 'react';
import { analysisApi } from '../services/api';
import './AnalysisDashboard.css';
import { AnalysisData } from './AnalysisResults';
import VideoPlayer from './VideoPlayer';

interface AnalysisDashboardProps {
  videoFilename: string;
  videoUrl: string;
  onClose: () => void;
}

const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({
  videoFilename,
  videoUrl,
  onClose,
}) => {
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAnalysis();
  }, [loadAnalysis]);

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

  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };



  const getAnalysisStatus = () => {
    if (loading) return { text: 'Loading...', color: 'loading' };
    if (error) return { text: 'Error', color: 'error' };
    if (analysis) return { text: 'Completed', color: 'completed' };
    return { text: 'Not Available', color: 'not-available' };
  };

  const status = getAnalysisStatus();

  return (
    <div className="analysis-dashboard">
      <div className="dashboard-header">
        <button className="back-btn" onClick={onClose}>
          <span className="back-icon">←</span>
          Back to Videos
        </button>
        <h1 className="dashboard-title">{videoFilename}</h1>
        <div className="upload-info">Uploaded recently</div>
      </div>

      <div className="dashboard-content">
        {/* Left Panel - Video Player and Analysis Status */}
        <div className="left-panel">
          <div className="video-section">
            <VideoPlayer
              videoUrl={videoUrl}
              title={videoFilename}
              showControls={true}
            />
          </div>

          <div className="analysis-status-section">
            <div className="status-header">
              <h3>Video Analysis</h3>
              <div className={`status-badge ${status.color}`}>
                {status.text}
              </div>
            </div>

            <div className="analysis-cards">
              <div className="analysis-card">
                <div className="card-header">
                  <span className="card-icon">🎾</span>
                  <h4>Swing Analysis</h4>
                </div>
                <div className="card-content">
                  {loading ? (
                    <div className="loading-text">Loading...</div>
                  ) : analysis ? (
                    <div className="analysis-complete">
                      <span className="complete-icon">✓</span>
                      Analysis complete
                    </div>
                  ) : (
                    <div className="analysis-error">
                      <span className="error-icon">⚠</span>
                      {error || 'Not available'}
                    </div>
                  )}
                </div>
              </div>

              <div className="analysis-card">
                <div className="card-header">
                  <span className="card-icon">👤</span>
                  <h4>Movement Tracking</h4>
                </div>
                <div className="card-content">
                  <div className="coming-soon">
                    <span className="soon-icon">🔜</span>
                    Coming soon
                  </div>
                </div>
              </div>

              <div className="analysis-card">
                <div className="card-header">
                  <span className="card-icon">📊</span>
                  <h4>Performance Metrics</h4>
                </div>
                <div className="card-content">
                  {loading ? (
                    <div className="loading-text">Loading...</div>
                  ) : analysis ? (
                    <div className="analysis-complete">
                      <span className="complete-icon">✓</span>
                      Analysis complete
                    </div>
                  ) : (
                    <div className="analysis-error">
                      <span className="error-icon">⚠</span>
                      {error || 'Not available'}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - Video Details and Actions */}
        <div className="right-panel">
          <div className="video-details-section">
            <div className="section-header">
              <span className="section-icon">📄</span>
              <h3>Video Details</h3>
            </div>
            
            <div className="details-list">
              <div className="detail-item">
                <span className="detail-label">File Name:</span>
                <span className="detail-value">{videoFilename}</span>
              </div>
              
              {analysis && (
                <>
                  <div className="detail-item">
                    <span className="detail-label">File Size:</span>
                    <span className="detail-value">42.92 MB</span>
                  </div>
                  
                  <div className="detail-item">
                    <span className="detail-label">Duration:</span>
                    <span className="detail-value">
                      {formatDuration(analysis.processing_time)}
                    </span>
                  </div>
                  
                  <div className="detail-item">
                    <span className="detail-label">Resolution:</span>
                    <span className="detail-value">1920×1080</span>
                  </div>
                  
                  <div className="detail-item">
                    <span className="detail-label">Frame Rate:</span>
                    <span className="detail-value">60 fps</span>
                  </div>
                  
                  <div className="detail-item">
                    <span className="detail-label">Format:</span>
                    <span className="detail-value">MP4</span>
                  </div>
                  
                  <div className="detail-item">
                    <span className="detail-label">Upload Date:</span>
                    <span className="detail-value">Jan 15, 2024</span>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="actions-section">
            <div className="section-header">
              <h3>Actions</h3>
            </div>
            
            <div className="action-buttons">
              <button className="action-btn download-btn">
                <span className="btn-icon">⬇</span>
                Download Video
              </button>
              
              <button className="action-btn export-btn">
                <span className="btn-icon">📤</span>
                Export Analysis
              </button>
              
              <button className="action-btn share-btn">
                <span className="btn-icon">🔗</span>
                Share Video
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalysisDashboard;
