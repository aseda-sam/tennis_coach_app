import { useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAdmin } from '../hooks/useAdmin';
import { useServeAttempts } from '../hooks/useServeAttempts';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { videoApi } from '../services/api';
import { serveAttemptApi } from '../services/serveAttemptApi';
import { VideoMetadata } from '../types/video';
import AnalysisRightPanel from './AnalysisRightPanel';
import './DemoDashboard.css';
import { ArrowBackIcon, UploadIcon } from './Icons';
import KeyboardShortcutsModal from './KeyboardShortcutsModal';
import LoadingIndicator from './LoadingIndicator';
import Tour, { TourStep } from './Tour';
import VideoPlayer from './VideoPlayer';

interface DemoDashboardProps {
  onClose: () => void;
  onExitToUpload: () => void;
}

const DemoDashboard: React.FC<DemoDashboardProps> = ({
  onClose,
  onExitToUpload,
}) => {
  const { isAdmin } = useAdmin();
  const isDemoReadOnly = !isAdmin;
  const queryClient = useQueryClient();

  // Fetch demo video
  const {
    data: demoVideo,
    isLoading: isLoadingDemo,
    error: demoError,
  } = useQuery<VideoMetadata, Error>({
    queryKey: ['demo-video'],
    queryFn: async () => {
      return await videoApi.getDemoVideo();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Use React Query hook for analysis status
  const { data: analysisStatus } = useVideoAnalysisStatus(demoVideo?.id || 0);

  // Get serve attempts for this video using the hook (for admin analysis functionality)
  const { serveAttempts } = useServeAttempts({
    videoId: demoVideo?.id,
    filters: demoVideo?.id ? { video_id: demoVideo.id } : undefined,
    autoRefresh: true,
  });

  const hasPoseAnalysis = analysisStatus?.has_analysis || false;
  const hasServeAttempts = serveAttempts.length > 0;
  const showStatusWarning =
    isAdmin && (!hasPoseAnalysis || !hasServeAttempts);

  const [videoPlayerNavigate, setVideoPlayerNavigate] = useState<
    ((serveAttemptId: number) => void) | null
  >(null);
  const [isTourOpen, setIsTourOpen] = useState(false);
  const [naturalScroll, setNaturalScroll] = useState(false);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);
  const [isAnalyzingServes, setIsAnalyzingServes] = useState(false);

  // Keyboard shortcut listener for ?
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }
      if (e.key === '?' || (e.key === '/' && e.shiftKey)) {
        e.preventDefault();
        setShowKeyboardShortcuts(true);
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const tourSteps: TourStep[] = useMemo(
    () => [
      {
        target: 'video-player',
        title: 'Video Player',
        content:
          'Play the demo clip and scrub through frames using the timeline below.',
        placement: 'bottom',
      },
      {
        target: 'serve-attempt-ranges',
        title: 'Key Moments',
        content: 'Navigate key moments directly from the timeline.',
        placement: 'top',
      },
      {
        target: 'analysis-panel',
        title: 'Metrics & Analysis',
        content:
          'Review pose and key-moment metrics to understand your serve mechanics.',
        placement: 'left',
      },
      {
        target: 'upload-cta',
        title: 'Ready to Upload?',
        content:
          'Ready to analyze your own video? Upload to see personalized feedback on your technique.',
        placement: 'left',
      },
    ],
    []
  );

  useEffect(() => {
    const tourCompleted = localStorage.getItem('demoTourCompleted');
    if (!tourCompleted && demoVideo) {
      // Small delay to ensure DOM is ready
      const timer = setTimeout(() => {
        setIsTourOpen(true);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [demoVideo]);

  const handleTourComplete = useCallback(() => {
    localStorage.setItem('demoTourCompleted', 'true');
  }, []);

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
    if (!demoVideo?.id) return;
    if (serveAttempts.length === 0) {
      alert('Please tag key moments first before analyzing.');
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
      await serveAttemptApi.analyzeServes(demoVideo.id);
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
  }, [demoVideo?.id, serveAttempts, queryClient]);

  // Demo mode is read-only for non-admin users.

  if (isLoadingDemo) {
    return (
      <div className="demo-dashboard">
        <div className="demo-dashboard__loading">
          <LoadingIndicator size="lg" label="Loading demo..." />
        </div>
      </div>
    );
  }

  if (demoError || !demoVideo) {
    return (
      <div className="demo-dashboard">
        <div className="demo-dashboard__error">
          <p>Demo video unavailable. Please try again later.</p>
        </div>
      </div>
    );
  }

  const videoUrl = `${process.env.REACT_APP_API_URL || 'http://localhost:8000/v0'}/videos/${demoVideo.id}/stream`;

  return (
    <div className="demo-dashboard">
      {/* Status Warning for Admins */}
      {showStatusWarning && (
        <div className="demo-dashboard__status-warning">
          <div className="demo-dashboard__status-warning-content">
            <strong>Demo Status:</strong>
            {!hasPoseAnalysis && (
              <span className="demo-dashboard__status-item warning">
                ⚠ Missing pose analysis
              </span>
            )}
            {!hasServeAttempts && (
              <span className="demo-dashboard__status-item warning">
                ⚠ No key moments tagged
              </span>
            )}
            <span className="demo-dashboard__status-hint">
              Use the Admin tab to manage demo videos.
            </span>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="demo-dashboard__content">
        {/* Left Column - Video Player */}
        <div className="demo-dashboard__video-column">
          <div data-tour="video-player">
            <VideoPlayer
              videoUrl={videoUrl}
              title={demoVideo.filename}
              showControls={true}
              aspectRatioMode="contain"
              videoId={demoVideo.id}
              hasPoseData={analysisStatus?.has_analysis || false}
              controlsBelow={true}
              onNavigateReady={handleNavigateReady}
              isDemo={isDemoReadOnly}
              naturalScroll={naturalScroll}
            />
          </div>
          <div className="demo-dashboard__shortcuts-hint">
            Press <kbd>?</kbd> for keyboard shortcuts
          </div>
        </div>

        {/* Right Column - Upload CTA & Analysis Panel */}
        <div className="demo-dashboard__analysis-column">
          {/* Friendly Upload CTA */}
          <div className="demo-dashboard__upload-cta" data-tour="upload-cta">
            <div className="demo-dashboard__upload-cta-content">
              <button
                className="demo-dashboard__back-button"
                onClick={onClose}
                type="button"
              >
                <ArrowBackIcon size={16} />
                Back to Home
              </button>
              <h3 className="demo-dashboard__upload-cta-title">
                Ready to analyze your own video?
              </h3>
              <p className="demo-dashboard__upload-cta-description">
                Now that you've seen how it works, upload your tennis video and
                get personalized feedback on your technique.
              </p>
              <button
                className="demo-dashboard__upload-cta-button"
                onClick={onExitToUpload}
                type="button"
              >
                <UploadIcon size={20} />
                Upload Your Video
              </button>
            </div>
          </div>

          {/* Admin-only: Serve Analysis Button */}
          {isAdmin &&
            analysisStatus?.has_analysis &&
            serveAttempts.length > 0 && (
              <div className="demo-dashboard__actions">
                <button
                  className="demo-dashboard__action-btn demo-dashboard__action-btn--primary"
                  onClick={handleAnalyzeServes}
                  disabled={isAnalyzingServes}
                >
                  {isAnalyzingServes
                    ? 'Analyzing…'
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

          <div data-tour="analysis-panel">
            <AnalysisRightPanel
              videoId={demoVideo.id}
              videoFilename={demoVideo.filename}
              analysisStatus={analysisStatus}
              onContactClick={handleServeAttemptClick}
              isDemo={isDemoReadOnly}
            />
          </div>
        </div>
      </div>

      <Tour
        steps={tourSteps}
        isOpen={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        onComplete={handleTourComplete}
        showSkip={true}
      />

      <KeyboardShortcutsModal
        isOpen={showKeyboardShortcuts}
        onClose={() => setShowKeyboardShortcuts(false)}
        isDemo={isDemoReadOnly}
        naturalScroll={naturalScroll}
        onNaturalScrollChange={setNaturalScroll}
      />
    </div>
  );
};

export default DemoDashboard;
