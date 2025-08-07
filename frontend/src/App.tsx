import React, { useState } from 'react';
import VideoUpload from './components/VideoUpload';
import VideoList from './components/VideoList';
import { VideoMetadata } from './types/video';
import './App.css';

function App() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUploadSuccess = (video: VideoMetadata) => {
    // Trigger a refresh of the video list
    setRefreshKey(prev => prev + 1);
  };

  const handleVideoDeleted = () => {
    // The video list will automatically refresh after deletion
    console.log('Video deleted successfully');
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎾 Tennis Analysis System</h1>
        <p>Upload and analyze your tennis videos with computer vision</p>
      </header>
      
      <main className="App-main">
        <VideoUpload onUploadSuccess={handleUploadSuccess} />
        <VideoList key={refreshKey} onVideoDeleted={handleVideoDeleted} />
      </main>
      
      <footer className="App-footer">
        <p>Computer Vision Tennis Analysis - Phase 3</p>
      </footer>
    </div>
  );
}

export default App;
