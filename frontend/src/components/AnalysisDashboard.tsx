import React, { useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAnalysisManager } from '../hooks/useAnalysisManager';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { ballContactApi } from '../services/ballContactApi';
import './AnalysisDashboard.css';
import AnalysisRightPanel from './AnalysisRightPanel';
import { ArrowBackIcon } from './Icons';
import ProgressBar from './ProgressBar';
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
  const queryClient = useQueryClient();

  // Use React Query hook for analysis status (with caching)
  const { data: analysisStatus, refetch: refetchAnalysisStatus } =
    useVideoAnalysisStatus(videoId);

  // Analysis manager for pose analysis
  const {
    analysisState,
    startAnalysis,
    isLoading: isAnalysisLoading,
  } = useAnalysisManager({
    videoId,
    autoRefresh: true,
    onAnalysisComplete: async () => {
      // Refresh analysis status after completion without reloading page
      await refetchAnalysisStatus();
      // Also invalidate the query to ensure fresh data
      queryClient.invalidateQueries({
        queryKey: ['video-analysis-status', videoId],
      });
    },
  });

  // Simple loading state for contact metrics (synchronous call)
  const [isRecomputingMetrics, setIsRecomputingMetrics] = useState(false);
  const [metricsError, setMetricsError] = useState<string | null>(null);

  const handleFocusAnalysis = useCallback(async () => {
    try {
      await startAnalysis({
        analysis_type: 'pose_only',
        confidence_threshold: 0.5,
      });
    } catch (error) {
      // Error handling is done by the startAnalysis hook
    }
  }, [startAnalysis]);

  const handleRecomputeContactMetrics = useCallback(async () => {
    setIsRecomputingMetrics(true);
    setMetricsError(null);
    try {
      await ballContactApi.analyzeVideoPosture(videoId, {
        force_reanalysis: false,
      });
      // Refresh contacts to show updated metrics
      await queryClient.invalidateQueries({
        queryKey: ['ball-contacts', videoId],
      });
    } catch (error) {
      const axiosError = error as { response?: { data?: { detail?: string } }; message?: string };
      const errorMessage =
        axiosError?.response?.data?.detail ||
        axiosError?.message ||
        'Failed to recompute contact metrics';
      setMetricsError(errorMessage);
    } finally {
      setIsRecomputingMetrics(false);
    }
  }, [videoId, queryClient]);

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
                  <span>Frame by frame</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column - Analysis Panel */}
        <div className="analysis-dashboard__analysis-column">
          {!analysisStatus?.has_analysis && (
            <>
              {(analysisState.status === 'starting' ||
                analysisState.status === 'processing') && (
                <div className="analysis-dashboard__progress-card">
                  <ProgressBar
                    progress={analysisState.progress}
                    status={analysisState.status}
                    showPercentage={true}
                    showStatus={true}
                    size="medium"
                    animated={true}
                  />
                </div>
              )}
              {analysisState.status === 'idle' && (
                <button
                  className="analysis-dashboard__analyze-btn"
                  onClick={handleFocusAnalysis}
                  disabled={isAnalysisLoading}
                >
                  Analyze
                </button>
              )}
              {analysisState.status === 'failed' && (
                <div className="analysis-dashboard__error-card">
                  <p className="analysis-dashboard__error-message">
                    {analysisState.error ||
                      'Analysis failed. Please try again.'}
                  </p>
                  <button
                    className="analysis-dashboard__analyze-btn"
                    onClick={handleFocusAnalysis}
                    disabled={isAnalysisLoading}
                  >
                    Retry Analysis
                  </button>
                </div>
              )}
            </>
          )}
          {analysisStatus?.has_analysis && (
            <>
              {isRecomputingMetrics && (
                <div className="analysis-dashboard__progress-card">
                  <p className="analysis-dashboard__loading-message">
                    Computing contact metrics...
                  </p>
                </div>
              )}
              {!isRecomputingMetrics && (
                <>
                  {metricsError ? (
                    <div className="analysis-dashboard__error-card">
                      <p className="analysis-dashboard__error-message">
                        {metricsError}
                      </p>
                      <button
                        className="analysis-dashboard__analyze-btn analysis-dashboard__analyze-btn--secondary"
                        onClick={handleRecomputeContactMetrics}
                      >
                        Retry
                      </button>
                    </div>
                  ) : (
                    <button
                      className="analysis-dashboard__analyze-btn analysis-dashboard__analyze-btn--secondary"
                      onClick={handleRecomputeContactMetrics}
                      disabled={isRecomputingMetrics}
                    >
                      Recompute Contact Metrics
                    </button>
                  )}
                </>
              )}
            </>
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
