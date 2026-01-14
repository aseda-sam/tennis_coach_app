import React, { useCallback } from 'react';
import { useAnalysisManager } from '../hooks/useAnalysisManager';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import './AnalysisDashboard.css';
import AnalysisRightPanel from './AnalysisRightPanel';
import { ArrowBackIcon } from './Icons';
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
  // Use React Query hook for analysis status (with caching)
  const { data: analysisStatus } = useVideoAnalysisStatus(videoId);

  // Analysis manager for pose analysis
  const {
    analysisState,
    startAnalysis,
    isLoading: isAnalysisLoading,
  } = useAnalysisManager({
    videoId,
    autoRefresh: true,
    onAnalysisComplete: () => {
      // Refresh analysis status after completion
      window.location.reload();
    },
  });

  const handleFocusAnalysis = useCallback(async () => {
    try {
      await startAnalysis({
        analysis_type: 'pose_only',
        confidence_threshold: 0.5,
      });
    } catch (error) {
      console.error('Failed to start pose analysis:', error);
    }
  }, [startAnalysis]);

  return (
    <div className="analysis-dashboard">
      {/* Header */}
      <div className="analysis-dashboard__header">
        <button className="analysis-dashboard__back-btn" onClick={onClose}>
          <ArrowBackIcon size={16} />
          Back
        </button>
        <div className="analysis-dashboard__header-content">
          <h1 className="analysis-dashboard__title">Serve Analysis</h1>
          <p className="analysis-dashboard__subtitle">{videoFilename}</p>
        </div>
      </div>

      {/* Main Content */}
      <div className="analysis-dashboard__content">
        {/* Left Column - Video Player */}
        <div className="analysis-dashboard__video-column">
          <VideoPlayer
            videoUrl={videoUrl}
            title={videoFilename}
            showControls={true}
            aspectRatioMode="contain"
            videoId={videoId}
            showPostureAnalysis={false}
            hasPoseData={analysisStatus?.has_analysis || false}
            controlsBelow={true}
          />

          {/* Keyboard Shortcuts Banner */}
          <div className="analysis-dashboard__keyboard-shortcuts">
            <div className="analysis-dashboard__shortcuts-icon">⌨️</div>
            <div className="analysis-dashboard__shortcuts-content">
              <h4 className="analysis-dashboard__shortcuts-title">
                Keyboard Shortcuts
              </h4>
              <div className="analysis-dashboard__shortcuts-list">
                <div className="analysis-dashboard__shortcut-item">
                  <kbd className="analysis-dashboard__kbd">Space</kbd>
                  <span>Play/Pause</span>
                </div>
                <div className="analysis-dashboard__shortcut-item">
                  <kbd className="analysis-dashboard__kbd">← →</kbd>
                  <span>Navigate serves</span>
                </div>
                <div className="analysis-dashboard__shortcut-item">
                  <kbd className="analysis-dashboard__kbd">↑ ↓</kbd>
                  <span>Frame by frame</span>
                </div>
                <div className="analysis-dashboard__shortcut-item">
                  <kbd className="analysis-dashboard__kbd">R</kbd>
                  <span>Loop serve</span>
                </div>
                <div className="analysis-dashboard__shortcut-item">
                  <kbd className="analysis-dashboard__kbd">V</kbd>
                  <span>Analyze</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Analysis Panel */}
        <div className="analysis-dashboard__analysis-column">
          {!analysisStatus?.has_analysis && (
            <button
              className="analysis-dashboard__analyze-btn"
              onClick={handleFocusAnalysis}
              disabled={isAnalysisLoading || analysisState.status === 'processing'}
            >
              {isAnalysisLoading || analysisState.status === 'processing'
                ? 'Analyzing...'
                : 'Analyze'}
            </button>
          )}
          <AnalysisRightPanel
            videoId={videoId}
            videoFilename={videoFilename}
            analysisStatus={analysisStatus}
          />
        </div>
      </div>
    </div>
  );
};

export default AnalysisDashboard;
