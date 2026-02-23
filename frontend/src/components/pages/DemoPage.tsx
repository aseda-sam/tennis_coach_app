import React, { Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { videoApi } from '../../services/api';
import { VideoMetadata } from '../../types/video';
import { useAuth } from '../../hooks/useAuth';
import { useUploadModal } from '../layouts/AppLayout';
import LoadingIndicator from '../LoadingIndicator';

const AnalysisDashboard = React.lazy(() => import('../AnalysisDashboard'));

function DemoPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { openUploadModal } = useUploadModal();

  const {
    data: demoVideo,
    isLoading,
    error,
  } = useQuery<VideoMetadata, Error>({
    queryKey: ['demo-video'],
    queryFn: async () => {
      return await videoApi.getDemoVideo();
    },
    staleTime: 5 * 60 * 1000,
  });

  const handleExitToUpload = () => {
    const profile = process.env.REACT_APP_PROFILE || 'local';
    if (profile === 'local' || user) {
      openUploadModal();
    } else {
      navigate('/library');
    }
  };

  if (isLoading) {
    return (
      <div className="app-container">
        <div className="app-loading">
          <LoadingIndicator size="lg" label="Loading demo..." />
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

  const videoUrl = `${process.env.REACT_APP_API_URL || 'http://localhost:8000/v0'}/videos/${demoVideo.id}/stream`;

  return (
    <Suspense
      fallback={
        <div className="app-container">
          <div className="app-loading">
            <LoadingIndicator size="lg" label="Loading analysis..." />
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
      />
    </Suspense>
  );
}

export default DemoPage;
