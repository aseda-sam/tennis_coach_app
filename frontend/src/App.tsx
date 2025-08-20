import { useState } from 'react';
import './App.css';
import DesignComparison from './components/DesignComparison';
import ModernAnalysisDashboard from './components/ModernAnalysisDashboard';
import ModernHomePage from './components/ModernHomePage';
import ModernVideoList from './components/ModernVideoList';
import ModernVideoUpload from './components/ModernVideoUpload';
import { VideoMetadata } from './types/video';

function App() {
  const [currentView, setCurrentView] = useState<
    'home' | 'upload' | 'list' | 'dashboard' | 'demo'
  >('home');
  const [selectedVideo, setSelectedVideo] = useState<VideoMetadata | null>(
    null
  );

  const handleVideoUploaded = (video: VideoMetadata) => {
    // Could store the uploaded video or just navigate to list
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

  // Mock function to check if user has videos - replace with real logic
  const hasVideos = false;

  const renderCurrentView = () => {
    switch (currentView) {
      case 'demo':
        return <DesignComparison />;
      case 'home':
        return (
          <ModernHomePage
            onGetStarted={handleGetStarted}
            onViewVideos={handleViewVideos}
            hasVideos={hasVideos}
          />
        );
      case 'upload':
        return (
          <ModernVideoUpload
            onUploadSuccess={handleVideoUploaded}
            onBack={() => setCurrentView('home')}
          />
        );

      case 'list':
        return (
          <ModernVideoList
            onVideoDeleted={handleVideoDeleted}
            onViewAnalysis={handleViewAnalysis}
            onUpload={() => setCurrentView('upload')}
            onBack={() => setCurrentView('home')}
          />
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
          <ModernAnalysisDashboard
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
