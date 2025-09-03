import React, { useCallback, useEffect, useRef, useState } from 'react';
import { analysisApi, AnalysisData, videoApi } from '../services/api';
import modularAnalysisApi from '../services/modularAnalysisApi';
import poseDetectionApi, {
  PoseDetectionStartResponse,
} from '../services/poseDetectionApi';
import { VideoMetadata } from '../types/video';
import AnalysisModal from './AnalysisModal';
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
import StageProgress from './StageProgress';
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
  const [analyses, setAnalyses] = useState<AnalysisData[]>([]);
  const [poseDetections, setPoseDetections] = useState<Map<number, any>>(
    new Map()
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedVideo, setSelectedVideo] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Track active analysis tasks
  const [activeTasks, setActiveTasks] = useState<
    Map<
      number,
      {
        taskId: number;
        progress: number;
        status: string;
        currentStage?: string;
        stageProgress?: number;
        stageMessage?: string;
      }
    >
  >(new Map());

  // Track active pose detection tasks
  const [activePoseTasks, setActivePoseTasks] = useState<
    Map<
      number,
      {
        taskId: number;
        progress: number;
        status: string;
      }
    >
  >(new Map());

  // Ref to store verifyAnalysisData function to avoid circular dependency
  const verifyAnalysisDataRef = useRef<
    ((videoId: number) => Promise<void>) | null
  >(null);

  const loadVideos = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [videosResponse, analysesResponse] = await Promise.all([
        videoApi.getVideos(),
        analysisApi.getAllAnalyses(),
      ]);
      setVideos(videosResponse.videos);
      setAnalyses(analysesResponse);

      // Load pose detection data for each video
      const poseDetectionMap = new Map<number, any>();
      for (const video of videosResponse.videos) {
        try {
          const poseDetection = await poseDetectionApi.getResults(video.id);
          if (poseDetection.pose_detection.status === 'completed') {
            poseDetectionMap.set(video.id, poseDetection.pose_detection);
          }
        } catch (error) {
          // No pose detection for this video, which is fine
          console.debug(`No pose detection for video ${video.id}`);
        }
      }
      setPoseDetections(poseDetectionMap);
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
      setActiveTasks(
        (prev) =>
          new Map(
            prev.set(videoId, { taskId: 0, progress: 0, status: 'starting' })
          )
      );

      // Use new modular analysis instead of legacy analysis
      const response = await modularAnalysisApi.startComprehensiveAnalysis(
        videoId,
        {
          include_video_quality: true,
          include_ball_detection: true,
          include_pose_detection: true,
          confidence_threshold: 0.5,
          detection_threshold: 0.5,
        }
      );

      if (response.status === 'processing') {
        // Analysis started - track the progress
        setActiveTasks(
          (prev) =>
            new Map(
              prev.set(videoId, {
                taskId: 0, // No task_id for modular analysis
                progress: 0,
                status: 'processing',
              })
            )
        );

        // Store modular analysis progress
        // TODO: Track individual service progress in future enhancement

        // Start polling for modular analysis results
        pollModularAnalysisStatus(videoId);
      } else if (response.status === 'completed') {
        // Analysis completed immediately
        setActiveTasks((prev) => {
          const newMap = new Map(prev);
          newMap.delete(videoId);
          return newMap;
        });
        // TODO: Clear modular analysis progress in future enhancement
        await loadVideos(); // Refresh to get the new analysis
      } else {
        throw new Error(response.message || 'Failed to start modular analysis');
      }
    } catch (err: any) {
      const errorMessage =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to start analysis';
      setError(errorMessage);
      console.error('Error starting analysis:', err);

      // Remove from active tasks on error
      setActiveTasks((prev) => {
        const newMap = new Map(prev);
        newMap.delete(videoId);
        return newMap;
      });
      // TODO: Clear modular analysis progress in future enhancement
    }
  };

  const handlePoseAnalyze = async (videoId: number) => {
    try {
      // Add task to active pose tasks map
      setActivePoseTasks(
        (prev) =>
          new Map(
            prev.set(videoId, { taskId: 0, progress: 0, status: 'starting' })
          )
      );

      const response: PoseDetectionStartResponse =
        await poseDetectionApi.startAnalysis(videoId, {
          confidence_threshold: 0.5,
          detection_threshold: 0.5,
        });

      if (response.status === 'completed' && response.pose_detection_id) {
        // Pose detection completed immediately
        setActivePoseTasks((prev) => {
          const newMap = new Map(prev);
          newMap.delete(videoId);
          return newMap;
        });
        await loadVideos(); // Refresh to get the new pose detection
      } else if (response.status === 'processing' && response.task_id) {
        // Pose detection started in background - track the task
        setActivePoseTasks(
          (prev) =>
            new Map(
              prev.set(videoId, {
                taskId: response.task_id || 0,
                progress: 0,
                status: 'processing',
              })
            )
        );

        // Start polling for this task (we'll need to create a pose-specific poller)
        // For now, just show processing status
        console.log(
          `Pose detection started for video ${videoId}, task ${response.task_id}`
        );
      } else {
        throw new Error(response.message || 'Failed to start pose detection');
      }
    } catch (err: any) {
      const errorMessage =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to start pose detection';
      setError(errorMessage);
      console.error('Error starting pose detection:', err);

      // Remove from active pose tasks on error
      setActivePoseTasks((prev) => {
        const newMap = new Map(prev);
        newMap.delete(videoId);
        return newMap;
      });
    }
  };

  // Legacy function to poll task status - not used in new modular approach
  // TODO: Remove this function completely once legacy analysis is removed
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const pollTaskStatus = useCallback(
    async (taskId: number, videoId: number) => {
      const pollInterval = setInterval(async () => {
        try {
          const taskStatus = await analysisApi.getTaskStatus(taskId);

          // Update active tasks with new progress and stage information
          setActiveTasks((prev) => {
            const newMap = new Map(prev);
            newMap.set(videoId, {
              taskId,
              progress: taskStatus.progress,
              status: taskStatus.status,
              currentStage: taskStatus.current_stage || undefined,
              stageProgress: taskStatus.stage_progress || undefined,
              stageMessage: taskStatus.stage_message || undefined,
            });
            return newMap;
          });

          // If task is completed, start verification process
          if (taskStatus.status === 'completed') {
            clearInterval(pollInterval);

            // Keep task in "finalizing" state while verifying analysis data
            setActiveTasks((prev) => {
              const newMap = new Map(prev);
              newMap.set(videoId, {
                taskId,
                progress: 100,
                status: 'finalizing',
              });
              return newMap;
            });

            // Verify analysis data is available with retries
            if (verifyAnalysisDataRef.current) {
              await verifyAnalysisDataRef.current(videoId);
            }
          } else if (
            taskStatus.status === 'failed' ||
            taskStatus.status === 'cancelled'
          ) {
            clearInterval(pollInterval);

            // Remove from active tasks
            setActiveTasks((prev) => {
              const newMap = new Map(prev);
              newMap.delete(videoId);
              return newMap;
            });
          }
        } catch (err) {
          console.error('Error polling task status:', err);
          clearInterval(pollInterval);

          // Remove from active tasks on error
          setActiveTasks((prev) => {
            const newMap = new Map(prev);
            newMap.delete(videoId);
            return newMap;
          });
        }
      }, 2000); // Poll every 2 seconds

      // Cleanup function
      return () => clearInterval(pollInterval);
    },
    []
  );

  // Function to verify analysis data is available
  const verifyAnalysisData = useCallback(
    async (videoId: number) => {
      const maxRetries = 5;
      const retryDelay = 2000; // 2 seconds

      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          // Try to get analysis data
          const analysis = await analysisApi.getAnalysisByVideo(videoId);

          // Check if analysis has the required data for annotated video
          if (
            analysis &&
            analysis.pose_detections &&
            analysis.pose_detections.length > 0
          ) {
            // Analysis data is complete, remove from active tasks
            setActiveTasks((prev) => {
              const newMap = new Map(prev);
              newMap.delete(videoId);
              return newMap;
            });

            // Refresh the analyses list
            await loadVideos();
            return;
          }

          // If we're on the last attempt, still remove from active tasks
          if (attempt === maxRetries) {
            setActiveTasks((prev) => {
              const newMap = new Map(prev);
              newMap.delete(videoId);
              return newMap;
            });
            await loadVideos();
            return;
          }

          // Wait before next retry
          await new Promise((resolve) => setTimeout(resolve, retryDelay));
        } catch (err) {
          console.error(
            `Error verifying analysis data (attempt ${attempt}):`,
            err
          );

          // If we're on the last attempt, remove from active tasks
          if (attempt === maxRetries) {
            setActiveTasks((prev) => {
              const newMap = new Map(prev);
              newMap.delete(videoId);
              return newMap;
            });
            await loadVideos();
            return;
          }

          // Wait before next retry
          await new Promise((resolve) => setTimeout(resolve, retryDelay));
        }
      }
    },
    [loadVideos]
  );

  // Store the function in ref to avoid circular dependency
  verifyAnalysisDataRef.current = verifyAnalysisData;

  // Function to poll modular analysis status
  const pollModularAnalysisStatus = useCallback(
    async (videoId: number) => {
      const pollInterval = setInterval(async () => {
        try {
          const results =
            await modularAnalysisApi.getComprehensiveResults(videoId);

          // Update progress
          // TODO: Track individual service progress in future enhancement
          console.log('Modular analysis progress:', {
            video_quality: results.video_quality ? 'completed' : 'pending',
            ball_detection: results.ball_detection ? 'completed' : 'pending',
            pose_detection: results.pose_detection ? 'completed' : 'pending',
          });

          // If analysis is completed, clean up
          if (results.overall_status === 'completed') {
            clearInterval(pollInterval);
            setActiveTasks((prev) => {
              const newMap = new Map(prev);
              newMap.delete(videoId);
              return newMap;
            });
            // TODO: Clear modular analysis progress in future enhancement
            await loadVideos(); // Refresh to get the new analysis
          } else if (results.overall_status === 'failed') {
            clearInterval(pollInterval);
            setActiveTasks((prev) => {
              const newMap = new Map(prev);
              newMap.delete(videoId);
              return newMap;
            });
            // TODO: Clear modular analysis progress in future enhancement
            setError(results.error || 'Modular analysis failed');
          }
        } catch (err) {
          console.error('Error polling modular analysis status:', err);
          // Continue polling on error, but log it
        }
      }, 2000); // Poll every 2 seconds

      // Clean up interval after 5 minutes to prevent infinite polling
      setTimeout(
        () => {
          clearInterval(pollInterval);
        },
        5 * 60 * 1000
      );
    },
    [loadVideos]
  );

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

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedVideo(null);
  };

  const handleCancelAnalysis = async (videoId: number) => {
    const activeTask = activeTasks.get(videoId);
    if (!activeTask || !activeTask.taskId) return;

    try {
      await analysisApi.cancelTask(activeTask.taskId);

      // Remove from active tasks
      setActiveTasks((prev) => {
        const newMap = new Map(prev);
        newMap.delete(videoId);
        return newMap;
      });

      setError('Analysis cancelled successfully');
    } catch (err: any) {
      const errorMessage =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to cancel analysis';
      setError(errorMessage);
      console.error('Error cancelling analysis:', err);
    }
  };

  const getAnalysisForVideo = (videoId: number): AnalysisData | null => {
    const video = videos.find((v) => v.id === videoId);
    if (!video) return null;

    // First try to find by video_id (stronger relationship)
    let analysis = analyses.find((analysis) => analysis.video_id === videoId);

    // Fallback to filename matching (for backward compatibility)
    if (!analysis) {
      analysis = analyses.find(
        (analysis) => analysis.video_filename === video.filename
      );
    }

    return analysis || null;
  };

  const isPoseAnalyzing = (videoId: number): boolean => {
    return activePoseTasks.get(videoId) !== undefined;
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
    const poseDetection = poseDetections.get(videoId);

    if (activeTask) {
      if (activeTask.status === 'processing') {
        return {
          text: `Processing (${activeTask.progress}%)`,
          color: 'processing',
        };
      } else if (activeTask.status === 'starting') {
        return { text: 'Starting...', color: 'processing' };
      } else if (activeTask.status === 'finalizing') {
        return { text: 'Finalizing...', color: 'processing' };
      } else if (activeTask.status === 'failed') {
        return { text: 'Failed', color: 'error' };
      } else if (activeTask.status === 'cancelled') {
        return { text: 'Cancelled', color: 'error' };
      }
    }

    if (analysis || poseDetection) {
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

  const isVideoAnalyzing = (videoId: number): boolean => {
    const activeTask = activeTasks.get(videoId);
    return (
      activeTask !== undefined &&
      (activeTask.status === 'starting' ||
        activeTask.status === 'processing' ||
        activeTask.status === 'finalizing')
    );
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
            const analysis = getAnalysisForVideo(video.id);
            const poseDetection = poseDetections.get(video.id);
            const isAnalyzing = isVideoAnalyzing(video.id);
            const status = getStatusTag(analysis, video.id);
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
                  {!analysis && !isAnalyzing && (
                    <>
                      <button
                        className="action-btn analyze-btn"
                        onClick={() => handleAnalyze(video.id)}
                      >
                        <AnalyticsIcon size={16} />
                        Analyze
                      </button>
                      <button
                        className="action-btn pose-btn"
                        onClick={() => handlePoseAnalyze(video.id)}
                      >
                        <AnalyticsIcon size={16} />
                        Pose Only
                      </button>
                    </>
                  )}

                  {isPoseAnalyzing(video.id) && (
                    <div className="analysis-progress-container">
                      <div className="pose-analysis-progress">
                        <span>Pose Detection: Processing...</span>
                        <ProgressBar
                          progress={
                            activePoseTasks.get(video.id)?.progress || 0
                          }
                          status="processing"
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

                  {/* Show View Analysis button when analysis OR pose detection exists */}
                  {(analysis || poseDetection) && (
                    <button
                      className="action-btn analysis-btn"
                      onClick={() => handleViewAnalysis(video.id)}
                    >
                      <EyeIcon size={16} />
                      View Analysis
                    </button>
                  )}

                  {isAnalyzing && (
                    <div className="analysis-progress-container">
                      {activeTasks.get(video.id)?.currentStage ? (
                        <StageProgress
                          currentStage={
                            activeTasks.get(video.id)?.currentStage ||
                            'processing'
                          }
                          stageProgress={
                            activeTasks.get(video.id)?.stageProgress || 0
                          }
                          stageMessage={
                            activeTasks.get(video.id)?.stageMessage ||
                            'Processing...'
                          }
                          overallProgress={
                            activeTasks.get(video.id)?.progress || 0
                          }
                          size="small"
                        />
                      ) : (
                        <ProgressBar
                          progress={activeTasks.get(video.id)?.progress || 0}
                          status={
                            (activeTasks.get(video.id)?.status as any) ||
                            'processing'
                          }
                          size="small"
                          showPercentage={false}
                          showStatus={false}
                        />
                      )}
                      <button
                        className="action-btn cancel-btn"
                        onClick={() => handleCancelAnalysis(video.id)}
                      >
                        Cancel
                      </button>
                    </div>
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
