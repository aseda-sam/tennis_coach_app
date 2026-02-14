import { useQueryClient } from '@tanstack/react-query';
import React, { useCallback, useState } from 'react';
import { AnalysisState, useAnalysisStatus } from '../hooks/useAnalysisStatus';
import { usePlayerProfile } from '../hooks/usePlayerProfile';
import {
  useDeleteVideo,
  useUpdateVideoMetadata,
  useVideoAnalysisStatuses,
  useVideos,
} from '../hooks/useVideos';
import { VideoMetadata } from '../types/video';
import { CloseIcon, DeleteIcon, UploadIcon, VideoIcon } from './Icons';
import LoadingIndicator from './LoadingIndicator';
import './VideoList.css';
import VideoUpload from './VideoUpload';

interface VideoListProps {
  onVideoDeleted?: () => void;
  onViewAnalysis?: (video: VideoMetadata) => void;
}

const VideoList: React.FC<VideoListProps> = ({
  onVideoDeleted,
  onViewAnalysis,
}) => {
  const queryClient = useQueryClient();
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingVideo, setEditingVideo] = useState<VideoMetadata | null>(null);
  const [editSessionType, setEditSessionType] = useState('');
  const [editCameraAngle, setEditCameraAngle] = useState('');
  const [editPlayerTag, setEditPlayerTag] = useState<'you' | 'someone_else'>(
    'you'
  );
  const [applyToExistingServes, setApplyToExistingServes] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Use React Query hooks for data fetching
  const {
    data: videos = [],
    isLoading: videosLoading,
    error: videosError,
    refetch: refetchVideos,
  } = useVideos();

  const videoIds = videos.map((v: VideoMetadata) => v.id);
  const { data: analysisStatusesMap = {}, isLoading: statusesLoading } =
    useVideoAnalysisStatuses(videoIds);

  const { data: playerProfile } = usePlayerProfile();

  const deleteVideoMutation = useDeleteVideo();
  const updateMetadataMutation = useUpdateVideoMetadata();

  // Track active analysis tasks using the unified system
  const [activeAnalysisTasks, setActiveAnalysisTasks] = useState<
    Map<number, string> // videoId -> jobId
  >(new Map());

  const loading = videosLoading || statusesLoading;
  const error = videosError ? 'Failed to load videos. Please try again.' : null;

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
          // Silently handle refresh errors - component will continue with existing state
          setActiveAnalysisTasks(new Map());
        }
      },
      [refetchVideos]
    ),
    onError: useCallback(
      (failedState: Extract<AnalysisState, { status: 'failed' }>) => {
        // Error is already handled by the failed state - just clear active tasks
        setActiveAnalysisTasks(new Map());
      },
      []
    ),
  });

  const handleDelete = async (videoId: number) => {
    try {
      await deleteVideoMutation.mutateAsync(videoId);
      onVideoDeleted?.();
    } catch (err: unknown) {
      // Silently handle deletion errors - mutation already handles error state
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

  const resolvePlayerTag = useCallback(
    (video: VideoMetadata) => {
      if (!video.primary_player_id || !playerProfile?.id) {
        return 'you';
      }
      return video.primary_player_id === playerProfile.id
        ? 'you'
        : 'someone_else';
    },
    [playerProfile?.id]
  );

  const getPlayerLabel = useCallback(
    (video: VideoMetadata) => {
      if (!playerProfile?.name) {
        return 'Your Profile';
      }
      if (
        !video.primary_player_id ||
        video.primary_player_id === playerProfile.id
      ) {
        return playerProfile.name;
      }
      return 'Someone Else';
    },
    [playerProfile?.id, playerProfile?.name]
  );

  const openEditModal = useCallback(
    (video: VideoMetadata) => {
      setEditingVideo(video);
      setEditSessionType(video.session_type || '');
      setEditCameraAngle(video.camera_angle || '');
      setEditPlayerTag(resolvePlayerTag(video));
      setApplyToExistingServes(false);
      setEditError(null);
      setIsEditModalOpen(true);
    },
    [resolvePlayerTag]
  );

  const handleEditSave = useCallback(async () => {
    if (!editingVideo) return;
    setEditError(null);

    try {
      await updateMetadataMutation.mutateAsync({
        videoId: editingVideo.id,
        metadata: {
          session_type: editSessionType || undefined,
          camera_angle: editCameraAngle || undefined,
          player_tag: editPlayerTag,
          apply_to_existing_serves: applyToExistingServes,
        },
      });

      queryClient.invalidateQueries({ queryKey: ['videos'] });
      setIsEditModalOpen(false);
      setEditingVideo(null);
    } catch (err: unknown) {
      const axiosError = err as {
        response?: { data?: { detail?: string } };
      };
      setEditError(
        axiosError.response?.data?.detail ||
          'Failed to update video. Please try again.'
      );
    }
  }, [
    applyToExistingServes,
    editCameraAngle,
    editPlayerTag,
    editSessionType,
    editingVideo,
    queryClient,
    updateMetadataMutation,
  ]);

  const handleUploadSuccess = useCallback(
    (video: VideoMetadata) => {
      // Invalidate videos cache to refetch the list with the new video
      queryClient.invalidateQueries({ queryKey: ['videos'] });
      setIsUploadModalOpen(false);
    },
    [queryClient]
  );

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
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    }
  };

  // Removed getStatusTag - not used in card layout

  if (loading) {
    return (
      <div className="video-list-container">
        <div className="video-list-loading">
          <LoadingIndicator size="lg" label="Loading videos..." />
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
          <p className="video-count">
            {videos.length} of {videos.length} sessions
          </p>
        </div>
        <div className="header-right">
          <button
            className="upload-btn"
            onClick={() => setIsUploadModalOpen(true)}
            type="button"
          >
            <UploadIcon size={18} />
            Upload
          </button>
        </div>
      </div>

      {videos.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <VideoIcon size={64} color="var(--color-text-disabled)" />
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
                  cursor:
                    analysisStatus?.has_analysis || !isCurrentlyAnalyzing
                      ? 'pointer'
                      : 'default',
                }}
              >
                {/* Thumbnail Area */}
                <div className="video-card-thumbnail">
                  <div className="video-card-thumbnail-placeholder">
                    <VideoIcon size={48} color="var(--color-text-muted)" />
                  </div>
                </div>

                {/* Metadata Section */}
                <div className="video-card-content">
                  <h3 className="video-card-filename">{video.filename}</h3>

                  <div className="video-card-meta-row">
                    <span className="user-info">
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        className="user-icon"
                      >
                        <path
                          d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"
                          fill="currentColor"
                        />
                      </svg>
                      {getPlayerLabel(video)}
                    </span>
                    <span className="meta-separator">•</span>
                    <span className="date-info">
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        className="calendar-icon"
                      >
                        <path
                          d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z"
                          fill="currentColor"
                        />
                      </svg>
                      {formatDate(video.recorded_at ?? video.created_at)}
                    </span>
                    <span className="meta-separator">•</span>
                    <span className="video-card-size">
                      {formatFileSize(video.file_size)}
                    </span>
                  </div>

                  {/* Action Buttons */}
                  <div className="video-card-actions">
                    <button
                      className="edit-card-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        openEditModal(video);
                      }}
                      disabled={updateMetadataMutation.isPending}
                      title="Edit"
                      type="button"
                    >
                      Edit
                    </button>
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
                      <DeleteIcon size={18} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Upload Modal */}
      {isUploadModalOpen && (
        <div
          className="upload-modal-overlay"
          onClick={() => setIsUploadModalOpen(false)}
        >
          <div className="upload-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Upload Video</h2>
              <button
                className="close-btn"
                onClick={() => setIsUploadModalOpen(false)}
                aria-label="Close"
              >
                <CloseIcon size={18} />
              </button>
            </div>
            <div className="modal-content">
              <VideoUpload onUploadSuccess={handleUploadSuccess} />
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isEditModalOpen && editingVideo && (
        <div
          className="upload-modal-overlay"
          onClick={() => setIsEditModalOpen(false)}
        >
          <div className="upload-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Edit Video Details</h2>
              <button
                className="close-btn"
                onClick={() => setIsEditModalOpen(false)}
                aria-label="Close"
                type="button"
              >
                <CloseIcon size={18} />
              </button>
            </div>
            <div className="modal-content">
              <div className="edit-video-form">
                <div className="edit-video-two-col">
                  <div className="edit-video-field">
                    <label>
                      Session Type{' '}
                      <span className="required-asterisk" aria-label="required">
                        *
                      </span>
                    </label>
                    <select
                      value={editSessionType}
                      onChange={(e) => setEditSessionType(e.target.value)}
                      disabled={updateMetadataMutation.isPending}
                    >
                      <option value="">Select session type</option>
                      <option value="serve_practice">Serve Practice</option>
                      <option value="match">Match</option>
                      <option value="other">Other</option>
                    </select>
                  </div>

                  <div className="edit-video-field">
                    <label>Camera Angle</label>
                    <select
                      value={editCameraAngle}
                      onChange={(e) => setEditCameraAngle(e.target.value)}
                      disabled={updateMetadataMutation.isPending}
                    >
                      <option value="">Select camera angle</option>
                      <option value="behind">Behind</option>
                      <option value="profile">Profile</option>
                      <option value="unknown">Unknown</option>
                    </select>
                  </div>
                </div>

                <div className="edit-video-section">
                  <div className="edit-video-section-header">
                    <div className="edit-video-section-title">
                      Who Is Serving?
                    </div>
                    <p className="edit-video-section-subtitle">
                      New serves detected in this video will be saved under this
                      player.
                    </p>
                  </div>

                  <div className="edit-video-radio-group edit-video-radio-group--horizontal">
                    <label>
                      <input
                        type="radio"
                        name="editPlayerTag"
                        value="you"
                        checked={editPlayerTag === 'you'}
                        onChange={() => setEditPlayerTag('you')}
                        disabled={updateMetadataMutation.isPending}
                      />
                      <span>{playerProfile?.name || 'Your Profile'}</span>
                    </label>
                    <label>
                      <input
                        type="radio"
                        name="editPlayerTag"
                        value="someone_else"
                        checked={editPlayerTag === 'someone_else'}
                        onChange={() => setEditPlayerTag('someone_else')}
                        disabled={updateMetadataMutation.isPending}
                      />
                      <span>Someone Else</span>
                    </label>
                  </div>
                  <div className="edit-video-checkbox-wrapper">
                    <label className="edit-video-checkbox">
                      <input
                        type="checkbox"
                        checked={applyToExistingServes}
                        onChange={(e) =>
                          setApplyToExistingServes(e.target.checked)
                        }
                        disabled={updateMetadataMutation.isPending}
                      />
                      <span>
                        Also update serves already detected in this video
                      </span>
                    </label>
                    <p className="edit-video-note edit-video-note--compact">
                      Only affects serves for this video.
                    </p>
                  </div>
                </div>

                {editError && (
                  <div className="edit-video-error">{editError}</div>
                )}
              </div>
            </div>
            <div className="edit-video-actions">
              <button
                type="button"
                className="edit-video-cancel"
                onClick={() => setIsEditModalOpen(false)}
                disabled={updateMetadataMutation.isPending}
              >
                Cancel
              </button>
              <button
                type="button"
                className="edit-video-save"
                onClick={handleEditSave}
                disabled={!editSessionType || updateMetadataMutation.isPending}
              >
                {updateMetadataMutation.isPending
                  ? 'Saving...'
                  : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoList;
