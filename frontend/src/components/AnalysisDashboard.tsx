import React, { useEffect, useState } from 'react';
import { videoApi } from '../services/api';
import { VideoMetadata } from '../types/video';
import './AnalysisDashboard.css';
import VideoPlayer from './VideoPlayer';
import AnalysisPanel from './AnalysisPanel';

interface AnalysisDashboardProps {
  videoId: number;
  videoFilename: string;
  videoUrl: string;
  onClose: () => void;
}

const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({
  videoId,
  videoFilename,
  videoUrl,
  onClose,
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const [aspectRatioMode, setAspectRatioMode] = useState<
    'cover' | 'contain' | 'auto'
  >('contain');
  const [, setVideo] = useState<VideoMetadata | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<{
    has_analysis: boolean;
    has_annotated_video: boolean;
    analysis_types: string[];
    annotated_video_available: boolean;
  } | null>(null);

  // Fetch video data for quality metrics
  useEffect(() => {
    const fetchVideo = async () => {
      try {
        const videoData = await videoApi.getVideo(videoId);
        setVideo(videoData);
      } catch (error) {
        console.error('Error fetching video data:', error);
        setVideoError('Failed to load video data');
      }
    };

    fetchVideo();
  }, [videoId]);

  // Fetch analysis status
  useEffect(() => {
    const fetchAnalysisStatus = async () => {
      try {
        const status = await videoApi.getVideoAnalysisStatus(videoId);
        setAnalysisStatus(status);
      } catch (error) {
        console.debug('No analysis status available for video:', videoId);
        setAnalysisStatus({
          has_analysis: false,
          has_annotated_video: false,
          analysis_types: [],
          annotated_video_available: false,
        });
      }
    };

    fetchAnalysisStatus();
  }, [videoId]);

  // Analysis state for the new unified system
  const [, setAnalysisResult] = useState<any>(null);
  const [, setAnalysisError] = useState<string | null>(null);

  // Smart video URL selection: use annotated video if available, otherwise original
  const getVideoUrl = () => {
    // Check if there's any analysis and annotated video is available
    if (
      analysisStatus?.has_analysis &&
      analysisStatus?.annotated_video_available
    ) {
      // Use the annotated video endpoint
      const baseUrl =
        process.env.REACT_APP_API_URL || 'http://localhost:8000/v0';
      const annotatedUrl = `${baseUrl}/videos/${videoId}/annotated/stream`;
      console.log('Using annotated video for:', videoFilename);
      console.log('Annotated video URL:', annotatedUrl);
      console.log('Analysis status:', analysisStatus);
      return annotatedUrl;
    }
    console.log('Using original video URL:', videoUrl);
    return videoUrl;
  };

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
        {/* Left Panel - Video Player */}
        <div className="left-panel">
          <div className="video-section">
            {/* Aspect Ratio Mode Selector */}
            <div className="aspect-ratio-controls">
              <label htmlFor="aspect-ratio-mode">Video Display Mode:</label>
              <select
                id="aspect-ratio-mode"
                value={aspectRatioMode}
                onChange={(e) =>
                  setAspectRatioMode(
                    e.target.value as 'cover' | 'contain' | 'auto'
                  )
                }
                className="aspect-ratio-select"
              >
                <option value="contain">Fit with Black Bars (Default)</option>
                <option value="cover">Crop to Fit</option>
                <option value="auto">Auto Adjust</option>
              </select>
            </div>

            <VideoPlayer
              videoUrl={getVideoUrl()}
              title={
                analysisStatus?.has_analysis &&
                analysisStatus?.annotated_video_available
                  ? `${videoFilename} (Annotated)`
                  : videoFilename
              }
              showControls={true}
              aspectRatioMode={aspectRatioMode}
              videoId={videoId}
            />
            {analysisStatus?.has_analysis &&
              analysisStatus?.annotated_video_available && (
                <div className="ai-analysis-badge">
                  <span className="ai-icon">⚡</span>
                  AI Analysis Active
                </div>
              )}
          </div>

          {/* Video Details and Actions below video */}
          <div className="video-details-section">
            <div
              className="section-header"
              onClick={() => setShowDetails(!showDetails)}
            >
              <span className="section-icon">📄</span>
              <h3>Video Details</h3>
              <span className="toggle-icon">{showDetails ? '▼' : '▶'}</span>
            </div>

            {showDetails && (
              <div className="details-list">
                <div className="detail-item">
                  <span className="detail-label">File Name:</span>
                  <span className="detail-value">{videoFilename}</span>
                </div>

                {analysisStatus?.has_analysis && (
                  <>
                    <div className="detail-item">
                      <span className="detail-label">Analysis Types:</span>
                      <span className="detail-value">
                        {analysisStatus.analysis_types.join(', ')}
                      </span>
                    </div>

                    <div className="detail-item">
                      <span className="detail-label">Annotated Video:</span>
                      <span className="detail-value">
                        {analysisStatus.annotated_video_available
                          ? 'Available'
                          : 'Not Available'}
                      </span>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Analysis Panel */}
        <div className="right-panel">
          <div className="analysis-status-section">
            {videoError ? (
              <div className="analysis-error">
                <h3>❌ Video Data Error</h3>
                <p>{videoError}</p>
                <button
                  className="retry-btn"
                  onClick={() => window.location.reload()}
                >
                  Reload Page
                </button>
              </div>
            ) : (
              <AnalysisPanel
                videoId={videoId}
                onAnalysisComplete={(result) => {
                  setAnalysisResult(result);
                  setAnalysisError(null);
                  // Refresh analysis status after completion
                  const fetchAnalysisStatus = async () => {
                    try {
                      const status = await videoApi.getVideoAnalysisStatus(videoId);
                      setAnalysisStatus(status);
                    } catch (error) {
                      console.debug('No analysis status available for video:', videoId);
                    }
                  };
                  fetchAnalysisStatus();
                }}
                onAnalysisError={(error) => {
                  setAnalysisError(error);
                  setAnalysisResult(null);
                }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalysisDashboard;
