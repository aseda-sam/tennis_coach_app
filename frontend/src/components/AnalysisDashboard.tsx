import { useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useEffect, useState } from 'react';
import { useAnalysisManager } from '../hooks/useAnalysisManager';
import { useServeAttempts } from '../hooks/useServeAttempts';
import { useServeProposals } from '../hooks/useServeProposals';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { serveAttemptApi } from '../services/serveAttemptApi';
import './AnalysisDashboard.css';
import AnalysisRightPanel from './AnalysisRightPanel';
import KeyboardShortcutsModal from './KeyboardShortcutsModal';
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
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [isFindingServes, setIsFindingServes] = useState(false);
  const [findServesMessage, setFindServesMessage] = useState<string | null>(null);

  // Get serve attempts for this video
  const { serveAttempts } = useServeAttempts({
    videoId,
    filters: { video_id: videoId },
    autoRefresh: true,
  });

  // Get serve proposals for detection functionality
  const {
    proposals,
    detectionStatus,
    runDetection,
    clearProposals,
  } = useServeProposals({
    videoId,
    autoRefresh: true,
  });

  // Keyboard shortcut listener for ?
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }

      // ? key (with or without shift) opens shortcuts
      if (e.key === '?' || (e.key === '/' && e.shiftKey)) {
        e.preventDefault();
        setShowKeyboardShortcuts(true);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Handle find serves
  const handleFindServes = useCallback(async () => {
    if (!analysisStatus?.has_analysis) {
      setFindServesMessage('Please run body tracking first.');
      setTimeout(() => setFindServesMessage(null), 3000);
      return;
    }

    // Check for existing detections
    const hasExisting = detectionStatus && (
      detectionStatus.pending_proposals > 0 ||
      detectionStatus.serve_attempts > 0
    );

    if (hasExisting && detectionStatus) {
      if (detectionStatus.serve_attempts > 0 && detectionStatus.pending_proposals === 0) {
        setFindServesMessage('Serves already tagged. Delete them to re-detect.');
        setTimeout(() => setFindServesMessage(null), 4000);
        return;
      }
      if (detectionStatus.pending_proposals > 0) {
        const confirmed = window.confirm(
          `You have ${detectionStatus.pending_proposals} pending proposal(s). Clear them and re-detect?`
        );
        if (!confirmed) return;
      }
    }

    setIsFindingServes(true);
    setFindServesMessage(null);
    try {
      const force = detectionStatus?.pending_proposals ? detectionStatus.pending_proposals > 0 : false;
      const response = await runDetection(force);
      if (response.count === 0) {
        setFindServesMessage('No serves found in this video.');
      } else {
        setFindServesMessage(`Found ${response.count} serve${response.count > 1 ? 's' : ''}!`);
      }
      setTimeout(() => setFindServesMessage(null), 4000);
    } catch (err) {
      console.error('Failed to find serves:', err);
      setFindServesMessage('Failed to find serves. Please try again.');
      setTimeout(() => setFindServesMessage(null), 4000);
    } finally {
      setIsFindingServes(false);
    }
  }, [analysisStatus, detectionStatus, runDetection]);

  // Handle clear proposals
  const handleClearProposals = useCallback(async () => {
    if (proposals.length === 0) return;
    const confirmed = window.confirm('Clear all pending serve proposals?');
    if (!confirmed) return;
    try {
      await clearProposals();
      setFindServesMessage('Proposals cleared.');
      setTimeout(() => setFindServesMessage(null), 2000);
    } catch (err) {
      console.error('Failed to clear:', err);
    }
  }, [proposals.length, clearProposals]);

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
      {/* Header - Compact title bar with keyboard shortcut hint */}
      <div className="analysis-dashboard__header">
        <div className="analysis-dashboard__header-content">
          <h1 className="analysis-dashboard__title">{videoFilename}</h1>
        </div>
        <button
          className="analysis-dashboard__shortcuts-btn"
          onClick={() => setShowKeyboardShortcuts(true)}
          title="Keyboard shortcuts (?)"
        >
          <span>?</span>
        </button>
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
        </div>

        {/* Right Column - Analysis Panel */}
        <div className="analysis-dashboard__analysis-column">
          {/* Action buttons for whole-video operations */}
          <div className="analysis-dashboard__actions">
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
                    className="analysis-dashboard__action-btn analysis-dashboard__action-btn--primary"
                    onClick={handleFocusAnalysis}
                    disabled={isAnalysisLoading}
                  >
                    Track Body Movement
                  </button>
                )}
                {analysisState.status === 'failed' && (
                  <div className="analysis-dashboard__error-card">
                    <p className="analysis-dashboard__error-message">
                      {analysisState.error || 'Analysis failed. Please try again.'}
                    </p>
                    <button
                      className="analysis-dashboard__action-btn analysis-dashboard__action-btn--primary"
                      onClick={handleFocusAnalysis}
                      disabled={isAnalysisLoading}
                    >
                      Retry Body Tracking
                    </button>
                  </div>
                )}
              </>
            )}

            {analysisStatus?.has_analysis && (
              <div className="analysis-dashboard__action-row">
                <button
                  className={`analysis-dashboard__action-btn ${
                    detectionStatus?.serve_attempts && detectionStatus.serve_attempts > 0
                      ? 'analysis-dashboard__action-btn--secondary'
                      : 'analysis-dashboard__action-btn--find'
                  }`}
                  onClick={handleFindServes}
                  disabled={isFindingServes}
                  title="Automatically detect serve positions in the video"
                >
                  {isFindingServes
                    ? 'Finding...'
                    : detectionStatus?.serve_attempts && detectionStatus.serve_attempts > 0
                      ? 'Re-find Serves'
                      : 'Find Serves'}
                </button>
                {proposals.length > 0 && (
                  <button
                    className="analysis-dashboard__action-btn analysis-dashboard__action-btn--ghost"
                    onClick={handleClearProposals}
                    title="Clear pending proposals"
                  >
                    Clear ({proposals.length})
                  </button>
                )}
              </div>
            )}

            {analysisStatus?.has_analysis && serveAttempts.length > 0 && (
              <button
                className="analysis-dashboard__action-btn analysis-dashboard__action-btn--primary"
                onClick={handleAnalyzeServes}
                disabled={isAnalyzingServes}
              >
                {isAnalyzingServes
                  ? 'Analyzing...'
                  : serveAttempts.some(
                        (sa) =>
                          sa.elbow_angle_at_contact !== null &&
                          sa.elbow_angle_at_contact !== undefined
                      )
                    ? 'Re-Analyze Serves'
                    : 'Analyze Serves'}
              </button>
            )}

            {findServesMessage && (
              <div className="analysis-dashboard__toast">
                {findServesMessage}
              </div>
            )}
          </div>

          <AnalysisRightPanel
            videoId={videoId}
            videoFilename={videoFilename}
            analysisStatus={analysisStatus}
            onContactClick={handleServeAttemptClick}
            isDemo={false}
          />
        </div>
      </div>

      {/* Keyboard Shortcuts Modal */}
      <KeyboardShortcutsModal
        isOpen={showKeyboardShortcuts}
        onClose={() => setShowKeyboardShortcuts(false)}
      />
    </div>
  );
};

export default AnalysisDashboard;
