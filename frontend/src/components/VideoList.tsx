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
import unifiedAnalysisApi from '../services/unifiedAnalysisApi';
import { VideoMetadata } from '../types/video';
import {
  AnalyticsIcon,
  DeleteIcon,
  EyeIcon,
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

  // Use the unified analysis status system
  const { state: analysisState, startPolling } = useAnalysisStatus({
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

  const handlePoseAnalyze = async (videoId: number) => {
    try {
      // Start pose detection analysis (annotation removed in this branch)
      const response = await unifiedAnalysisApi.startPoseAnalysis(
        videoId,
        0.5
      );

      // Analysis started in background - track the task
      setActiveAnalysisTasks((prev) => {
        const newMap = new Map(prev);
        newMap.set(videoId, response.job_id);
        return newMap;
      });

      // Start polling for progress
      startPolling(response.job_id);
    } catch (err: any) {
      console.error('Error starting pose analysis:', err);

      // Remove from active tasks on error
      setActiveAnalysisTasks((prev) => {
        const newMap = new Map(prev);
        newMap.delete(videoId);
        return newMap;
      });
    }
  };

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

  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes: number): string => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const getStatusTag = (analysis: any, videoId: number) => {
    const analysisStatus = analysisStatusesMap[videoId];
    const isCurrentlyAnalyzing = isAnalyzing(videoId);

    // Show current analysis state if this video is being analyzed
    if (isCurrentlyAnalyzing && analysisState.status !== 'idle') {
      const jobId = activeAnalysisTasks.get(videoId);
      // Only show status if this is the active job
      if (jobId && 'jobId' in analysisState && analysisState.jobId === jobId) {
        switch (analysisState.status) {
          case 'processing':
            return { text: 'Processing', color: 'processing' };
          case 'queued':
            return { text: 'Queued', color: 'queued' };
          case 'failed':
            return { text: 'Failed', color: 'error' };
          case 'completed':
            return { text: 'Ready', color: 'completed' };
        }
      }
      // Fallback: show processing if job is tracked but state not yet loaded
      return { text: 'Processing', color: 'processing' };
    }

    if (analysisStatus?.has_analysis) {
      return { text: 'Ready', color: 'completed' };
    }

    return { text: 'No analysis', color: 'not-analyzed' };
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
          <h2 className="page-title">Videos</h2>
          <p className="video-count">{videos.length} uploaded</p>
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
        <div className="video-list">
          {videos.map((video: VideoMetadata) => {
            const analysisStatus = analysisStatusesMap[video.id];
            const isCurrentlyAnalyzing = isAnalyzing(video.id);
            const status = getStatusTag(null, video.id);

            return (
              <div
                key={video.id}
                className="video-item"
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
                <div className="video-thumbnail-container">
                  <div className="video-thumbnail">
                    <VideoIcon size={32} color="white" />
                    {video.duration && (
                      <div className="duration-badge">
                        {formatDuration(video.duration)}
                      </div>
                    )}
                  </div>
                </div>

                <div className="video-content">
                  <div className="video-header">
                    <h3 className="video-title">{video.filename}</h3>
                    <div className="video-meta-list">
                      {formatFileSize(video.file_size)}
                      {video.width && video.height && (
                        <> • {video.width}×{video.height}</>
                      )}
                    </div>
                  </div>

                  <div className="video-actions">
                    <span className={`analysis-pill ${status.color}`}>
                      {status.color === 'completed' && (
                        <>
                          <EyeIcon size={14} />
                          <span>{status.text}</span>
                        </>
                      )}
                      {status.color !== 'completed' && <span>{status.text}</span>}
                    </span>

                    {!analysisStatus?.has_analysis && !isCurrentlyAnalyzing && (
                      <button
                        className="btn btn-secondary"
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePoseAnalyze(video.id);
                        }}
                        type="button"
                      >
                        <AnalyticsIcon size={16} />
                        Analyze
                      </button>
                    )}

                    <button
                      className="icon-btn delete-icon-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(video.id);
                      }}
                      disabled={deleteVideoMutation.isPending}
                      title="Delete"
                      type="button"
                    >
                      <DeleteIcon size={18} />
                    </button>
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
