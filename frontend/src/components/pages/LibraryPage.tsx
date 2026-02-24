import React from 'react';
import { useNavigate } from 'react-router-dom';
import VideoList from '../VideoList';

function LibraryPage() {
  const navigate = useNavigate();

  return (
    <div className="app-container">
      <VideoList
        onVideoDeleted={() => {
          // Stay on library page — list refreshes via React Query
        }}
        onViewAnalysis={(video) => navigate(`/videos/${video.id}`)}
      />
    </div>
  );
}

export default LibraryPage;
