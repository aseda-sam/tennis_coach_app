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
import { clsx } from 'clsx';
import {
  AnalyticsIcon,
  DeleteIcon,
  EyeIcon,
  GridIcon,
  ListIcon,
  PlayIcon,
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
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

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
            return { text: 'Completed', color: 'completed' };
        }
      }
      // Fallback: show processing if job is tracked but state not yet loaded
      return { text: 'Processing', color: 'processing' };
    }

    if (analysisStatus?.has_analysis) {
      return { text: 'Completed', color: 'completed' };
    }

    return { text: 'Not Analyzed', color: 'not-analyzed' };
  };

  const getQualityStatus = (video: VideoMetadata) => {
    if (!video.quality_level || video.quality_level === 'unknown') {
      return { text: 'Quality Unknown', color: 'unknown' };
    }

    switch (video.quality_level) {
      case 'excellent':
        return { text: 'Excellent Quality', color: 'excellent' };
      case 'good':
        return { text: 'Good Quality', color: 'good' };
      case 'fair':
        return { text: 'Fair Quality', color: 'fair' };
      case 'poor':
        return { text: 'Poor Quality', color: 'poor' };
      default:
        return { text: 'Quality Unknown', color: 'unknown' };
    }
  };

  const getQualityMessage = (video: VideoMetadata): string => {
    if (!video.quality_level || video.quality_level === 'unknown') {
      return 'Quality not assessed yet';
    }

    switch (video.quality_level) {
      case 'excellent':
        return 'Great video quality! Ready for analysis.';
      case 'good':
        return 'Good quality. Analysis should work well.';
      case 'fair':
        return 'Fair quality. Analysis may have reduced accuracy.';
      case 'poor':
        return 'Poor quality detected. Consider re-recording with better lighting/steadier camera.';
      default:
        return 'Quality not assessed yet';
    }
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
          {videos.map((video: VideoMetadata) => {
            const analysisStatus = analysisStatusesMap[video.id];
            const isCurrentlyAnalyzing = isAnalyzing(video.id);
            const status = getStatusTag(null, video.id); // No legacy analysis
            const qualityStatus = getQualityStatus(video);

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
                  {/* Quality status tag */}
                  <div className={`quality-tag ${qualityStatus.color}`}>
                    {qualityStatus.text}
                  </div>
                </div>

                <div className="video-content">
                  <h3 className="video-title">{video.filename}</h3>

                  {/* Quality message */}
                  {video.quality_level && video.quality_level !== 'unknown' && (
                    <div className="quality-message">
                      {getQualityMessage(video)}
                    </div>
                  )}

                  <div className="video-metadata-enhanced">
                    <div className="metadata-row">
                      <span className="metadata-label">File Size:</span>
                      <span className="metadata-value">
                        {formatFileSize(video.file_size)}
                      </span>
                    </div>

                    {video.width && video.height && (
                      <div className="metadata-row">
                        <span className="metadata-label">Resolution:</span>
                        <span className="metadata-value">
                          {video.width}×{video.height}
                        </span>
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
                  {!analysisStatus?.has_analysis && !isCurrentlyAnalyzing && (
                    <button
                      className="action-btn pose-btn"
                      onClick={() => handlePoseAnalyze(video.id)}
                    >
                      <AnalyticsIcon size={16} />
                      Pose Only
                    </button>
                  )}

                  {/* Show analysis status if currently analyzing */}
                  {isCurrentlyAnalyzing && analysisState.status !== 'idle' && (
                    <div className="analysis-status-container">
                      <span
                        className={clsx(
                          'px-2 py-1 text-xs font-medium rounded-full',
                          analysisState.status === 'processing' &&
                            'bg-blue-100 text-blue-700',
                          analysisState.status === 'queued' &&
                            'bg-yellow-100 text-yellow-700',
                          analysisState.status === 'completed' &&
                            'bg-green-100 text-green-700',
                          analysisState.status === 'failed' &&
                            'bg-red-100 text-red-700'
                        )}
                      >
                        {analysisState.status.toUpperCase()}
                      </span>
                    </div>
                  )}

                  {/* Always show View Video button */}
                  <button
                    className="action-btn view-btn"
                    onClick={() => handleViewAnalysis(video.id)}
                  >
                    <PlayIcon size={16} />
                    View Video
                  </button>

                  {/* Show View Analysis button when analysis exists */}
                  {analysisStatus?.has_analysis && (
                    <button
                      className="action-btn analysis-btn"
                      onClick={() => handleViewAnalysis(video.id)}
                    >
                      <EyeIcon size={16} />
                      View Analysis
                    </button>
                  )}

                  <button
                    className="action-btn delete-btn"
                    onClick={() => handleDelete(video.id)}
                    disabled={deleteVideoMutation.isPending}
                  >
                    <DeleteIcon size={16} />
                    {deleteVideoMutation.isPending ? 'Deleting...' : 'Delete'}
                  </button>
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
