import React, { useCallback, useEffect, useState } from 'react';
import {
  AnalysisProgress,
  useAnalysisProgress,
} from '../hooks/useAnalysisProgress';
import { videoApi } from '../services/api';
import unifiedAnalysisApi from '../services/unifiedAnalysisApi';
import { VideoMetadata } from '../types/video';
import {
  AnalyticsIcon,
  DeleteIcon,
  EyeIcon,
  GridIcon,
  ListIcon,
  PlayIcon,
  VideoIcon,
} from './Icons';
import ProgressBar from './ProgressBar';
import './VideoList.css';

interface VideoListProps {
  onVideoDeleted?: () => void;
  onViewAnalysis?: (video: VideoMetadata) => void;
}

const VideoList: React.FC<VideoListProps> = ({
  onVideoDeleted,
  onViewAnalysis,
}) => {
  const [videos, setVideos] = useState<VideoMetadata[]>([]);
  const [analysisStatuses, setAnalysisStatuses] = useState<
    Map<
      number,
      {
        has_analysis: boolean;
        analysis_types: string[];
      }
    >
  >(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [, setModalOpen] = useState(false);
  const [, setSelectedVideo] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Track active analysis tasks using the unified system
  const [activeAnalysisTasks, setActiveAnalysisTasks] = useState<
    Map<number, string> // videoId -> jobId
  >(new Map());

  // Removed legacy analysis verification

  const loadVideos = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const videosResponse = await videoApi.getVideos();
      setVideos(videosResponse.videos);

      // Load analysis status for each video
      const analysisStatusMap = new Map<
        number,
        {
          has_analysis: boolean;
          analysis_types: string[];
        }
      >();
      for (const video of videosResponse.videos) {
        try {
          const status = await videoApi.getVideoAnalysisStatus(video.id);
          analysisStatusMap.set(video.id, status);
        } catch (error) {
          // No analysis status for this video, which is fine
          console.debug(`No analysis status for video ${video.id}`);
          analysisStatusMap.set(video.id, {
            has_analysis: false,
            analysis_types: [],
          });
        }
      }
      setAnalysisStatuses(analysisStatusMap);
    } catch (err: any) {
      setError('Failed to load videos. Please try again.');
      console.error('Error loading videos:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVideos();
  }, [loadVideos]);

  // Use the unified analysis progress system
  const { progress: analysisProgress, startPolling } = useAnalysisProgress({
    onComplete: useCallback(
      async (progress: AnalysisProgress) => {
        // Task completed, refresh videos and clear active tasks
        try {
          await loadVideos();
          setActiveAnalysisTasks(new Map());
        } catch (err) {
          console.error('Error refreshing videos after analysis:', err);
          setActiveAnalysisTasks(new Map());
        }
      },
      [loadVideos]
    ),
    onError: useCallback((error: string) => {
      console.error('Analysis task failed:', error);
      setError(error);
      setActiveAnalysisTasks(new Map());
    }, []),
  });

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

  // Removed handleAnalyze - we now only use pose detection

  const handlePoseAnalyze = async (videoId: number) => {
    try {
      // Clear any previous error for a fresh start
      setError(null);

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
      const errorMessage =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to start pose detection';
      setError(errorMessage);
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
      const video = videos.find((v) => v.id === videoId);
      if (video) {
        onViewAnalysis(video);
      }
    } else {
      setSelectedVideo(videoId);
      setModalOpen(true);
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
    const analysisStatus = analysisStatuses.get(videoId);
    const isCurrentlyAnalyzing = isAnalyzing(videoId);

    if (isCurrentlyAnalyzing && analysisProgress) {
      if (analysisProgress.status === 'processing') {
        return {
          text: `Processing (${analysisProgress.progress}%)`,
          color: 'processing',
        };
      } else if (analysisProgress.status === 'queued') {
        return { text: 'Queued...', color: 'processing' };
      } else if (analysisProgress.status === 'failed') {
        return { text: 'Failed', color: 'error' };
      } else if (analysisProgress.status === 'cancelled') {
        return { text: 'Cancelled', color: 'error' };
      }
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
          <button onClick={loadVideos} className="retry-btn">
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
          {videos.map((video) => {
            const analysisStatus = analysisStatuses.get(video.id);
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

                  {isCurrentlyAnalyzing && analysisProgress && (
                    <div className="analysis-progress-container">
                      <div className="pose-analysis-progress">
                        <span>
                          {analysisProgress.status === 'queued'
                            ? 'Queued...'
                            : analysisProgress.status === 'processing'
                              ? `Processing... (${
                                  analysisProgress.elapsedTime
                                    ? Math.round(
                                        analysisProgress.elapsedTime / 1000
                                      )
                                    : 0
                                }s)` +
                                (analysisProgress.estimatedDuration
                                  ? `, ~${Math.round(analysisProgress.estimatedDuration)}s estimated`
                                  : '')
                              : analysisProgress.status}
                        </span>
                        <ProgressBar
                          progress={analysisProgress.progress}
                          status={
                            analysisProgress.status === 'processing'
                              ? 'processing'
                              : analysisProgress.status === 'completed'
                                ? 'completed'
                                : analysisProgress.status === 'failed'
                                  ? 'failed'
                                  : 'processing'
                          }
                          size="small"
                          showPercentage={false}
                          showStatus={false}
                        />
                      </div>
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

      {/* Removed AnalysisModal - we now use pose detection only */}
    </div>
  );
};

export default VideoList;
