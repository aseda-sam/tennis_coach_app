import React, { useCallback, useState } from 'react';
import {
  useAnalysisStatus,
  AnalysisState,
} from '../hooks/useAnalysisStatus';
import {
  useVideos,
  useVideoAnalysisStatuses,
  useDeleteVideo,
} from '../hooks/useVideos';
import { VideoMetadata } from '../types/video';
import {
  DeleteIcon,
  VideoIcon,
} from './Icons';
import './VideoList.css';

interface VideoListProps {
  onVideoDeleted?: () => void;
  onViewAnalysis?: (video: VideoMetadata) => void;
}

const VideoList: React.FC<VideoListProps> = ({
  onVideoDeleted,
  onViewAnalysis,
}) => {
  // Use React Query hooks for data fetching
  const {
    data: videos = [],
    isLoading: videosLoading,
    error: videosError,
    refetch: refetchVideos,
  } = useVideos();

  const videoIds = videos.map((v: VideoMetadata) => v.id);
  const {
    data: analysisStatusesMap = {},
    isLoading: statusesLoading,
  } = useVideoAnalysisStatuses(videoIds);

  const deleteVideoMutation = useDeleteVideo();

  // Track active analysis tasks using the unified system
  const [activeAnalysisTasks, setActiveAnalysisTasks] = useState<
    Map<number, string> // videoId -> jobId
  >(new Map());

  const loading = videosLoading || statusesLoading;
  const error = videosError
    ? 'Failed to load videos. Please try again.'
    : null;

  // Use the unified analysis status system (callbacks kept for future analyze functionality)
  useAnalysisStatus({
    onComplete: useCallback(
      async (
        completedState: Extract<AnalysisState, { status: 'completed' }>
      ) => {
        // Task completed, refresh videos and clear active tasks
        try {
          await refetchVideos();
          setActiveAnalysisTasks(new Map());
        } catch (err) {
          console.error('Error refreshing videos after analysis:', err);
          setActiveAnalysisTasks(new Map());
        }
      },
      [refetchVideos]
    ),
    onError: useCallback(
      (failedState: Extract<AnalysisState, { status: 'failed' }>) => {
        console.error('Analysis task failed:', failedState.error);
        setActiveAnalysisTasks(new Map());
      },
      []
    ),
  });

  const handleDelete = async (videoId: number) => {
    try {
      await deleteVideoMutation.mutateAsync(videoId);
      onVideoDeleted?.();
    } catch (err: any) {
      console.error('Error deleting video:', err);
    }
  };

  // Removed handleAnalyze - we now only use pose detection
  // Removed handlePoseAnalyze - not used in card layout (can be re-added if needed for analyze button)

  // Removed pollTaskStatus - legacy function no longer needed

  // Removed verifyAnalysisData - we now use generic analysis status

  // Removed pollModularAnalysisStatus - we now use pose detection only

  const handleViewAnalysis = (videoId: number) => {
    if (onViewAnalysis) {
      const video = videos.find((v: VideoMetadata) => v.id === videoId);
      if (video) {
        onViewAnalysis(video);
      }
    }
  };

  // Removed handleCancelAnalysis - we now only use pose detection

  // Removed getAnalysisForVideo - we now only use pose detection

  const isAnalyzing = (videoId: number): boolean => {
    return activeAnalysisTasks.has(videoId);
  };

  const formatFileSize = (bytes: number): string => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return 'Today';
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays} days ago`;
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
  };

  // Removed getStatusTag - not used in card layout



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
          <button onClick={() => refetchVideos()} className="retry-btn">
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="video-list-container">
      {/* Header */}
      <div className="video-list-header">
        <div className="header-left">
          <h2 className="page-title">Video Library</h2>
          <p className="video-count">{videos.length} of {videos.length} sessions</p>
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
        <div className="video-grid">
          {videos.map((video: VideoMetadata) => {
            const analysisStatus = analysisStatusesMap[video.id];
            const isCurrentlyAnalyzing = isAnalyzing(video.id);

            return (
              <div
                key={video.id}
                className="video-card"
                onClick={() => {
                  // Only make clickable if analysis exists or not analyzing
                  if (analysisStatus?.has_analysis || !isCurrentlyAnalyzing) {
                    handleViewAnalysis(video.id);
                  }
                }}
                style={{
                  cursor: analysisStatus?.has_analysis || !isCurrentlyAnalyzing ? 'pointer' : 'default',
                }}
              >
                {/* Thumbnail Area */}
                <div className="video-card-thumbnail">
                  <div className="video-card-thumbnail-placeholder">
                    <VideoIcon size={48} color="#64748b" />
                  </div>
                </div>

                {/* Metadata Section */}
                <div className="video-card-content">
                  <h3 className="video-card-filename">{video.filename}</h3>
                  
                  <div className="video-card-meta">
                    <div className="video-card-user-date">
                      <span className="user-info">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="user-icon">
                          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" fill="currentColor"/>
                        </svg>
                        Myself
                      </span>
                      <span className="date-info">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="calendar-icon">
                          <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z" fill="currentColor"/>
                        </svg>
                        {formatDate(video.created_at)}
                      </span>
                      <button
                        className="delete-card-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(video.id);
                        }}
                        disabled={deleteVideoMutation.isPending}
                        title="Delete"
                        type="button"
                      >
                        <DeleteIcon size={16} />
                      </button>
                    </div>
                  </div>

                  {/* File Size */}
                  <div className="video-card-size">
                    {formatFileSize(video.file_size)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Removed AnalysisModal - we now use pose detection only */}
    </div>
  );
};

export default VideoList;
