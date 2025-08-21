import React, { useEffect, useState } from 'react';
import { useAnalysisManager } from '../hooks/useAnalysisManager';
import { videoApi } from '../services/api';
import { VideoMetadata } from '../types/video';
import './AnalysisDashboard.css';
import AnalysisResults from './AnalysisResults';
import ProgressBar from './ProgressBar';
import StageProgress from './StageProgress';
import VideoPlayer from './VideoPlayer';

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
  const [video, setVideo] = useState<VideoMetadata | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);

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

  // Use the analysis manager hook for better state management
  const { analysisState, refreshAnalysis, cancelAnalysis, isLoading } =
    useAnalysisManager({
      videoId,
      autoRefresh: true,
      onAnalysisComplete: (analysis) => {
        console.log('Analysis completed:', analysis);
      },
      onAnalysisError: (error) => {
        console.error('Analysis error:', error);
      },
    });

  const { analysis, status, progress, error } = analysisState;

  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Smart video URL selection: use annotated video if available, otherwise original
  const getVideoUrl = () => {
    if (analysis?.pose_detections && analysis.pose_detections.length > 0) {
      // Use the new annotated video endpoint
      const baseUrl =
        process.env.REACT_APP_API_URL || 'http://localhost:8000/v0';
      const annotatedUrl = `${baseUrl}/videos/${videoId}/annotated/stream`;
      console.log('Using annotated video for:', videoFilename);
      console.log('Annotated video URL:', annotatedUrl);
      console.log('Analysis data:', analysis);
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
                analysis?.pose_detections && analysis.pose_detections.length > 0
                  ? `${videoFilename} (Annotated)`
                  : videoFilename
              }
              showControls={true}
              aspectRatioMode={aspectRatioMode}
              contactTimestamps={analysis?.contact_timestamps || []}
            />
            {analysis?.pose_detections &&
              analysis.pose_detections.length > 0 && (
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

                {analysis && (
                  <>
                    <div className="detail-item">
                      <span className="detail-label">Processing Time:</span>
                      <span className="detail-value">
                        {formatDuration(analysis.processing_time)}
                      </span>
                    </div>

                    <div className="detail-item">
                      <span className="detail-label">Total Frames:</span>
                      <span className="detail-value">
                        {analysis.total_frames}
                      </span>
                    </div>

                    <div className="detail-item">
                      <span className="detail-label">Analysis Type:</span>
                      <span className="detail-value">
                        {analysis.analysis_type}
                      </span>
                    </div>

                    {analysis.model_used && (
                      <div className="detail-item">
                        <span className="detail-label">Model Used:</span>
                        <span className="detail-value">
                          {analysis.model_used}
                        </span>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Analysis Results */}
        <div className="right-panel">
          <div className="analysis-status-section">
            {isLoading ||
            status === 'starting' ||
            status === 'processing' ||
            status === 'finalizing' ? (
              <div className="analysis-loading">
                <div className="loading-header">
                  <div className="loading-spinner"></div>
                  <h3>Analyzing Tennis Video...</h3>
                </div>

                <div className="progress-section">
                  {analysisState.currentStage ? (
                    <StageProgress
                      currentStage={analysisState.currentStage}
                      stageProgress={analysisState.stageProgress || 0}
                      stageMessage={
                        analysisState.stageMessage || 'Processing...'
                      }
                      overallProgress={progress}
                      size="large"
                    />
                  ) : (
                    <ProgressBar
                      progress={progress}
                      status={status as any}
                      size="large"
                      showPercentage={true}
                      showStatus={true}
                    />
                  )}
                </div>

                <p className="loading-note">
                  This may take 2-3 minutes for longer videos. You can leave
                  this page and return later.
                </p>

                {(status === 'processing' || status === 'starting') && (
                  <button
                    className="cancel-analysis-btn"
                    onClick={cancelAnalysis}
                  >
                    Cancel Analysis
                  </button>
                )}
              </div>
            ) : error ? (
              <div className="analysis-error">
                <h3>❌ Analysis Error</h3>
                <p>{error}</p>
                <button className="retry-btn" onClick={refreshAnalysis}>
                  Try Again
                </button>
              </div>
            ) : videoError ? (
              <div className="analysis-error">
                <h3>❌ Video Data Error</h3>
                <p>{videoError}</p>
                <button className="retry-btn" onClick={() => window.location.reload()}>
                  Reload Page
                </button>
              </div>
            ) : analysis ? (
              <AnalysisResults analysis={analysis} video={video} />
            ) : (
              <div className="analysis-empty">
                <h3>📊 Analysis Results</h3>
                <p>
                  No analysis data available. Start an analysis to see results.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalysisDashboard;
