import React, { useCallback, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { videoApi } from '../services/api';
import { useVideoAnalysisStatus } from '../hooks/useVideos';
import { VideoMetadata } from '../types/video';
import './DemoDashboard.css';
import AnalysisRightPanel from './AnalysisRightPanel';
import { ArrowBackIcon } from './Icons';
import KeyboardShortcutsBanner from './KeyboardShortcutsBanner';
import VideoPlayer from './VideoPlayer';

interface DemoDashboardProps {
  onClose: () => void;
  onExitToUpload: () => void;
}

const DemoDashboard: React.FC<DemoDashboardProps> = ({
  onClose,
  onExitToUpload,
}) => {

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
    ((contactId: number) => void) | null
  >(null);

  const handleContactClick = useCallback(
    (contactId: number) => {
      videoPlayerNavigate?.(contactId);
    },
    [videoPlayerNavigate]
  );

  const handleNavigateReady = useCallback(
    (navigateFn: (contactId: number) => void) => {
      setVideoPlayerNavigate(() => navigateFn);
    },
    []
  );

  // Note: Demo mode is fully read-only. Contact creation is blocked at the API level.
  // These handlers are available for navigation between contacts but cannot create new ones.

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
          <button onClick={onClose} className="demo-dashboard__back-btn">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const videoUrl = `${process.env.REACT_APP_API_URL || 'http://localhost:8000/v0'}/videos/${demoVideo.id}/stream`;

  return (
    <div className="demo-dashboard">
      {/* Demo Banner */}
      <div className="demo-dashboard__banner">
        <div className="demo-dashboard__banner-content">
          <span className="demo-dashboard__banner-icon">🎾</span>
          <span className="demo-dashboard__banner-text">
            Demo Mode - Explore features without saving changes
          </span>
        </div>
      </div>

      {/* Header - Only show if accessed from demo-landing, otherwise use app header */}
      <div className="demo-dashboard__header">
        <button 
          className="demo-dashboard__back-btn" 
          onClick={onClose}
          title="Back to previous view"
        >
          <ArrowBackIcon size={16} />
          Back
        </button>
        <div className="demo-dashboard__header-content">
          <h1 className="demo-dashboard__title">Demo: Serve Analysis</h1>
          <p className="demo-dashboard__subtitle">{demoVideo.filename}</p>
        </div>
        <button
          className="demo-dashboard__exit-btn"
          onClick={onExitToUpload}
          type="button"
        >
          Upload Your Video
        </button>
      </div>

      {/* Main Content */}
      <div className="demo-dashboard__content">
        {/* Left Column - Video Player */}
        <div className="demo-dashboard__video-column">
          <VideoPlayer
            videoUrl={videoUrl}
            title={demoVideo.filename}
            showControls={true}
            aspectRatioMode="contain"
            videoId={demoVideo.id}
            showPostureAnalysis={false}
            hasPoseData={analysisStatus?.has_analysis || false}
            controlsBelow={true}
            onNavigateReady={handleNavigateReady}
            isDemo={true}
          />
          <KeyboardShortcutsBanner isDemo={true} />
        </div>

        {/* Right Column - Analysis Panel */}
        <div className="demo-dashboard__analysis-column">
          <AnalysisRightPanel
            videoId={demoVideo.id}
            videoFilename={demoVideo.filename}
            analysisStatus={analysisStatus}
            onContactClick={handleContactClick}
            isDemo={true}
          />
        </div>
      </div>
    </div>
  );
};

export default DemoDashboard;
