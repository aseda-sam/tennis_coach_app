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

function JobStatusBadge({
  status,
}: {
  status: DemoVideoListItem['job_status'];
}) {
  if (!status) return null;
  return (
    <span className="admin-demo-management__job-badge" data-status={status}>
      {status === 'transcoding' ? 'Transcoding…' : 'Analyzing…'}
    </span>
  );
}

const AdminDemoManagement: React.FC<AdminDemoManagementProps> = ({
  onOpenVideo,
  onNavigateToDemo,
}) => {
  const queryClient = useQueryClient();
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const {
    data: demoVideos,
    isLoading,
    error,
  } = useQuery<DemoVideoListItem[]>({
    queryKey: ['admin-demo-videos'],
    queryFn: () => videoApi.listDemoVideos(),
    // Poll faster when any video has an active job
    refetchInterval: (query) => {
      const videos = query.state.data;
      const hasActiveJob = videos?.some((v) => v.job_status !== null);
      return hasActiveJob ? 5000 : 30000;
    },
  });

  const setActiveMutation = useMutation({
    mutationFn: (videoId: number) => videoApi.setActiveDemo(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-demo-videos'] });
      queryClient.invalidateQueries({ queryKey: ['demo-video'] });
    },
  });

  const analyzePoseMutation = useMutation({
    mutationFn: (videoId: number) => videoApi.analyzeDemoPose(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-demo-videos'] });
    },
  });

  const deleteVideoMutation = useMutation({
    mutationFn: (videoId: number) => videoApi.deleteDemoVideo(videoId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-demo-videos'] });
      queryClient.invalidateQueries({ queryKey: ['demo-video'] });
      setConfirmDeleteId(null);
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
      setActiveMutation.mutate(videoId);
    }
  };

  const handleAnalyzePose = (videoId: number) => {
    if (
      window.confirm(
        'Start pose analysis for this demo video? This may take several minutes.'
      )
    ) {
      analyzePoseMutation.mutate(videoId);
    }
  };

  const handleOpenVideo = (videoId: number) => {
    openVideoMutation.mutate(videoId);
  };

  const handleUploadSuccess = (video: VideoMetadata) => {
    queryClient.invalidateQueries({ queryKey: ['admin-demo-videos'] });
    setShowUploadModal(false);
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
        <h2>Demo Videos</h2>
        <button
          className="admin-demo-management__action-btn primary"
          onClick={() => setShowUploadModal(true)}
          type="button"
        >
          Upload Demo Video
        </button>
      </div>

      <div className="admin-demo-management__content">
        {/* Active Demo */}
        {activeDemo && (
          <div className="admin-demo-management__active-section">
            <p className="admin-demo-management__section-label">Active Demo</p>
            <div
              className="admin-demo-management__active-card"
              onClick={onNavigateToDemo}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && onNavigateToDemo()}
            >
              <div className="admin-demo-management__active-card-main">
                <strong>{activeDemo.filename}</strong>
                <span className="admin-demo-management__badge">LIVE</span>
              </div>
              <div className="admin-demo-management__status-row">
                <span
                  className={
                    activeDemo.has_pose_analysis ? 'status-ok' : 'status-warn'
                  }
                >
                  {activeDemo.has_pose_analysis
                    ? 'Pose analysis ready'
                    : 'No pose analysis'}
                </span>
                {activeDemo.serve_window_count > 0 && (
                  <span className="status-ok">
                    {activeDemo.serve_window_count} key moment
                    {activeDemo.serve_window_count !== 1 ? 's' : ''}
                  </span>
                )}
                <JobStatusBadge status={activeDemo.job_status} />
              </div>
              <span className="admin-demo-management__active-card-hint">
                Click to preview demo →
              </span>
            </div>
          </div>
        )}

        {/* All Demo Videos */}
        <div className="admin-demo-management__videos-section">
          <p className="admin-demo-management__section-label">
            All Demo Videos
          </p>
          {!demoVideos || demoVideos.length === 0 ? (
            <p className="admin-demo-management__empty">No demo videos yet.</p>
          ) : (
            <div className="admin-demo-management__videos-grid">
              {demoVideos.map((video) => (
                <div
                  key={video.id}
                  className={`admin-demo-management__video-card ${video.is_active_demo ? 'active' : ''}`}
                  onClick={() => handleOpenVideo(video.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) =>
                    e.key === 'Enter' && handleOpenVideo(video.id)
                  }
                >
                  <div className="admin-demo-management__video-card-header">
                    <strong title={video.filename}>{video.filename}</strong>
                    {video.is_active_demo && (
                      <span className="admin-demo-management__badge">LIVE</span>
                    )}
                  </div>

                  <div className="admin-demo-management__video-card-meta">
                    <span>
                      {new Date(video.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  <div className="admin-demo-management__status-row">
                    {video.job_status ? (
                      <JobStatusBadge status={video.job_status} />
                    ) : (
                      <>
                        <span
                          className={
                            video.has_pose_analysis
                              ? 'status-ok'
                              : 'status-warn'
                          }
                        >
                          {video.has_pose_analysis ? 'Pose ready' : 'No pose'}
                        </span>
                        <span
                          className={
                            video.serve_window_count > 0
                              ? 'status-ok'
                              : 'status-warn'
                          }
                        >
                          {video.serve_window_count > 0
                            ? `${video.serve_window_count} serve${video.serve_window_count !== 1 ? 's' : ''}`
                            : 'No serves'}
                        </span>
                      </>
                    )}
                  </div>

                  <div
                    className="admin-demo-management__video-card-actions"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {!video.is_active_demo && !video.job_status && (
                      <button
                        className="admin-demo-management__action-btn"
                        onClick={() => handleSetActive(video.id)}
                        disabled={setActiveMutation.isPending}
                        type="button"
                      >
                        Set Live
                      </button>
                    )}
                    {!video.has_pose_analysis && !video.job_status && (
                      <button
                        className="admin-demo-management__action-btn"
                        onClick={() => handleAnalyzePose(video.id)}
                        disabled={analyzePoseMutation.isPending}
                        type="button"
                      >
                        Run Pose
                      </button>
                    )}
                    {video.is_active_demo ? (
                      <span className="admin-demo-management__delete-blocked">
                        Set another video live before deleting
                      </span>
                    ) : confirmDeleteId === video.id ? (
                      <>
                        <button
                          className="admin-demo-management__action-btn danger"
                          onClick={() => deleteVideoMutation.mutate(video.id)}
                          disabled={deleteVideoMutation.isPending}
                          type="button"
                        >
                          {deleteVideoMutation.isPending
                            ? 'Deleting…'
                            : 'Confirm Delete'}
                        </button>
                        <button
                          className="admin-demo-management__action-btn"
                          onClick={() => setConfirmDeleteId(null)}
                          type="button"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <button
                        className="admin-demo-management__action-btn"
                        onClick={() => setConfirmDeleteId(video.id)}
                        disabled={deleteVideoMutation.isPending}
                        type="button"
                      >
                        Delete
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
              <button
                onClick={() => setShowUploadModal(false)}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            <div className="admin-demo-management__upload-modal-body">
              <VideoUpload
                onUploadSuccess={handleUploadSuccess}
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
