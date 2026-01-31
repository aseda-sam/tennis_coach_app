import { useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useState } from 'react';
import { useAnalysisManager } from '../hooks/useAnalysisManager';
import { useServeAttempts } from '../hooks/useServeAttempts';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { serveAttemptApi } from '../services/serveAttemptApi';
import './AnalysisDashboard.css';
import AnalysisRightPanel from './AnalysisRightPanel';
import KeyboardShortcutsBanner from './KeyboardShortcutsBanner';
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

  // Memoize the completion callback to prevent infinite re-renders
  const handleAnalysisComplete = useCallback(async () => {
    // Refresh analysis status after completion without reloading page
    await refetchAnalysisStatus();
    // Also invalidate the query to ensure fresh data
    queryClient.invalidateQueries({
      queryKey: ['video-analysis-status', videoId],
    });
  }, [refetchAnalysisStatus, queryClient, videoId]);

  // Analysis manager for pose analysis
  const {
    analysisState,
    startAnalysis,
    isLoading: isAnalysisLoading,
  } = useAnalysisManager({
    videoId,
    autoRefresh: true,
    onAnalysisComplete: handleAnalysisComplete,
  });

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

  const [videoPlayerNavigate, setVideoPlayerNavigate] = useState<
    ((serveAttemptId: number) => void) | null
  >(null);
  const [isAnalyzingServes, setIsAnalyzingServes] = useState(false);
  const [naturalScroll, setNaturalScroll] = useState(false);

  // Get serve attempts for this video
  const { serveAttempts } = useServeAttempts({
    videoId,
    filters: { video_id: videoId },
    autoRefresh: true,
  });

  const handleServeAttemptClick = useCallback(
    (serveAttemptId: number) => {
      videoPlayerNavigate?.(serveAttemptId);
    },
    [videoPlayerNavigate]
  );

  const handleNavigateReady = useCallback(
    (navigateFn: (serveAttemptId: number) => void) => {
      setVideoPlayerNavigate(() => navigateFn);
    },
    []
  );

  const handleAnalyzeServes = useCallback(async () => {
    if (serveAttempts.length === 0) {
      alert('Please tag serve attempts first before analyzing.');
      return;
    }

    // Check if any serve attempts already have metrics
    const hasExistingMetrics = serveAttempts.some(
      (sa) =>
        sa.elbow_angle_at_contact !== null &&
        sa.elbow_angle_at_contact !== undefined
    );

    setIsAnalyzingServes(true);
    try {
      await serveAttemptApi.analyzeServes(videoId);
      // Invalidate serve attempts query to refresh with metrics
      queryClient.invalidateQueries({ queryKey: ['serve-attempts'] });
      // Show different message based on whether metrics already existed
      const message = hasExistingMetrics
        ? 'Serves re-analyzed! Updated metrics are shown below.'
        : 'Serve analysis completed! Check the metrics below.';
      alert(message);
    } catch (error: unknown) {
      // Error detail is already normalized to string by axios interceptor
      const axiosError = error as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      const errorMessage =
        axiosError?.response?.data?.detail ||
        axiosError?.message ||
        'Failed to analyze serves. Please try again.';
      alert(errorMessage);
    } finally {
      setIsAnalyzingServes(false);
    }
  }, [videoId, serveAttempts, queryClient]);

  return (
    <div className="analysis-dashboard">
      {/* Header - Compact title bar */}
      <div className="analysis-dashboard__header">
        <div className="analysis-dashboard__header-content">
          <h1 className="analysis-dashboard__title">{videoFilename}</h1>
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
            hasPoseData={analysisStatus?.has_analysis || false}
            controlsBelow={true}
            onNavigateReady={handleNavigateReady}
            isDemo={false}
            naturalScroll={naturalScroll}
          />

          <KeyboardShortcutsBanner
            naturalScroll={naturalScroll}
            onNaturalScrollChange={setNaturalScroll}
          />
        </div>

        {/* Right Column - Analysis Panel */}
        <div className="analysis-dashboard__analysis-column">
          {!analysisStatus?.has_analysis && (
            <>
              {(analysisState.status === 'starting' ||
                analysisState.status === 'processing') && (
                <div className="analysis-dashboard__progress-card">
                  <ProgressBar
                    status={analysisState.status}
                    showPercentage={false}
                    showStatus={true}
                    size="medium"
                    animated={true}
                    indeterminate={true}
                  />
                </div>
              )}
              {analysisState.status === 'idle' && (
                <button
                  className="analysis-dashboard__analyze-btn"
                  onClick={handleFocusAnalysis}
                  disabled={isAnalysisLoading}
                >
                  Track Body Movement
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
                    Retry Body Tracking
                  </button>
                </div>
              )}
            </>
          )}
          {analysisStatus?.has_analysis && serveAttempts.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              <button
                className="analysis-dashboard__analyze-btn"
                onClick={handleAnalyzeServes}
                disabled={isAnalyzingServes}
                style={{ width: '100%' }}
              >
                {isAnalyzingServes
                  ? 'Analyzing Serves...'
                  : serveAttempts.some(
                        (sa) =>
                          sa.elbow_angle_at_contact !== null &&
                          sa.elbow_angle_at_contact !== undefined
                      )
                    ? 'Re-Analyze Serves'
                    : 'Analyze Serves'}
              </button>
            </div>
          )}
          <AnalysisRightPanel
            videoId={videoId}
            videoFilename={videoFilename}
            analysisStatus={analysisStatus}
            onContactClick={handleServeAttemptClick}
            isDemo={false}
          />
        </div>
      </div>
    </div>
  );
};

export default AnalysisDashboard;
