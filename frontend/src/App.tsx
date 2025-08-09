import { useState } from 'react';
import './App.css';
import AnalysisDashboard from './components/AnalysisDashboard';
import VideoList from './components/VideoList';
import VideoUpload from './components/VideoUpload';
import { VideoMetadata } from './types/video';

function App() {
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

  const renderCurrentView = () => {
    switch (currentView) {
      case 'upload':
        return (
          <div className="app-container">
            <div className="upload-section">
              <h1 className="app-title">Tennis Video Analyzer</h1>
              <p className="app-subtitle">
                Upload your tennis videos for advanced performance analysis and technique insights
              </p>
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
            videoFilename={selectedVideo.filename}
            videoUrl={`${process.env.REACT_APP_API_URL || 'http://localhost:8000/api'}/videos/${selectedVideo.filename}/stream`}
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
