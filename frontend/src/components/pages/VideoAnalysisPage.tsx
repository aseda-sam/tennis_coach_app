import React, { Suspense } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { videoApi } from '../../services/api';
import LoadingIndicator from '../LoadingIndicator';

const AnalysisDashboard = React.lazy(() => import('../AnalysisDashboard'));

function VideoAnalysisPage() {
  const { videoId } = useParams<{ videoId: string }>();
  const navigate = useNavigate();

  const numericId = videoId ? Number(videoId) : NaN;

  const {
    data: video,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['video', numericId],
    queryFn: () => videoApi.getVideo(numericId),
    enabled: !isNaN(numericId),
  });

  if (!videoId || isNaN(numericId)) {
    return <Navigate to="/library" replace />;
  }

  if (isLoading) {
    return (
      <div className="app-container">
        <div className="app-loading">
          <LoadingIndicator size="lg" label="Loading video..." />
        </div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="app-container">
        <div className="error-message">
          <p>Video not found or could not be loaded.</p>
          <button onClick={() => navigate('/library')}>Back to Library</button>
        </div>
      </div>
    );
  }

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
        videoId={video.id}
        videoFilename={video.filename}
        videoUrl={`${process.env.REACT_APP_API_URL || 'http://localhost:8000/v0'}/videos/${video.id}/stream`}
        onClose={() => navigate('/library')}
      />
    </Suspense>
  );
}

export default VideoAnalysisPage;
