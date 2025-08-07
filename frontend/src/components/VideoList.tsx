import React, { useEffect, useState } from 'react';
import { analysisApi, videoApi } from '../services/api';
import { VideoMetadata } from '../types/video';
import AnalysisModal from './AnalysisModal';
import { AnalysisData } from './AnalysisResults';
import {
    AnalyticsIcon,
    DeleteIcon,
    EyeIcon,
    GridIcon,
    ListIcon,
    PlayIcon,
    VideoIcon
} from './Icons';
import './VideoList.css';

interface VideoListProps {
  onVideoDeleted: () => void;
  onViewAnalysis?: (video: VideoMetadata) => void;
}

const VideoList: React.FC<VideoListProps> = ({ onVideoDeleted, onViewAnalysis }) => {
  const [videos, setVideos] = useState<VideoMetadata[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const loadVideos = async () => {
    try {
      setLoading(true);
      setError(null);
      const [videosResponse, analysesResponse] = await Promise.all([
        videoApi.getVideos(),
        analysisApi.getAllAnalyses()
      ]);
      setVideos(videosResponse.videos);
      setAnalyses(analysesResponse);
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
    try {
      setDeletingId(filename);
      await videoApi.deleteVideo(filename);
      await loadVideos();
      onVideoDeleted();
    } catch (err: any) {
      setError('Failed to delete video. Please try again.');
      console.error('Error deleting video:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleAnalyze = async (filename: string) => {
    try {
      setAnalyzingId(filename);
      await analysisApi.startAnalysis(filename);
      const analysesResponse = await analysisApi.getAllAnalyses();
      setAnalyses(analysesResponse);
    } catch (err: any) {
      setError('Failed to start analysis. Please try again.');
      console.error('Error starting analysis:', err);
    } finally {
      setAnalyzingId(null);
    }
  };

  const handleViewAnalysis = (filename: string) => {
    if (onViewAnalysis) {
      const video = videos.find(v => v.filename === filename);
      if (video) {
        onViewAnalysis(video);
      }
    } else {
      setSelectedVideo(filename);
      setModalOpen(true);
    }
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedVideo(null);
  };

  const getAnalysisForVideo = (filename: string): AnalysisData | null => {
    return analyses.find(analysis => analysis.video_filename === filename) || null;
  };

  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes: number): string => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    });
  };

  const getStatusTag = (analysis: AnalysisData | null, isAnalyzing: boolean) => {
    if (isAnalyzing) {
      return { text: 'Processing', color: 'processing' };
    }
    if (analysis) {
      return { text: 'Completed', color: 'completed' };
    }
    return { text: 'Not Analyzed', color: 'not-analyzed' };
  };

  if (loading) {
    return (
      <div className="video-list-container">
        <div className="loading-spinner">
          <div className="spinner"></div>
          <p>Loading videos...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="video-list-container">
        <div className="error-message">
          <p>{error}</p>
          <button onClick={loadVideos} className="retry-btn">Try Again</button>
        </div>
      </div>
    );
  }

  return (
    <div className="video-list-container">
      {/* Enhanced Header */}
      <div className="video-list-header">
        <div className="header-left">
          <h1 className="page-title">My Videos</h1>
          <p className="video-count">{videos.length} videos uploaded</p>
        </div>
        <div className="header-right">
          <div className="view-toggle">
            <button 
              className={`toggle-btn ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
            >
              <GridIcon size={18} />
            </button>
            <button 
              className={`toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
            >
              <ListIcon size={18} />
            </button>
          </div>
        </div>
      </div>

      {videos.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <VideoIcon size={64} color="#94a3b8" />
          </div>
          <h3>No videos uploaded yet</h3>
          <p>Upload your first tennis video to get started with analysis</p>
        </div>
      ) : (
        <div className={`video-grid ${viewMode}`}>
          {videos.map((video) => {
            const analysis = getAnalysisForVideo(video.filename);
            const isAnalyzing = analyzingId === video.filename;
            const status = getStatusTag(analysis, isAnalyzing);
            
            return (
              <div key={video.filename} className="video-card-enhanced">
                <div className="video-thumbnail-container">
                  <div className="video-thumbnail">
                    <VideoIcon size={48} color="white" />
                    <div className="play-overlay">
                      <PlayIcon size={32} color="#3b82f6" />
                    </div>
                    {video.duration && (
                      <div className="duration-badge">
                        {formatDuration(video.duration)}
                      </div>
                    )}
                  </div>
                  <div className={`status-tag ${status.color}`}>
                    {status.text}
                  </div>
                </div>
                
                <div className="video-content">
                  <h3 className="video-title">{video.filename}</h3>
                  
                  <div className="video-metadata-enhanced">
                    <div className="metadata-row">
                      <span className="metadata-label">File Size:</span>
                      <span className="metadata-value">{formatFileSize(video.file_size)}</span>
                    </div>
                    
                    {video.width && video.height && (
                      <div className="metadata-row">
                        <span className="metadata-label">Resolution:</span>
                        <span className="metadata-value">{video.width}×{video.height}</span>
                      </div>
                    )}
                    
                    {video.fps && (
                      <div className="metadata-row">
                        <span className="metadata-label">Frame Rate:</span>
                        <span className="metadata-value">{video.fps} fps</span>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="video-actions-enhanced">
                  {!analysis && !isAnalyzing && (
                    <button
                      className="action-btn analyze-btn"
                      onClick={() => handleAnalyze(video.filename)}
                    >
                      <AnalyticsIcon size={16} />
                      Analyze
                    </button>
                  )}
                  
                  {analysis && (
                    <button
                      className="action-btn view-btn"
                      onClick={() => handleViewAnalysis(video.filename)}
                    >
                      <EyeIcon size={16} />
                      View Analysis
                    </button>
                  )}
                  
                  {isAnalyzing && (
                    <button className="action-btn processing-btn" disabled>
                      <div className="loading-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                      Analyzing...
                    </button>
                  )}
                  
                  <button
                    className="action-btn delete-btn"
                    onClick={() => handleDelete(video.filename)}
                    disabled={deletingId === video.filename}
                  >
                    <DeleteIcon size={16} />
                    {deletingId === video.filename ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {modalOpen && selectedVideo && (
        <AnalysisModal
          isOpen={modalOpen}
          onClose={handleCloseModal}
          videoFilename={selectedVideo}
        />
      )}
    </div>
  );
};

export default VideoList;
