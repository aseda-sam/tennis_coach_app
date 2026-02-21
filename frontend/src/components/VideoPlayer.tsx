import React from 'react';
import {
  useVideoPlayerState,
  type ViewMode,
  ZOOM_LEVELS,
  contactTimestampsQueryKey,
} from '../hooks/useVideoPlayerState';
import type { ServeWindowCreate } from '../types/serveWindow';
import AddServeWindowButton from './AddServeWindowButton';
import { CloseIcon, WarningIcon } from './Icons';
import LoadingIndicator from './LoadingIndicator';
import ServeWindowModal from './ServeWindowModal';
import StickFigureCanvas from './StickFigureCanvas';
import VideoOverlay from './VideoOverlay';
import VideoPlayerControls from './VideoPlayerControls';
import VideoPlayerTimeline from './VideoPlayerTimeline';
import './VideoPlayer.css';

const VIEW_OPTIONS: { value: ViewMode; label: string; title: string }[] = [
  { value: 'video', label: 'Video', title: 'Video only' },
  {
    value: 'skeleton',
    label: 'Skeleton',
    title: 'Video with skeleton overlay',
  },
  { value: 'stickfigure', label: 'Stick', title: 'Video with stick figure' },
];

interface VideoPlayerProps {
  videoUrl: string;
  title: string;
  onClose?: () => void;
  showControls?: boolean;
  aspectRatioMode?: 'cover' | 'contain' | 'auto';
  videoId?: number;
  hasPoseData?: boolean;
  controlsBelow?: boolean;
  onContactNavigate?: (serveWindowId: number) => void;
  onNavigateReady?: (navigateFn: (serveWindowId: number) => void) => void;
  isDemo?: boolean;
  naturalScroll?: boolean;
  lowConfidenceThreshold?: number;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoUrl,
  title,
  onClose,
  showControls = true,
  aspectRatioMode = 'contain',
  videoId,
  hasPoseData = false,
  controlsBelow = false,
  onContactNavigate,
  onNavigateReady,
  isDemo = false,
  naturalScroll: naturalScrollProp = false,
  lowConfidenceThreshold = 0.6,
}) => {
  const s = useVideoPlayerState({
    videoUrl,
    title,
    onClose,
    showControls,
    aspectRatioMode,
    videoId,
    hasPoseData,
    controlsBelow,
    onContactNavigate,
    onNavigateReady,
    isDemo,
    naturalScroll: naturalScrollProp,
    lowConfidenceThreshold,
  });

  const handleAddServeWindow = async (serveWindow: ServeWindowCreate) => {
    await s.createServeWindow(serveWindow);
    if (videoId) {
      s.queryClient.invalidateQueries({
        queryKey: contactTimestampsQueryKey(videoId),
      });
    }
    if (s.openRange) s.clearRangeMarks();
  };

  const handleFormOpen = (timestamp: number) => {
    const video = s.videoRef.current;
    if (video && s.isPlaying) {
      video.pause();
      s.wasPlayingRef.current = true;
    } else {
      s.wasPlayingRef.current = false;
    }
    s.setHighlightTimestamp(timestamp);
  };

  const handleFormClose = () => {
    s.setHighlightTimestamp(null);
    s.setOpenRange(null);
    s.wasPlayingRef.current = false;
  };

  const handleModalClose = () => {
    s.setIsModalOpen(false);
    s.setSelectedServeWindow(null);
    s.setSelectedServeWindowId(undefined);
  };

  const handleModalUpdate = async (
    serveWindowId: number,
    updates: Parameters<typeof s.updateServeWindow>[1]
  ) => {
    await s.updateServeWindow(serveWindowId, updates);
    if (videoId && updates.contact_timestamp !== undefined) {
      s.queryClient.invalidateQueries({
        queryKey: contactTimestampsQueryKey(videoId),
      });
    }
  };

  const handleModalDelete = async (serveWindowId: number) => {
    await s.deleteServeWindow(serveWindowId);
    if (videoId) {
      s.queryClient.invalidateQueries({
        queryKey: contactTimestampsQueryKey(videoId),
      });
    }
  };

  return (
    <div
      className={`video-player-container ${controlsBelow ? 'controls-below' : ''}`}
    >
      {s.detectionMessage && (
        <div className="auto-detect-toast" role="status">
          {s.detectionMessage}
        </div>
      )}
      {onClose && (
        <div className="video-player-header">
          <button className="close-btn" onClick={onClose}>
            <CloseIcon size={20} />
          </button>
          <h2 className="video-title">{title}</h2>
        </div>
      )}

      <div className="video-player-wrapper">
        {hasPoseData && (
          <div className="video-player-view-bar">
            <span className="video-player-view-bar__label">View</span>
            <div
              className="video-player-view-bar__segmented"
              role="radiogroup"
              aria-label="Overlay mode"
            >
              {VIEW_OPTIONS.map(({ value, label, title: optTitle }) => (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={s.viewMode === value}
                  title={optTitle}
                  className={`video-player-view-bar__option ${s.viewMode === value ? 'video-player-view-bar__option--active' : ''}`}
                  onClick={() => s.setViewMode(value)}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="video-player-zoom-controls">
              <button
                type="button"
                className="video-player-zoom-btn"
                onClick={s.zoomOut}
                disabled={s.zoomLevel === ZOOM_LEVELS[0]}
                title="Zoom out"
              >
                −
              </button>
              <button
                type="button"
                className="video-player-zoom-level"
                onClick={s.resetZoom}
                title="Reset zoom"
              >
                {Math.round(s.zoomLevel * 100)}%
              </button>
              <button
                type="button"
                className="video-player-zoom-btn"
                onClick={s.zoomIn}
                disabled={s.zoomLevel === ZOOM_LEVELS[ZOOM_LEVELS.length - 1]}
                title="Zoom in"
              >
                +
              </button>
            </div>
          </div>
        )}

        {hasPoseData && !controlsBelow && s.hasPoseDataForDetection && (
          <div className="overlay-toggle-container">
            <div className="auto-detect-wrap">
              <button
                className={`auto-detect-btn ${s.hasExistingDetections ? 'auto-detect-btn--has-detections' : ''}`}
                onClick={s.handleAutoDetect}
                disabled={s.isRunningDetection}
                title={
                  s.hasExistingDetections
                    ? 'Detection already run - click to re-detect'
                    : 'Auto-detect serve windows'
                }
              >
                {s.isRunningDetection ? 'Detecting...' : 'Auto-detect serves'}
              </button>
              {s.proposals.length > 0 && (
                <button
                  className="auto-detect-clear-btn"
                  onClick={s.handleClearProposals}
                  disabled={s.isRunningDetection}
                  title="Clear all pending proposals"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        )}

        <div className="video-player-main">
          <div
            ref={s.containerRef}
            className={`video-container video-container-${aspectRatioMode} ${s.isPlaying ? 'playing' : 'paused'} ${s.isScrubbing ? 'scrubbing' : ''}`}
            onClick={s.handleVideoClick}
            style={{ position: 'relative' }}
          >
            {s.resolvedVideoUrl && (
              <div
                className="video-zoom-wrapper"
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  overflow: 'hidden',
                  transform:
                    s.zoomLevel !== 1 ? `scale(${s.zoomLevel})` : 'none',
                  transformOrigin: 'center center',
                  transition: 'transform 0.2s ease-out',
                }}
              >
                <video
                  ref={s.videoRef}
                  src={s.resolvedVideoUrl}
                  className={`video-element video-element-${aspectRatioMode} ${s.viewMode === 'stickfigure' && hasPoseData ? 'video-element--hidden' : ''}`}
                  preload="metadata"
                  crossOrigin="anonymous"
                  data-testid="video-element"
                />
              </div>
            )}
            {videoId && s.viewMode === 'stickfigure' && hasPoseData && (
              <StickFigureCanvas
                videoId={videoId}
                currentTime={s.currentTime}
                fps={s.videoMetadata?.fps}
                isPlaying={s.isPlaying}
              />
            )}
            {videoId && s.viewMode === 'skeleton' && hasPoseData && (
              <VideoOverlay
                videoId={videoId}
                videoElement={s.videoRef.current}
                showOverlay={true}
                hasPoseData={hasPoseData}
                currentTime={s.currentTime}
                zoomLevel={s.zoomLevel}
              />
            )}
            {s.showScrollHint && (
              <div className="scroll-hint">
                <span className="scroll-hint__icon">&#x27F3;</span>
                <span>Use scroll wheel to navigate frames</span>
              </div>
            )}
            {s.isLoadingUrl && (
              <div className="loading-overlay">
                <LoadingIndicator
                  size="lg"
                  tone="light"
                  label="Loading Video..."
                />
              </div>
            )}
            {!controlsBelow && (
              <AddServeWindowButton
                currentTime={s.currentTime}
                videoId={videoId || 0}
                videoDuration={s.duration}
                fps={s.videoMetadata?.fps}
                onAddServeWindow={handleAddServeWindow}
                isVisible={s.isAddServeWindowVisible}
                isReadOnly={isDemo}
                placement="overlay"
                onSeek={s.seekToTime}
                openRequestId={s.openRequestId}
                openRange={s.openRange ?? undefined}
                onFormOpen={handleFormOpen}
                onFormClose={handleFormClose}
              />
            )}
            {s.error && !s.isLoadingUrl && (
              <div className="error-overlay">
                <div className="error-message">
                  <span className="error-icon">
                    <WarningIcon size={24} color="white" />
                  </span>
                  <p>{s.error}</p>
                </div>
              </div>
            )}
            {showControls && !controlsBelow && (
              <VideoPlayerControls
                state={s}
                videoId={videoId}
                isDemo={isDemo}
                lowConfidenceThreshold={lowConfidenceThreshold}
              />
            )}
          </div>
        </div>
      </div>

      {showControls && controlsBelow && (
        <VideoPlayerTimeline
          state={s}
          videoId={videoId}
          isDemo={isDemo}
          lowConfidenceThreshold={lowConfidenceThreshold}
        />
      )}

      {!controlsBelow && (
        <ServeWindowModal
          serveWindow={s.selectedServeWindow}
          isOpen={s.isModalOpen}
          videoDuration={s.duration}
          currentTime={s.currentTime}
          isDemo={isDemo}
          mode="overlay"
          onClose={handleModalClose}
          onUpdate={handleModalUpdate}
          onDelete={handleModalDelete}
          onSeek={s.seekToTime}
        />
      )}
    </div>
  );
};

export default VideoPlayer;
