import { useQuery } from '@tanstack/react-query';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { videoApi } from '../services/api';
import { VideoMetadata } from '../types/video';
import AnalysisRightPanel from './AnalysisRightPanel';
import './DemoDashboard.css';
import { UploadIcon } from './Icons';
import KeyboardShortcutsBanner from './KeyboardShortcutsBanner';
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
  const { user } = useAuth();

  const canEditDemo = useMemo(() => {
    if (!user) {
      return false;
    }
    if (user.user_metadata?.is_admin) {
      return true;
    }
    return user.id === 'ca4a6fcc-4cdf-435c-a22f-1c8c02ce4c5f';
  }, [user]);
  const isDemoReadOnly = !canEditDemo;

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
  const { data: analysisStatus } = useVideoAnalysisStatus(
    demoVideo?.id || 0
  );

  const [videoPlayerNavigate, setVideoPlayerNavigate] = useState<
    ((serveAttemptId: number) => void) | null
  >(null);
  const [isTourOpen, setIsTourOpen] = useState(false);

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
        title: 'Serve Attempt Ranges',
        content:
          'Jump to key moments using the serve attempt ranges on the timeline.',
        placement: 'top',
      },
      {
        target: 'analysis-panel',
        title: 'Metrics & Analysis',
        content:
          'Review metrics derived from existing serve attempts, including elbow angles and shot types.',
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

  // Demo mode is read-only for non-admin/demo editor users.

  if (isLoadingDemo) {
    return (
      <div className="demo-dashboard">
        <div className="demo-dashboard__loading">Loading demo...</div>
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
            />
          </div>
          <KeyboardShortcutsBanner isDemo={isDemoReadOnly} />
        </div>

        {/* Right Column - Upload CTA & Analysis Panel */}
        <div className="demo-dashboard__analysis-column">
          {/* Friendly Upload CTA */}
          <div
            className="demo-dashboard__upload-cta"
            data-tour="upload-cta"
          >
            <div className="demo-dashboard__upload-cta-content">
              <h3 className="demo-dashboard__upload-cta-title">
                Ready to analyze your own video?
              </h3>
              <p className="demo-dashboard__upload-cta-description">
                Now that you've seen how it works, upload your tennis video and get personalized feedback on your technique.
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
    </div>
  );
};

export default DemoDashboard;
