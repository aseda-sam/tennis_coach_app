import { useState } from 'react';
import './App.css';
import AnalysisDashboard from './components/AnalysisDashboard';
import VideoList from './components/VideoList';
import VideoUpload from './components/VideoUpload';
import { AuthForm } from './components/AuthForm';
import { ListIcon, UploadIcon } from './components/Icons';
import { useAuth } from './hooks/useAuth';
import { VideoMetadata } from './types/video';

function App() {
  const profile = process.env.REACT_APP_PROFILE || 'local';
  const { user, loading, signOut } = useAuth();
  const [currentView, setCurrentView] = useState<'upload' | 'list' | 'dashboard'>('upload');
  const [selectedVideo, setSelectedVideo] = useState<VideoMetadata | null>(null);

  const handleVideoUploaded = () => {
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

  if (loading) {
    return (
      <div className="App">
        <div className="app-container">
          <div style={{ textAlign: 'center', padding: '50px' }}>Loading...</div>
        </div>
      </div>
    );
  }

  // Show auth form only if profile is not local and user is not authenticated
  if (profile !== 'local' && !user) {
    return (
      <div className="App">
        <div className="app-container">
          <AuthForm />
        </div>
      </div>
    );
  }

  const renderHeader = () => {
    if (currentView === 'dashboard') return null;

    return (
      <div className="app-header">
        <div className="app-header-left">
          <h1 className="app-title">Tennis Coach</h1>
        </div>

        <div className="app-header-center" role="tablist" aria-label="Primary navigation">
          <div className="view-toggle">
            <button
              type="button"
              className={`view-toggle-btn ${currentView === 'upload' ? 'active' : ''}`}
              onClick={() => setCurrentView('upload')}
              aria-selected={currentView === 'upload'}
            >
              <UploadIcon size={18} />
              Upload
            </button>
            <button
              type="button"
              className={`view-toggle-btn ${currentView === 'list' ? 'active' : ''}`}
              onClick={() => setCurrentView('list')}
              aria-selected={currentView === 'list'}
            >
              <ListIcon size={18} />
              My Videos
            </button>
          </div>
        </div>

        <div className="app-header-right">
          <button className="logout-btn" onClick={signOut}>
            Logout
          </button>
        </div>
      </div>
    );
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case 'upload':
        return (
          <div className="app-container">
            {renderHeader()}
            
            <div className="upload-section">
              <div className="header-content">
                <p className="app-subtitle">
                  Upload your tennis video and get personalized feedback
                </p>
                <p className="app-description">
                  Share a video of your serve or groundstrokes, and we'll help you understand 
                  what's working well and where you can improve. More shot types coming soon!
                </p>
              </div>

              <VideoUpload onUploadSuccess={handleVideoUploaded} />
            </div>
          </div>
        );

      case 'list':
        return (
          <div className="app-container">
            {renderHeader()}
            <VideoList onVideoDeleted={handleVideoDeleted} onViewAnalysis={handleViewAnalysis} />
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
      {renderCurrentView()}
    </div>
  );
}

export default App;
