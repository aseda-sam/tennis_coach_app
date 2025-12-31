import { useState } from 'react';
import './App.css';
import AnalysisDashboard from './components/AnalysisDashboard';
import VideoList from './components/VideoList';
import VideoUpload from './components/VideoUpload';
import { AuthForm } from './components/AuthForm';
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

  const renderCurrentView = () => {
    switch (currentView) {
      case 'upload':
        return (
          <div className="app-container">
            <div className="upload-section">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <div>
                  <h1 className="app-title">Tennis Video Analyzer</h1>
                  <p className="app-subtitle">
                    Upload your tennis videos for advanced performance analysis and technique insights
                  </p>
                </div>
                <button 
                  onClick={signOut}
                  style={{
                    padding: '8px 16px',
                    background: '#ef4444',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  Logout
                </button>
              </div>
              <VideoUpload onUploadSuccess={handleVideoUploaded} />
              <div className="view-videos-section">
                <button 
                  className="view-videos-btn"
                  onClick={() => setCurrentView('list')}
                >
                  View My Videos
                </button>
              </div>
            </div>
          </div>
        );

      case 'list':
        return (
          <div className="app-container">
            <div className="list-section">
              <div className="list-header">
                <button 
                  className="back-to-upload-btn"
                  onClick={() => setCurrentView('upload')}
                >
                  ← Back to Upload
                </button>
                <button 
                  className="upload-new-btn"
                  onClick={() => setCurrentView('upload')}
                >
                  Upload New Video
                </button>
                <button 
                  onClick={signOut}
                  style={{
                    padding: '8px 16px',
                    background: '#ef4444',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    marginLeft: '10px',
                  }}
                >
                  Logout
                </button>
              </div>
              <VideoList 
                onVideoDeleted={handleVideoDeleted}
                onViewAnalysis={handleViewAnalysis}
              />
            </div>
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
