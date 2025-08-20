import { useState } from 'react';
import './App.css';
import AnalysisDashboard from './components/AnalysisDashboard';
import VideoList from './components/VideoList';
import VideoUpload from './components/VideoUpload';
import ModernHomePage from './components/ModernHomePage';
import { VideoMetadata } from './types/video';

function App() {
  const [currentView, setCurrentView] = useState<'home' | 'upload' | 'list' | 'dashboard'>('home');
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

  const handleGetStarted = () => {
    setCurrentView('upload');
  };

  const handleViewVideos = () => {
    setCurrentView('list');
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case 'home':
        return (
          <ModernHomePage
            onGetStarted={handleGetStarted}
            onViewVideos={handleViewVideos}
            hasVideos={true} // TODO: Check if user has videos
          />
        );

      case 'upload':
        return (
          <div className="app-container">
            <div className="upload-section">
              <button 
                className="back-to-home-btn"
                onClick={() => setCurrentView('home')}
              >
                ← Back to Home
              </button>
              <h1 className="app-title">Upload Video</h1>
              <p className="app-subtitle">
                Upload your tennis videos for advanced performance analysis
              </p>
              <VideoUpload onUploadSuccess={handleVideoUploaded} />
            </div>
          </div>
        );

      case 'list':
        return (
          <div className="app-container">
            <div className="list-section">
              <div className="list-header">
                <button 
                  className="back-to-home-btn"
                  onClick={() => setCurrentView('home')}
                >
                  ← Back to Home
                </button>
                <button 
                  className="upload-new-btn"
                  onClick={() => setCurrentView('upload')}
                >
                  Upload New Video
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

  return <div className="App">{renderCurrentView()}</div>;
}

export default App;
