import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import './App.css';
import AnalysisDashboard from './components/AnalysisDashboard';
import { AuthForm } from './components/AuthForm';
import DemoDashboard from './components/DemoDashboard';
import DemoLanding from './components/DemoLanding';
import { VideoIcon } from './components/Icons';
import VideoList from './components/VideoList';
import VideoUpload from './components/VideoUpload';
import { useAuth } from './hooks/useAuth';
import { VideoMetadata } from './types/video';

function App() {
  const profile = process.env.REACT_APP_PROFILE || 'local';
  const { user, loading, signOut } = useAuth();
  const queryClient = useQueryClient();
  const [currentView, setCurrentView] = useState<
    'upload' | 'list' | 'dashboard' | 'demo-landing' | 'demo-dashboard'
  >('demo-landing');
  const [selectedVideo, setSelectedVideo] = useState<VideoMetadata | null>(
    null
  );

  const handleVideoUploaded = () => {
    // Invalidate videos cache to refetch the list with the new video
    queryClient.invalidateQueries({ queryKey: ['videos'] });
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

  const handleExitDemoToUpload = () => {
    // If user is logged in, go to upload; otherwise show auth
    if (user) {
      setCurrentView('upload');
    } else {
      // Show auth form by setting a special state or redirecting
      // For now, we'll handle this in the upload view rendering
      setCurrentView('upload');
    }
  };

  const handleUploadFromHome = () => {
    // Gate upload behind login
    if (user) {
      setCurrentView('upload');
    } else {
      // Show auth form by navigating to upload (which will show auth form)
      setCurrentView('upload');
    }
  };

  const handleGetStarted = () => {
    // Show auth form by navigating to upload (which will check auth and show auth form)
    setCurrentView('upload');
  };

  if (loading) {
    return (
      <div className="App">
        <div className="app-container">
          <div style={{ textAlign: 'center', padding: '50px' }}>Loading...</div>
        </div>
      </div>
    );
  }

  // Show auth form only for protected views (upload, list, dashboard) when not logged in
  // Home (demo-landing) and demo-dashboard are accessible without login
  const requiresAuth = ['upload', 'list', 'dashboard'].includes(currentView);
  if (profile !== 'local' && !user && requiresAuth) {
    return (
      <div className="App">
        <div className="app-container">
          <AuthForm />
        </div>
      </div>
    );
  }

  const renderHeader = () => {
    // Special header for demo-landing (Home page)
    if (currentView === 'demo-landing') {
      return (
        <div className="app-header">
          <div className="app-header-wrapper">
            <div className="app-header-left">
              <div className="app-brand">
                <div className="app-logo">
                  <VideoIcon size={20} color="white" />
                </div>
                <h1 className="app-title">Tennis Coach</h1>
              </div>
            </div>

            <div className="app-header-right">
              {user ? (
                <button 
                  className="logout-btn" 
                  onClick={async () => {
                    try {
                      await signOut();
                      // After logout, stay on home page
                      setCurrentView('demo-landing');
                    } catch (error) {
                      console.error('Logout failed:', error);
                    }
                  }}
                >
                  Logout
                </button>
              ) : (
                <button 
                  className="get-started-btn" 
                  onClick={handleGetStarted}
                >
                  Get Started
                </button>
              )}
            </div>
          </div>
        </div>
      );
    }

    // Standard header for other views
    return (
      <div className="app-header">
        <div className="app-header-wrapper">
          <div className="app-header-left">
            <div className="app-brand">
              <div className="app-logo">
                <VideoIcon size={20} color="white" />
              </div>
              <h1 className="app-title">Tennis Coach</h1>
            </div>
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
                className="view-toggle-btn"
                onClick={() => setCurrentView('demo-landing')}
                aria-selected={false}
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
            <button 
              className="logout-btn" 
              onClick={async () => {
                try {
                  await signOut();
                  // After logout, go back to home
                  setCurrentView('demo-landing');
                } catch (error) {
                  console.error('Logout failed:', error);
                }
              }}
            >
              Logout
            </button>
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

      case 'upload':
        // Gate upload behind login (unless local profile)
        if (profile !== 'local' && !user) {
          return (
            <div className="App">
              <div className="app-container">
                <AuthForm />
              </div>
            </div>
          );
        }
        return (
          <div className="app-container">
            <div className="upload-section">
              <div className="header-content">
                <p className="app-subtitle">
                  Upload your tennis video and get personalized feedback
                </p>
                <p className="app-description">
                  Share a video of your serve or groundstrokes, and we'll help
                  you understand what's working well and where you can improve.
                  More shot types coming soon!
                </p>
              </div>

              <VideoUpload onUploadSuccess={handleVideoUploaded} />
            </div>
          </div>
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
      {renderCurrentView()}
    </div>
  );
}

export default App;
