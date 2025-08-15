import React, { useCallback, useEffect, useState } from 'react';
import { analysisApi, AnalysisData, AnalysisStartResponse, videoApi } from '../services/api';
import { VideoMetadata } from '../types/video';
import { AnalyticsIcon, DeleteIcon, EyeIcon, GridIcon, ListIcon, PlayIcon, VideoIcon } from './Icons';
import AnalysisModal from './AnalysisModal';
import './VideoList.css';

interface VideoListProps {
  onVideoDeleted?: () => void;
  onViewAnalysis?: (video: VideoMetadata) => void;
}

const VideoList: React.FC<VideoListProps> = ({ onVideoDeleted, onViewAnalysis }) => {
  const [videos, setVideos] = useState<VideoMetadata[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  
  // Track active analysis tasks
  const [activeTasks, setActiveTasks] = useState<Map<number, { taskId: number; progress: number; status: string }>>(new Map());

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

  const handleDelete = async (videoId: number) => {
    try {
      setDeletingId(videoId);
      await videoApi.deleteVideo(videoId);
      await loadVideos();
      onVideoDeleted?.();
    } catch (err: any) {
      setError('Failed to delete video. Please try again.');
      console.error('Error deleting video:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleAnalyze = async (videoId: number) => {
    try {
      // Add task to active tasks map
      setActiveTasks(prev => new Map(prev.set(videoId, { taskId: 0, progress: 0, status: 'starting' })));
      
      const response: AnalysisStartResponse = await analysisApi.startAnalysis(videoId, {
        analysis_type: 'ball_tracking',
        confidence_threshold: 0.5,
        include_pose_detection: true
      });

      if (response.status === 'completed' && response.analysis_id) {
        // Analysis completed immediately
        setActiveTasks(prev => {
          const newMap = new Map(prev);
          newMap.delete(videoId);
          return newMap;
        });
        await loadVideos(); // Refresh to get the new analysis
      } else if (response.status === 'processing' && response.task_id) {
        // Analysis started in background - track the task
        setActiveTasks(prev => new Map(prev.set(videoId, { 
          taskId: response.task_id || 0, 
          progress: 0, 
          status: 'processing' 
        })));
        
        // Start polling for this task
        pollTaskStatus(response.task_id, videoId);
      } else {
        throw new Error(response.message || 'Failed to start analysis');
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to start analysis';
      setError(errorMessage);
      console.error('Error starting analysis:', err);
      
      // Remove from active tasks on error
      setActiveTasks(prev => {
        const newMap = new Map(prev);
        newMap.delete(videoId);
        return newMap;
      });
    }
  };

  // Function to poll task status
  const pollTaskStatus = useCallback(async (taskId: number, videoId: number) => {
    const pollInterval = setInterval(async () => {
      try {
        const taskStatus = await analysisApi.getTaskStatus(taskId);
        
        // Update active tasks with new progress
        setActiveTasks(prev => {
          const newMap = new Map(prev);
          newMap.set(videoId, { 
            taskId, 
            progress: taskStatus.progress, 
            status: taskStatus.status 
          });
          return newMap;
        });

        // If task is completed, stop polling and refresh data
        if (taskStatus.status === 'completed' || taskStatus.status === 'failed' || taskStatus.status === 'cancelled') {
          clearInterval(pollInterval);
          
          // Remove from active tasks
          setActiveTasks(prev => {
            const newMap = new Map(prev);
            newMap.delete(videoId);
            return newMap;
          });

          // Refresh analyses if completed
          if (taskStatus.status === 'completed') {
            await loadVideos();
          }
        }
      } catch (err) {
        console.error('Error polling task status:', err);
        clearInterval(pollInterval);
        
        // Remove from active tasks on error
        setActiveTasks(prev => {
          const newMap = new Map(prev);
          newMap.delete(videoId);
          return newMap;
        });
      }
    }, 2000); // Poll every 2 seconds

    // Cleanup function
    return () => clearInterval(pollInterval);
  }, []);

  const handleViewAnalysis = (videoId: number) => {
    if (onViewAnalysis) {
      const video = videos.find(v => v.id === videoId);
      if (video) {
        onViewAnalysis(video);
      }
    } else {
      setSelectedVideo(videoId);
      setModalOpen(true);
    }
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedVideo(null);
  };

  const getAnalysisForVideo = (videoId: number): AnalysisData | null => {
    const video = videos.find(v => v.id === videoId);
    if (!video) return null;
    
    // First try to find by video_id (stronger relationship)
    let analysis = analyses.find(analysis => analysis.video_id === videoId);
    
    // Fallback to filename matching (for backward compatibility)
    if (!analysis) {
      analysis = analyses.find(analysis => analysis.video_filename === video.filename);
    }
    
    return analysis || null;
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

  const getStatusTag = (analysis: AnalysisData | null, videoId: number) => {
    const activeTask = activeTasks.get(videoId);
    
    if (activeTask) {
      if (activeTask.status === 'processing') {
        return { text: `Processing (${activeTask.progress}%)`, color: 'processing' };
      } else if (activeTask.status === 'starting') {
        return { text: 'Starting...', color: 'processing' };
      } else if (activeTask.status === 'failed') {
        return { text: 'Failed', color: 'error' };
      } else if (activeTask.status === 'cancelled') {
        return { text: 'Cancelled', color: 'error' };
      }
    }
    
    if (analysis) {
      return { text: 'Completed', color: 'completed' };
    }
    
    return { text: 'Not Analyzed', color: 'not-analyzed' };
  };

  const isVideoAnalyzing = (videoId: number): boolean => {
    const activeTask = activeTasks.get(videoId);
    return activeTask !== undefined && (activeTask.status === 'starting' || activeTask.status === 'processing');
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
            const analysis = getAnalysisForVideo(video.id);
            const isAnalyzing = isVideoAnalyzing(video.id);
            const status = getStatusTag(analysis, video.id);
            
            return (
              <div key={video.id} className="video-card-enhanced">
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

                    {video.status && video.status !== 'uploaded' && (
                      <div className="metadata-row">
                        <span className="metadata-label">Status:</span>
                        <span className="metadata-value">{video.status}</span>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="video-actions-enhanced">
                  {!analysis && !isAnalyzing && (
                    <button
                      className="action-btn analyze-btn"
                      onClick={() => handleAnalyze(video.id)}
                    >
                      <AnalyticsIcon size={16} />
                      Analyze
                    </button>
                  )}
                  
                  {analysis && (
                    <button
                      className="action-btn view-btn"
                      onClick={() => handleViewAnalysis(video.id)}
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
                    onClick={() => handleDelete(video.id)}
                    disabled={deletingId === video.id}
                  >
                    <DeleteIcon size={16} />
                    {deletingId === video.id ? 'Deleting...' : 'Delete'}
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
          videoId={selectedVideo}
        />
      )}
    </div>
  );
};

export default VideoList;
