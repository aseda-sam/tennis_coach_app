import React, { Suspense, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { videoApi } from '../../services/api';
import { PublicDemoVideo } from '../../types/video';
import { useAuth } from '../../hooks/useAuth';
import { useUploadModal } from '../layouts/AppLayout';
import LoadingIndicator from '../LoadingIndicator';
import { useDemoTour } from '../DemoTour/useDemoTour';
import { TourPlaybackControls } from '../DemoTour/tourSteps';
import DemoTourOverlay from '../DemoTour/DemoTourOverlay';
import DemoUploadPill from '../DemoTour/DemoUploadPill';

const AnalysisDashboard = React.lazy(() => import('../AnalysisDashboard'));

function DemoPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { openUploadModal } = useUploadModal();

  const {
    data: demoVideo,
    isLoading,
    error,
  } = useQuery<PublicDemoVideo, Error>({
    queryKey: ['demo-video'],
    queryFn: async () => {
      return await videoApi.getDemoVideo();
    },
    staleTime: 5 * 60 * 1000,
  });

  const handleExitToUpload = () => {
    const profile = import.meta.env.VITE_PROFILE || 'local';
    if (profile === 'local' || user) {
      openUploadModal();
    } else {
      navigate('/library');
    }
  };

  const tourControlsRef = useRef<TourPlaybackControls>(null);

  const tour = useDemoTour({
    enabled: !!demoVideo && !isLoading,
    controlsRef: tourControlsRef,
  });

  if (isLoading) {
    return (
      <div className="app-container">
        <div className="app-loading">
          <LoadingIndicator size="lg" label="Setting up the demo..." />
        </div>
      </div>
    );
  }

  if (error || !demoVideo) {
    return (
      <div className="app-container">
        <div className="error-message">
          <p>Demo video unavailable. Please try again later.</p>
          <button onClick={() => navigate('/')}>Back to Home</button>
        </div>
      </div>
    );
  }

  const videoUrl = `${import.meta.env.VITE_API_URL || 'http://localhost:8000/v0'}/videos/${demoVideo.id}/stream`;

  return (
    <Suspense
      fallback={
        <div className="app-container">
          <div className="app-loading">
            <LoadingIndicator size="lg" label="Pulling up the analysis..." />
          </div>
        </div>
      }
    >
      <AnalysisDashboard
        videoId={demoVideo.id}
        videoFilename={demoVideo.filename}
        videoUrl={videoUrl}
        onClose={() => navigate('/')}
        isDemo={true}
        onExitToUpload={handleExitToUpload}
        tourControlsRef={tourControlsRef}
        onRestartTour={tour.restart}
      />

      {tour.isActive && tour.currentStep && (
        <DemoTourOverlay
          step={tour.currentStep}
          stepIndex={tour.currentStepIndex}
          totalSteps={tour.totalSteps}
          onNext={tour.next}
          onPrev={tour.prev}
          onEnd={tour.end}
        />
      )}

      {!tour.isActive && tour.tourCompleted && (
        <DemoUploadPill onUpload={handleExitToUpload} />
      )}
    </Suspense>
  );
}

export default DemoPage;
