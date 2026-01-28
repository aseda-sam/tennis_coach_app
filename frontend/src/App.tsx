import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import './App.css';
import { AccountMenu } from './components/AccountMenu';
import AnalysisDashboard from './components/AnalysisDashboard';
import { AuthForm } from './components/AuthForm';
import DemoDashboard from './components/DemoDashboard';
import DemoLanding from './components/DemoLanding';
import { CloseIcon, VideoIcon } from './components/Icons';
import VideoList from './components/VideoList';
import VideoUpload from './components/VideoUpload';
import { useAuth } from './hooks/useAuth';
import { videoApi } from './services/api';
import { VideoMetadata } from './types/video';

function App() {
  const profile = process.env.REACT_APP_PROFILE || 'local';
  const { user, loading, signOut } = useAuth();
  const queryClient = useQueryClient();
  const [currentView, setCurrentView] = useState<
    'list' | 'dashboard' | 'demo-landing' | 'demo-dashboard'
  >('demo-landing');
  const [selectedVideo, setSelectedVideo] = useState<VideoMetadata | null>(
    null
  );
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const handleVideoUploaded = (video: VideoMetadata) => {
    // Invalidate videos cache to refetch the list with the new video
    queryClient.invalidateQueries({ queryKey: ['videos'] });
    setIsUploadModalOpen(false);
    // Redirect to Library to see the uploaded video
    setCurrentView('list');
  };

  const handleVideoDeleted = () => {
    // Refresh the list view
    setCurrentView('list');
  };

  const handleViewAnalysis = (video: VideoMetadata) => {
    setSelectedVideo(video);
    setCurrentView('dashboard');
  };

  const handleBackToList = () => {
    setCurrentView('list');
    setSelectedVideo(null);
  };

  const handleTryDemo = () => {
    setCurrentView('demo-dashboard');
  };

  const handleOpenUploadModal = () => {
    // Gate upload behind login (unless local profile)
    if (profile === 'local' || user) {
      setIsUploadModalOpen(true);
    } else {
      // If not logged in, navigate to Library which will show auth form
      setCurrentView('list');
    }
  };

  const handleExitDemoToUpload = () => {
    handleOpenUploadModal();
  };

  const handleUploadFromHome = () => {
    handleOpenUploadModal();
  };

  const handleGetStarted = () => {
    // If logged out, navigate to list which will show auth form
    // If logged in, open upload modal
    if (user) {
      handleOpenUploadModal();
    } else {
      setCurrentView('list');
    }
  };

  const handleLogout = async () => {
    try {
      await signOut();
      // After logout, stay on home page
      setCurrentView('demo-landing');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  // Prefetch demo video metadata and URL when landing page is shown
  useEffect(() => {
    if (currentView === 'demo-landing') {
      // Fetch demo metadata (using fetchQuery to get the data)
      queryClient
        .fetchQuery<VideoMetadata, Error>({
          queryKey: ['demo-video'],
          queryFn: async () => {
            return await videoApi.getDemoVideo();
          },
          staleTime: 5 * 60 * 1000, // 5 minutes
        })
        .then((demoVideo) => {
          if (demoVideo?.id) {
            // Prefetch video URL after metadata is available
            const expiresIn = 3600;
            queryClient
              .prefetchQuery<string>({
                queryKey: ['video-url', demoVideo.id, expiresIn],
                queryFn: async () => {
                  return await videoApi.getVideoUrl(demoVideo.id, expiresIn);
                },
                staleTime: expiresIn * 1000 * 0.9, // Cache for 90% of expiry time
                gcTime: expiresIn * 1000, // Keep in cache for full expiry time
              })
              .then(() => {
                // Get the URL from cache to add preconnect link
                const url = queryClient.getQueryData<string>([
                  'video-url',
                  demoVideo.id,
                  expiresIn,
                ]);
                if (url) {
                  try {
                    const urlObj = new URL(url);
                    const origin = urlObj.origin;

                    // Check if preconnect link already exists
                    const existingLink = document.querySelector(
                      `link[rel="preconnect"][href="${origin}"]`
                    );

                    if (!existingLink) {
                      const link = document.createElement('link');
                      link.rel = 'preconnect';
                      link.href = origin;
                      link.crossOrigin = 'anonymous';
                      document.head.appendChild(link);
                    }
                  } catch (e) {
                    // Silently fail if URL parsing fails (e.g., relative URL)
                    console.debug(
                      'Failed to parse demo video URL for preconnect:',
                      e
                    );
                  }
                }
              })
              .catch((error) => {
                // Silently handle prefetch errors - demo will still work
                console.debug('Failed to prefetch demo video URL:', error);
              });
          }
        })
        .catch((error) => {
          // Silently handle prefetch errors - demo will still work
          console.debug('Failed to fetch demo video metadata:', error);
        });
    }
  }, [currentView, queryClient]);

  if (loading) {
    return (
      <div className="App">
        <div className="app-container">
          <div style={{ textAlign: 'center', padding: '50px' }}>Loading...</div>
        </div>
      </div>
    );
  }

  // Show auth form only for protected views (list, dashboard) when not logged in
  // Home (demo-landing) and demo-dashboard are accessible without login
  const requiresAuth = ['list', 'dashboard'].includes(currentView);
  const showAuthForm = profile !== 'local' && !user && requiresAuth;

  const renderHeader = () => {
    // Header with tabs for all views (including homepage for returning users)
    return (
      <div className="app-header">
        <div className="app-header-wrapper">
          <div className="app-header-left">
            <button
              className="app-brand"
              onClick={() => setCurrentView('demo-landing')}
              aria-label="Go to home"
            >
              <div className="app-logo">
                <VideoIcon size={20} color="white" />
              </div>
              <h1 className="app-title">Tennis Coach</h1>
            </button>
          </div>

          <div
            className="app-header-center"
            role="tablist"
            aria-label="Primary navigation"
          >
            <div className="view-toggle">
              <button
                type="button"
                role="tab"
                className={`view-toggle-btn ${currentView === 'demo-landing' ? 'active' : ''}`}
                onClick={() => setCurrentView('demo-landing')}
                aria-selected={currentView === 'demo-landing'}
              >
                Home
              </button>
              <button
                type="button"
                role="tab"
                className={`view-toggle-btn ${currentView === 'list' ? 'active' : ''}`}
                onClick={() => setCurrentView('list')}
                aria-selected={currentView === 'list'}
              >
                Library
              </button>
              <button
                type="button"
                role="tab"
                className={`view-toggle-btn ${currentView === 'demo-dashboard' ? 'active' : ''}`}
                onClick={() => setCurrentView('demo-dashboard')}
                aria-selected={currentView === 'demo-dashboard'}
              >
                Demo
              </button>
            </div>
          </div>

          <div className="app-header-right">
            {user ? (
              <AccountMenu onLogout={handleLogout} />
            ) : (
              <button className="sign-in-btn" onClick={handleGetStarted}>
                Sign In
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case 'demo-landing':
        return (
          <div className="app-container">
            <DemoLanding
              onTryDemo={handleTryDemo}
              onUploadVideo={handleUploadFromHome}
              user={user}
            />
          </div>
        );

      case 'demo-dashboard':
        return (
          <DemoDashboard
            onClose={() => {
              // Always go back to demo landing page
              setCurrentView('demo-landing');
            }}
            onExitToUpload={handleExitDemoToUpload}
          />
        );

      case 'list':
        return (
          <div className="app-container">
            <VideoList
              onVideoDeleted={handleVideoDeleted}
              onViewAnalysis={handleViewAnalysis}
            />
          </div>
        );

      case 'dashboard':
        if (!selectedVideo) {
          return (
            <div className="app-container">
              <div className="error-message">
                <p>No video selected. Please go back and select a video.</p>
                <button onClick={handleBackToList}>Back to Videos</button>
              </div>
            </div>
          );
        }

        return (
          <AnalysisDashboard
            videoId={selectedVideo.id}
            videoFilename={selectedVideo.filename}
            videoUrl={`${process.env.REACT_APP_API_URL || 'http://localhost:8000/v0'}/videos/${selectedVideo.id}/stream`}
            onClose={handleBackToList}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div className="App">
      {renderHeader()}
      {showAuthForm ? (
        <div className="app-container">
          <AuthForm />
        </div>
      ) : (
        renderCurrentView()
      )}

      {/* Upload Modal - Shared across all views */}
      {isUploadModalOpen && (
        <div
          className="upload-modal-overlay"
          onClick={() => setIsUploadModalOpen(false)}
        >
          <div className="upload-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Upload Video</h2>
              <button
                className="close-btn"
                onClick={() => setIsUploadModalOpen(false)}
                aria-label="Close"
              >
                <CloseIcon size={18} />
              </button>
            </div>
            <div className="modal-content">
              <VideoUpload onUploadSuccess={handleVideoUploaded} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
