import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import React, { useState } from 'react';
import { videoApi } from '../services/api';
import { DemoVideoListItem, VideoMetadata } from '../types/video';
import './AdminDemoManagement.css';
import LoadingIndicator from './LoadingIndicator';
import VideoUpload from './VideoUpload';

interface AdminDemoManagementProps {
  onOpenVideo: (video: VideoMetadata) => void;
  onNavigateToDemo: () => void;
}

const AdminDemoManagement: React.FC<AdminDemoManagementProps> = ({
  onOpenVideo,
  onNavigateToDemo,
}) => {
  const queryClient = useQueryClient();
  const [selectedVideoId, setSelectedVideoId] = useState<number | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Fetch demo videos list
  const {
    data: demoVideos,
    isLoading,
    error,
  } = useQuery<DemoVideoListItem[]>({
    queryKey: ['admin-demo-videos'],
    queryFn: () => videoApi.listDemoVideos(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Set active demo mutation
  const setActiveMutation = useMutation({
    mutationFn: (videoId: number) => videoApi.setActiveDemo(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-demo-videos'] });
      queryClient.invalidateQueries({ queryKey: ['demo-video'] });
      setSelectedVideoId(null);
    },
  });

  // Analyze pose mutation
  const analyzePoseMutation = useMutation({
    mutationFn: (videoId: number) => videoApi.analyzeDemoPose(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-demo-videos'] });
      setSelectedVideoId(null);
    },
  });

  const openVideoMutation = useMutation({
    mutationFn: (videoId: number) => videoApi.getVideo(videoId),
    onSuccess: (video) => {
      onOpenVideo(video);
    },
  });

  const handleSetActive = (videoId: number) => {
    if (
      window.confirm(
        'Set this video as the active demo? This will replace the current active demo.'
      )
    ) {
      setSelectedVideoId(videoId);
      setActiveMutation.mutate(videoId);
    }
  };

  const handleAnalyzePose = (videoId: number) => {
    if (
      window.confirm(
        'Start pose analysis for this demo video? This may take several minutes.'
      )
    ) {
      setSelectedVideoId(videoId);
      analyzePoseMutation.mutate(videoId);
    }
  };

  const handleOpenVideo = (videoId: number) => {
    openVideoMutation.mutate(videoId);
  };

  const handleUploadSuccess = (video: VideoMetadata) => {
    queryClient.invalidateQueries({ queryKey: ['admin-demo-videos'] });
    setShowUploadModal(false);
    setSelectedVideoId(video.id);
  };

  if (isLoading) {
    return (
      <div className="admin-demo-management">
        <div className="admin-demo-management__loading">
          <LoadingIndicator size="lg" label="Loading demo videos..." />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-demo-management">
        <div className="admin-demo-management__error">
          <p>Failed to load demo videos. Please try again.</p>
          <button
            onClick={() =>
              queryClient.invalidateQueries({ queryKey: ['admin-demo-videos'] })
            }
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const activeDemo = demoVideos?.find((v) => v.is_active_demo);

  return (
    <div className="admin-demo-management">
      <div className="admin-demo-management__header">
        <h2>Demo Video Management</h2>
      </div>

      <div className="admin-demo-management__content">
        {/* Active Demo Status - Clickable to go to demo */}
        {activeDemo && (
          <div className="admin-demo-management__active-section">
            <h3>Active Demo</h3>
            <div
              className="admin-demo-management__active-card"
              onClick={onNavigateToDemo}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && onNavigateToDemo()}
            >
              <div className="admin-demo-management__active-card-content">
                <div className="admin-demo-management__active-card-main">
                  <strong>{activeDemo.filename}</strong>
                  <span className="admin-demo-management__badge">ACTIVE</span>
                </div>
                <div className="admin-demo-management__status-row">
                  <span
                    className={
                      activeDemo.has_pose_analysis
                        ? 'status-ok'
                        : 'status-warning'
                    }
                  >
                    {activeDemo.has_pose_analysis
                      ? '✓ Pose Analysis'
                      : '⚠ No Pose Analysis'}
                  </span>
                  <span
                    className={
                      activeDemo.serve_attempt_count > 0
                        ? 'status-ok'
                        : 'status-warning'
                    }
                  >
                    {activeDemo.serve_attempt_count > 0
                      ? `✓ ${activeDemo.serve_attempt_count} Key Moment${activeDemo.serve_attempt_count !== 1 ? 's' : ''}`
                      : '⚠ No Key Moments'}
                  </span>
                </div>
                <span className="admin-demo-management__active-card-hint">
                  Click to view demo
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="admin-demo-management__actions">
          <button
            className="admin-demo-management__action-btn primary"
            onClick={() => setShowUploadModal(true)}
            type="button"
          >
            Upload Demo Video
          </button>
          <span className="admin-demo-management__helper-text">
            Open a video to tag key moments or review analysis.
          </span>
        </div>

        {/* Demo Videos List */}
        <div className="admin-demo-management__videos-section">
          <h3>All Demo Videos</h3>
          {!demoVideos || demoVideos.length === 0 ? (
            <p className="admin-demo-management__empty">
              No demo videos found.
            </p>
          ) : (
            <div className="admin-demo-management__videos-grid">
              {demoVideos.map((video) => (
                <div
                  key={video.id}
                  className={`admin-demo-management__video-card ${
                    video.is_active_demo ? 'active' : ''
                  }`}
                  onClick={() => handleOpenVideo(video.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) =>
                    e.key === 'Enter' && handleOpenVideo(video.id)
                  }
                >
                  <div className="admin-demo-management__video-card-header">
                    <strong>{video.filename}</strong>
                    {video.is_active_demo && (
                      <span className="admin-demo-management__badge">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <div className="admin-demo-management__video-card-meta">
                    <span>ID: {video.id}</span>
                    <span>
                      {new Date(video.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <div className="admin-demo-management__status-row">
                    <span
                      className={
                        video.has_pose_analysis ? 'status-ok' : 'status-warning'
                      }
                    >
                      {video.has_pose_analysis ? '✓ Pose' : '⚠ No Pose'}
                    </span>
                    <span
                      className={
                        video.serve_attempt_count > 0
                          ? 'status-ok'
                          : 'status-warning'
                      }
                    >
                      {video.serve_attempt_count > 0
                        ? `✓ ${video.serve_attempt_count} Serve${video.serve_attempt_count !== 1 ? 's' : ''}`
                        : '⚠ No Serves'}
                    </span>
                  </div>
                  <div
                    className="admin-demo-management__video-card-actions"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {!video.is_active_demo && (
                      <button
                        className="admin-demo-management__action-btn"
                        onClick={() => handleSetActive(video.id)}
                        disabled={setActiveMutation.isPending}
                        type="button"
                      >
                        {setActiveMutation.isPending &&
                        selectedVideoId === video.id
                          ? 'Setting...'
                          : 'Set Active'}
                      </button>
                    )}
                    {!video.has_pose_analysis && (
                      <button
                        className="admin-demo-management__action-btn"
                        onClick={() => handleAnalyzePose(video.id)}
                        disabled={analyzePoseMutation.isPending}
                        type="button"
                      >
                        {analyzePoseMutation.isPending &&
                        selectedVideoId === video.id
                          ? 'Starting...'
                          : 'Run Pose'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="admin-demo-management__upload-modal">
          <div className="admin-demo-management__upload-modal-content">
            <div className="admin-demo-management__upload-modal-header">
              <h3>Upload Demo Video</h3>
              <button onClick={() => setShowUploadModal(false)}>×</button>
            </div>
            <div className="admin-demo-management__upload-modal-body">
              <VideoUpload
                onUploadSuccess={(video) => {
                  handleUploadSuccess(video);
                }}
                defaultIsDemo={true}
                forceDemo={true}
                hideDemoToggle={true}
                demoNoticeText="Uploads from this panel are automatically marked as demo videos."
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDemoManagement;
