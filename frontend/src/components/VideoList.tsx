import React, { useEffect, useState } from 'react';
import { videoApi } from '../services/api';
import { VideoMetadata } from '../types/video';
import './VideoList.css';

interface VideoListProps {
  onVideoDeleted: () => void;
}

const VideoList: React.FC<VideoListProps> = ({ onVideoDeleted }) => {
  const [videos, setVideos] = useState<VideoMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadVideos = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await videoApi.getVideos();
      setVideos(response.videos);
    } catch (err: any) {
      setError('Failed to load videos. Please try again.');
      console.error('Error loading videos:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVideos();
  }, []);

  const handleDelete = async (filename: string) => {
    if (!window.confirm('Are you sure you want to delete this video?')) {
      return;
    }

    try {
      setDeletingId(filename);
      await videoApi.deleteVideo(filename);
      setVideos(videos.filter(video => video.filename !== filename));
      onVideoDeleted();
    } catch (err: any) {
      setError('Failed to delete video. Please try again.');
      console.error('Error deleting video:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const formatFileSize = (bytes: number): string => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };



  if (loading) {
    return (
      <div className="video-list">
        <h2>Uploaded Videos</h2>
        <div className="loading">Loading videos...</div>
      </div>
    );
  }

  return (
    <div className="video-list">
      <h2>Uploaded Videos ({videos.length})</h2>
      
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      {videos.length === 0 ? (
        <div className="empty-state">
          <p>No videos uploaded yet.</p>
          <p>Upload your first tennis video to get started!</p>
        </div>
      ) : (
        <div className="videos-grid">
          {videos.map((video) => (
            <div key={video.filename} className="video-card">
              <div className="video-thumbnail">
                <span className="video-icon">🎾</span>
              </div>
              
              <div className="video-info">
                <h3 className="video-title">{video.filename}</h3>
                
                <div className="video-metadata">
                  {video.duration && (
                    <div className="metadata-item">
                      <span className="label">Duration:</span>
                      <span className="value">{formatDuration(video.duration)}</span>
                    </div>
                  )}
                  
                  {video.width && video.height && (
                    <div className="metadata-item">
                      <span className="label">Resolution:</span>
                      <span className="value">{video.width}×{video.height}</span>
                    </div>
                  )}
                  
                  {video.fps && (
                    <div className="metadata-item">
                      <span className="label">FPS:</span>
                      <span className="value">{video.fps}</span>
                    </div>
                  )}
                  
                  <div className="metadata-item">
                    <span className="label">Size:</span>
                    <span className="value">{formatFileSize(video.file_size)}</span>
                  </div>
                </div>
              </div>
              
              <div className="video-actions">
                <button
                  className="delete-btn"
                  onClick={() => handleDelete(video.filename)}
                  disabled={deletingId === video.filename}
                >
                  {deletingId === video.filename ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default VideoList;
