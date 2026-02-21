import React, { useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
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
import VideoEditModal from './VideoEditModal';
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
  const [editingVideo, setEditingVideo] = useState<VideoMetadata | null>(null);

  // Use React Query hooks for data fetching
  const {
    data: videos = [],
    isLoading: videosLoading,
    error: videosError,
    refetch: refetchVideos,
  } = useVideos();

  const videoIds = videos.map((v: VideoMetadata) => v.id);
  const { isLoading: statusesLoading } = useVideoAnalysisStatuses(videoIds);

  const { data: playerProfile } = usePlayerProfile();

  const deleteVideoMutation = useDeleteVideo();
  const updateMetadataMutation = useUpdateVideoMetadata();

  const loading = videosLoading || statusesLoading;
  const error = videosError ? 'Failed to load videos. Please try again.' : null;

  const handleDelete = async (videoId: number) => {
    try {
      await deleteVideoMutation.mutateAsync(videoId);
      onVideoDeleted?.();
    } catch (err: unknown) {
      // Silently handle deletion errors - mutation already handles error state
    }
  };

  const handleViewAnalysis = (videoId: number) => {
    if (onViewAnalysis) {
      const video = videos.find((v: VideoMetadata) => v.id === videoId);
      if (video) {
        onViewAnalysis(video);
      }
    }
  };

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

  const handleUploadSuccess = useCallback(
    (video: VideoMetadata) => {
      // Invalidate videos cache to refetch the list with the new video
      queryClient.invalidateQueries({ queryKey: ['videos'] });
      setIsUploadModalOpen(false);
    },
    [queryClient]
  );

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
            return (
              <div
                key={video.id}
                className="video-card"
                onClick={() => handleViewAnalysis(video.id)}
                style={{ cursor: 'pointer' }}
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
                        setEditingVideo(video);
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
      {editingVideo && (
        <VideoEditModal
          video={editingVideo}
          onClose={() => setEditingVideo(null)}
        />
      )}
    </div>
  );
};

export default VideoList;
