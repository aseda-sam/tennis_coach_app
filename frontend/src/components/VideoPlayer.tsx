import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useBallContacts } from '../hooks/useBallContacts';
import { useVideoMetadata } from '../hooks/useVideos';
import { useVideoUrl } from '../hooks/useVideoUrl';
import { BallContact, BallContactCreate } from '../services/ballContactApi';
import AddContactButton from './AddContactButton';
import BallContactMarker from './BallContactMarker';
import BallContactModal from './BallContactModal';
import {
  AnalyticsIcon,
  ArrowBackIcon,
  CloseIcon,
  FullscreenIcon,
  PauseIcon,
  PlayIcon,
  VolumeIcon,
  VolumeOffIcon,
  WarningIcon,
} from './Icons';
import PostureAnalysisSidebar from './PostureAnalysisSidebar';
import VideoOverlay from './VideoOverlay';
import './VideoPlayer.css';

interface VideoPlayerProps {
  videoUrl: string;
  title: string;
  onClose?: () => void;
  showControls?: boolean;
  aspectRatioMode?: 'cover' | 'contain' | 'auto';
  videoId?: number; // Video ID for fetching ball contacts
  showPostureAnalysis?: boolean; // Show posture analysis sidebar
  hasPoseData?: boolean; // Whether pose detection data exists
  controlsBelow?: boolean; // Render controls below video instead of overlaying
  onContactNavigate?: (contactId: number) => void; // Callback when contact is navigated to
  onNavigateReady?: (navigateFn: (contactId: number) => void) => void; // Callback to expose navigate function
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoUrl,
  title,
  onClose,
  showControls = true,
  aspectRatioMode = 'contain',
  videoId,
  showPostureAnalysis = false,
  hasPoseData = false,
  controlsBelow = false,
  onContactNavigate,
  onNavigateReady,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [videoAspectRatio, setVideoAspectRatio] = useState<number | null>(null);
  const [isScrubbing, setIsScrubbing] = useState(false);
  const [selectedContact, setSelectedContact] = useState<BallContact | null>(
    null
  );
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isPostureSidebarOpen, setIsPostureSidebarOpen] =
    useState(showPostureAnalysis);
  const [selectedContactId, setSelectedContactId] = useState<
    number | undefined
  >();
  const [showOverlay, setShowOverlay] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const scrubberTrackRef = useRef<HTMLDivElement>(null);
  const [highlightTimestamp, setHighlightTimestamp] = useState<number | null>(null);
  const wasPlayingRef = useRef<boolean>(false);
  const [hoverTimestamp, setHoverTimestamp] = useState<number | null>(null);
  const [openTimestamp, setOpenTimestamp] = useState<number | null>(null);
  const [openRequestId, setOpenRequestId] = useState(0);
  const isAddContactVisible = !!videoId && !error && duration > 0;

  // Use ball contacts hook if videoId is provided
  const {
    contacts: ballContacts,
    updateContact,
    deleteContact,
    createContact,
  } = useBallContacts({
    videoId: videoId || 0,
    autoRefresh: !!videoId,
  });

  // Use React Query hook for video URL resolution
  const { resolvedUrl: resolvedVideoUrl, isLoading: isLoadingUrl } = useVideoUrl({
    videoId,
    videoUrl,
    expiresIn: 3600,
  });

  // Use React Query hook for video metadata
  const { data: videoMetadata } = useVideoMetadata(videoId);

  // Reset aspect ratio when video URL changes
  useEffect(() => {
    setVideoAspectRatio(null);
  }, [resolvedVideoUrl]);

  // Clear error state when URL changes
  useEffect(() => {
    setError(null);
  }, [resolvedVideoUrl]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      const currentVideo = videoRef.current;
      if (!currentVideo) return;
      setDuration(currentVideo.duration);
      setError(null);

      // Calculate and store the video's natural aspect ratio
      if (currentVideo.videoWidth && currentVideo.videoHeight) {
        const aspectRatio = currentVideo.videoWidth / currentVideo.videoHeight;
        setVideoAspectRatio(aspectRatio);
      }
    };

    const handleTimeUpdate = () => {
      const currentVideo = videoRef.current;
      if (!currentVideo) return;
      setCurrentTime(currentVideo.currentTime);
    };

    const handlePlay = () => {
      setIsPlaying(true);
    };

    const handlePause = () => {
      setIsPlaying(false);
    };

    const handleError = (e: Event) => {
      const currentVideo = videoRef.current;
      if (!currentVideo) return;

      // Suppress errors during URL loading to prevent error flash
      if (isLoadingUrl) {
        return;
      }

      // Suppress errors if video src is empty (we're still loading the URL)
      if (!currentVideo.currentSrc || currentVideo.currentSrc === '') {
        return;
      }

      // Provide more specific error messages based on error type
      let errorMessage =
        'Failed to load video. Please check if the video file exists.';
      if (currentVideo.error) {
        switch (currentVideo.error.code) {
          case MediaError.MEDIA_ERR_ABORTED:
            errorMessage = 'Video loading was aborted.';
            break;
          case MediaError.MEDIA_ERR_NETWORK:
            errorMessage =
              'Network error occurred while loading video. This may be a CORS issue or the video URL is not accessible.';
            break;
          case MediaError.MEDIA_ERR_DECODE:
            errorMessage = 'Video format is not supported or corrupted.';
            break;
          case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
            errorMessage = 'Video format is not supported by your browser.';
            break;
        }
      }

      // Add URL information to error message for debugging
      if (currentVideo.currentSrc) {
        errorMessage += ` (URL: ${currentVideo.currentSrc})`;
      }

      setError(errorMessage);
      setIsPlaying(false);
    };

    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('error', handleError);

    // Capture video element for cleanup to avoid ESLint warning
    const cleanupVideo = video;
    return () => {
      cleanupVideo.removeEventListener('loadedmetadata', handleLoadedMetadata);
      cleanupVideo.removeEventListener('timeupdate', handleTimeUpdate);
      cleanupVideo.removeEventListener('play', handlePlay);
      cleanupVideo.removeEventListener('pause', handlePause);
      cleanupVideo.removeEventListener('error', handleError);
    };
  }, [resolvedVideoUrl, isLoadingUrl]);

  // Handle aspect ratio mode changes
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    if (aspectRatioMode === 'auto' && videoAspectRatio) {
      const paddingBottom = (1 / videoAspectRatio) * 100;
      container.style.paddingBottom = `${paddingBottom}%`;
    } else {
      // Reset to default for other modes (CSS will handle the styling)
      container.style.paddingBottom = '';
    }

    // Cleanup function to reset styling when component unmounts
    return () => {
      if (container) {
        container.style.paddingBottom = '';
      }
    };
  }, [aspectRatioMode, videoAspectRatio]);

  const togglePlay = useCallback(async () => {
    const video = videoRef.current;
    if (!video) return;

    try {
      if (isPlaying) {
        video.pause();
      } else {
        await video.play();
      }
    } catch (err) {
      // Handle AbortError specifically (common when play is interrupted by pause)
      if (err instanceof Error && err.name === 'AbortError') {
        return; // Don't show error for this case - this is normal behavior
      }
      setError('Failed to play video. Please try again.');
    }
  }, [isPlaying]);

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (!video) return;

    const newTime = parseFloat(e.target.value);
    video.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleSeekStart = () => {
    const video = videoRef.current;
    if (!video) return;

    setIsScrubbing(true);

    // Pause video during scrubbing for precise positioning
    if (isPlaying) {
      video.pause();
    }
  };

  const handleSeekEnd = () => {
    const video = videoRef.current;
    if (!video) return;

    setIsScrubbing(false);

    // Only resume playing if video was playing before AND user wants it to continue
    // For ball contact creation, we want it to stay paused for precision
    // Users can manually click play if they want to resume
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (!video) return;

    const newVolume = parseFloat(e.target.value);
    video.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  };

  const toggleMute = () => {
    const video = videoRef.current;
    if (!video) return;

    if (isMuted) {
      video.volume = volume;
      setIsMuted(false);
    } else {
      video.volume = 0;
      setIsMuted(true);
    }
  };

  const formatTime = useCallback((time: number): string => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }, []);

  // Calculate frame-based step size for precise positioning
  const frameStep = useMemo(() => {
    if (videoMetadata?.fps && videoMetadata.fps > 0) {
      return 1 / videoMetadata.fps;
    }
    // Fallback to 0.1s if FPS is not available (backward compatibility)
    return 0.1;
  }, [videoMetadata?.fps]);

  // Frame navigation functions
  const navigateFrame = useCallback(
    (direction: 'forward' | 'backward') => {
      const video = videoRef.current;
      if (!video || !videoMetadata?.fps) return;

      const frameTime = 1 / videoMetadata.fps;
      const newTime =
        direction === 'forward'
          ? Math.min(video.currentTime + frameTime, duration)
          : Math.max(video.currentTime - frameTime, 0);

      // Update state first to ensure overlay gets the new time immediately
      setCurrentTime(newTime);
      // Then update video element (this will trigger seeked event)
      video.currentTime = newTime;
    },
    [videoMetadata?.fps, duration]
  );

  const navigateToNextFrame = useCallback(() => {
    navigateFrame('forward');
  }, [navigateFrame]);

  const navigateToPreviousFrame = useCallback(() => {
    navigateFrame('backward');
  }, [navigateFrame]);

  // Navigate to a specific contact by ID (exposed via callback)
  const navigateToContactById = useCallback(
    (contactId: number) => {
      const contact = ballContacts.find((c) => c.id === contactId);
      if (!contact) return;

      const video = videoRef.current;
      if (!video) return;

      // Pause if playing
      if (isPlaying) {
        video.pause();
      }

      // Update state first to ensure overlay gets the new time immediately
      setCurrentTime(contact.video_timestamp);
      setSelectedContactId(contact.id);
      
      // Then seek video (this will trigger seeked event which overlay listens to)
      video.currentTime = contact.video_timestamp;
      
      onContactNavigate?.(contact.id);
    },
    [ballContacts, isPlaying, onContactNavigate]
  );

  // Get sorted contacts for navigation
  const sortedContacts = useMemo(() => {
    return [...ballContacts].sort((a, b) => a.video_timestamp - b.video_timestamp);
  }, [ballContacts]);

  // Navigate to previous/next contact
  const navigateToPreviousContact = useCallback(() => {
    if (sortedContacts.length === 0) return;

    const video = videoRef.current;
    const videoTime = video?.currentTime ?? currentTime;

    // Find the contact before current time (with small tolerance)
    const tolerance = 0.1;
    const previousContacts = sortedContacts.filter(
      (c) => c.video_timestamp < videoTime - tolerance
    );

    if (previousContacts.length > 0) {
      const previousContact = previousContacts[previousContacts.length - 1];
      navigateToContactById(previousContact.id);
    }
  }, [sortedContacts, currentTime, navigateToContactById]);

  const navigateToNextContact = useCallback(() => {
    if (sortedContacts.length === 0) return;

    const video = videoRef.current;
    const videoTime = video?.currentTime ?? currentTime;

    // Find the contact after current time (with small tolerance)
    const tolerance = 0.1;
    const nextContact = sortedContacts.find(
      (c) => c.video_timestamp > videoTime + tolerance
    );

    if (nextContact) {
      navigateToContactById(nextContact.id);
    }
  }, [sortedContacts, currentTime, navigateToContactById]);

  // Check if previous/next navigation is available
  const hasPreviousContact = useMemo(() => {
    const tolerance = 0.1;
    return sortedContacts.some((c) => c.video_timestamp < currentTime - tolerance);
  }, [sortedContacts, currentTime]);

  const hasNextContact = useMemo(() => {
    const tolerance = 0.1;
    return sortedContacts.some((c) => c.video_timestamp > currentTime + tolerance);
  }, [sortedContacts, currentTime]);

  const navigateRef = useRef(navigateToContactById);

  useEffect(() => {
    navigateRef.current = navigateToContactById;
  }, [navigateToContactById]);

  const stableNavigateToContactById = useCallback((contactId: number) => {
    navigateRef.current(contactId);
  }, []);

  // Expose navigate function to parent
  useEffect(() => {
    if (onNavigateReady) {
      onNavigateReady(stableNavigateToContactById);
    }
  }, [onNavigateReady, stableNavigateToContactById]);

  // Open add contact form at current time (for keyboard shortcut)
  const openAddContactForm = useCallback(() => {
    if (!isAddContactVisible) return;

    const video = videoRef.current;
    const timestamp = video?.currentTime ?? currentTime;

    // Pause video if playing
    if (video && isPlaying) {
      video.pause();
      wasPlayingRef.current = true;
    } else {
      wasPlayingRef.current = false;
    }

    if (controlsBelow) {
      // For scrubber mode, use the programmatic open mechanism
      setOpenTimestamp(timestamp);
      setOpenRequestId((prev) => prev + 1);
      setHighlightTimestamp(timestamp);
    } else {
      // For overlay mode, trigger via the button's onFormOpen callback
      // We'll handle this by setting a state that the overlay AddContactButton can react to
      setHighlightTimestamp(timestamp);
      // The overlay AddContactButton will be triggered via a ref or we can add a similar mechanism
      // For now, let's use the same mechanism for consistency
      setOpenTimestamp(timestamp);
      setOpenRequestId((prev) => prev + 1);
    }
  }, [isAddContactVisible, currentTime, isPlaying, controlsBelow]);

  // Keyboard shortcuts for frame navigation, play/pause, and contact navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Only handle keyboard shortcuts when video player is focused or when not in input fields
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      switch (event.key) {
        case ' ':
        case 'Space':
          event.preventDefault();
          togglePlay();
          break;
        case 'ArrowLeft':
          event.preventDefault();
          navigateToPreviousFrame();
          break;
        case 'ArrowRight':
          event.preventDefault();
          navigateToNextFrame();
          break;
        case '[':
          event.preventDefault();
          navigateToPreviousContact();
          break;
        case ']':
          event.preventDefault();
          navigateToNextContact();
          break;
        case 'a':
        case 'A':
          event.preventDefault();
          openAddContactForm();
          break;
        default:
          break;
      }
    };

    // Add event listener to document
    document.addEventListener('keydown', handleKeyDown);

    // Cleanup function
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    togglePlay,
    navigateToPreviousFrame,
    navigateToNextFrame,
    navigateToPreviousContact,
    navigateToNextContact,
    openAddContactForm,
  ]);

  // Memoize formatted time strings to prevent unnecessary re-renders
  const formattedCurrentTime = useMemo(
    () => formatTime(currentTime),
    [currentTime, formatTime]
  );
  const formattedDuration = useMemo(
    () => formatTime(duration),
    [duration, formatTime]
  );

  const handleVideoClick = () => {
    // When controlsBelow is true, clicking video toggles play/pause
    if (controlsBelow) {
      togglePlay();
    }
  };

  const getTimestampFromClientX = useCallback(
    (clientX: number): number | null => {
      const track = scrubberTrackRef.current;
      if (!track || duration <= 0) return null;

      const rect = track.getBoundingClientRect();
      const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      return ratio * duration;
    },
    [duration]
  );

  const handleAddBandPointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      const timestamp = getTimestampFromClientX(event.clientX);
      if (timestamp !== null) {
        setHoverTimestamp(timestamp);
      }
    },
    [getTimestampFromClientX]
  );

  const handleAddBandPointerLeave = useCallback(() => {
    setHoverTimestamp(null);
  }, []);

  const handleAddBandPointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!isAddContactVisible) return;
      const timestamp = getTimestampFromClientX(event.clientX);
      if (timestamp === null) return;

      event.preventDefault();
      event.stopPropagation();
      setOpenTimestamp(timestamp);
      setOpenRequestId((prev) => prev + 1);
    },
    [getTimestampFromClientX, isAddContactVisible]
  );

  const toggleFullscreen = () => {
    const video = videoRef.current;
    if (!video) return;

    if (!document.fullscreenElement) {
      video.requestFullscreen().catch(() => {
        // Silently handle fullscreen errors - browser may not support it
      });
    } else {
      document.exitFullscreen().catch(() => {
        // Silently handle fullscreen exit errors
      });
    }
  };

  return (
    <div
      className={`video-player-container ${controlsBelow ? 'controls-below' : ''}`}
    >
      {onClose && (
        <div className="video-player-header">
          <button className="close-btn" onClick={onClose}>
            <CloseIcon size={20} />
          </button>
          <h2 className="video-title">{title}</h2>
          {videoId && (
            <button
              className="posture-analysis-toggle"
              onClick={() => setIsPostureSidebarOpen(!isPostureSidebarOpen)}
              title="Toggle posture analysis"
            >
              <AnalyticsIcon size={18} />
            </button>
          )}
        </div>
      )}

      <div
        className={`video-player-wrapper ${isPostureSidebarOpen ? 'with-sidebar' : ''}`}
        style={{
          minHeight: isPostureSidebarOpen ? '500px' : 'auto',
        }}
      >
        {/* Controls row (kept minimal) - only show when controlsBelow is false */}
        {hasPoseData && !controlsBelow && (
          <div className="overlay-toggle-container">
            <label className="overlay-toggle-label">
              <input
                type="checkbox"
                checked={showOverlay}
                onChange={(e) => setShowOverlay(e.target.checked)}
                className="overlay-toggle-checkbox"
              />
              <span className="overlay-toggle-text">Pose overlay</span>
            </label>
          </div>
        )}

        <div
          className={`video-player-main ${isPostureSidebarOpen ? 'with-sidebar' : ''}`}
        >
          {/* Video Container */}
          <div
            ref={containerRef}
            className={`video-container video-container-${aspectRatioMode} ${
              isPlaying ? 'playing' : 'paused'
            } ${isScrubbing ? 'scrubbing' : ''}`}
            onClick={handleVideoClick}
            style={{ position: 'relative' }}
          >
            {resolvedVideoUrl && (
              <video
                ref={videoRef}
                src={resolvedVideoUrl}
                className={`video-element video-element-${aspectRatioMode}`}
                preload="metadata"
                crossOrigin="anonymous"
                data-testid="video-element"
              />
            )}

            {/* Video Overlay */}
            {videoId && showOverlay && (
              <VideoOverlay
                videoId={videoId}
                videoElement={videoRef.current}
                showOverlay={showOverlay}
                hasPoseData={hasPoseData}
                currentTime={currentTime}
              />
            )}

            {/* Loading overlay while resolving URL */}
            {isLoadingUrl && (
              <div className="loading-overlay">
                <div className="loading-spinner" />
                <p>Loading video...</p>
              </div>
            )}

            {/* Add Contact Button (overlay placement) */}
            {!controlsBelow && (
              <AddContactButton
                currentTime={currentTime}
                videoId={videoId || 0}
                videoDuration={duration}
                fps={videoMetadata?.fps}
                onAddContact={async (contact: BallContactCreate) => {
                  await createContact(contact);
                }}
                isVisible={isAddContactVisible}
                placement="overlay"
                openRequestId={openRequestId}
                openTimestamp={openTimestamp ?? undefined}
                onFormOpen={(timestamp) => {
                  // Pause video if playing
                  const video = videoRef.current;
                  if (video && isPlaying) {
                    video.pause();
                    wasPlayingRef.current = true;
                  } else {
                    wasPlayingRef.current = false;
                  }
                  // Set highlight timestamp
                  setHighlightTimestamp(timestamp);
                }}
                onFormClose={() => {
                  // Clear highlight
                  setHighlightTimestamp(null);
                  // Clear open timestamp
                  setOpenTimestamp(null);
                  // Note: We don't auto-resume playback - user can manually play
                  wasPlayingRef.current = false;
                }}
              />
            )}

            {error && !isLoadingUrl && (
              <div className="error-overlay">
                <div className="error-message">
                  <span className="error-icon">
                    <WarningIcon size={24} color="white" />
                  </span>
                  <p>{error}</p>
                </div>
              </div>
            )}

            {showControls && !controlsBelow && (
              <div className="video-controls">
                <div className="progress-container">
                  <div className="progress-bar-wrapper">
                    <input
                      type="range"
                      className="progress-bar"
                      min="0"
                      max={duration || 0}
                      value={currentTime}
                      onChange={handleSeek}
                      onMouseDown={handleSeekStart}
                      onMouseUp={handleSeekEnd}
                      onTouchStart={handleSeekStart}
                      onTouchEnd={handleSeekEnd}
                      onKeyDown={(e) => {
                        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                          handleSeekStart();
                        }
                      }}
                      onKeyUp={(e) => {
                        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                          handleSeekEnd();
                        }
                      }}
                      step={frameStep}
                    />
                    {/* Contact markers */}
                    {ballContacts.length > 0 && duration > 0 && (
                      <div className="contact-markers">
                        {ballContacts.map((contact) => {
                          const position =
                            (contact.video_timestamp / duration) * 100;
                          const isSelected = selectedContactId === contact.id;

                          return (
                            <BallContactMarker
                              key={contact.id}
                              contact={contact}
                              position={position}
                              isSelected={isSelected}
                              onClick={() => {
                                setSelectedContact(contact);
                                setSelectedContactId(contact.id);
                                setIsModalOpen(true);
                              }}
                              onAnalyzeClick={() => {
                                setSelectedContactId(contact.id);
                                // The analysis will be handled by the sidebar
                              }}
                              showAnalysisButton={isPostureSidebarOpen}
                            />
                          );
                        })}
                      </div>
                    )}
                    {/* Highlight marker for locked contact timestamp */}
                    {highlightTimestamp !== null && duration > 0 && (
                      <div
                        className="contact-highlight-marker"
                        style={{
                          left: `${(highlightTimestamp / duration) * 100}%`,
                        }}
                      />
                    )}
                  </div>
                  <div className="time-display">
                    <span>{formattedCurrentTime}</span>
                    <span>{formattedDuration}</span>
                  </div>
                </div>

                <div className="controls-row">
                  <div className="left-controls">
                    <button
                      className="control-btn play-btn"
                      onClick={togglePlay}
                    >
                      {isPlaying ? (
                        <PauseIcon size={20} />
                      ) : (
                        <PlayIcon size={20} />
                      )}
                    </button>

                    <div className="volume-control">
                      <button
                        className="control-btn volume-btn"
                        onClick={toggleMute}
                      >
                        {isMuted ? (
                          <VolumeOffIcon size={20} />
                        ) : (
                          <VolumeIcon size={20} />
                        )}
                      </button>
                      <input
                        type="range"
                        className="volume-slider"
                        min="0"
                        max="1"
                        step="0.1"
                        value={isMuted ? 0 : volume}
                        onChange={handleVolumeChange}
                      />
                    </div>
                  </div>

                  <div className="right-controls">
                    <button
                      className="control-btn fullscreen-btn"
                      onClick={toggleFullscreen}
                    >
                      <FullscreenIcon size={20} />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Posture Analysis Sidebar */}
          {videoId && (
            <PostureAnalysisSidebar
              ballContacts={ballContacts}
              videoId={videoId}
              onContactSelect={(contact) => {
                setSelectedContact(contact);
                setSelectedContactId(contact.id);
                // Seek to the contact time
                const video = videoRef.current;
                if (video) {
                  video.currentTime = contact.video_timestamp;
                }
              }}
              selectedContactId={selectedContactId}
              isVisible={isPostureSidebarOpen}
              onClose={() => setIsPostureSidebarOpen(false)}
            />
          )}
        </div>
      </div>

      {/* Controls Below Video (when controlsBelow is true) - Outside video wrapper */}
      {showControls && controlsBelow && (
        <div className="video-controls-below">
          {/* Video Scrubber */}
          <div className="video-controls-below__scrubber">
            <div
              className="video-controls-below__scrubber-track"
              ref={scrubberTrackRef}
            >
              <div
                className="video-controls-below__add-band"
                onPointerMove={handleAddBandPointerMove}
                onPointerLeave={handleAddBandPointerLeave}
                onPointerDown={handleAddBandPointerDown}
                title="Click to add contact (or press A)"
              />
              <AddContactButton
                currentTime={currentTime}
                videoId={videoId || 0}
                videoDuration={duration}
                fps={videoMetadata?.fps}
                onAddContact={async (contact: BallContactCreate) => {
                  await createContact(contact);
                }}
                isVisible={isAddContactVisible}
                placement="scrubber"
                openRequestId={openRequestId}
                openTimestamp={openTimestamp ?? undefined}
                onFormOpen={(timestamp) => {
                  // Pause video if playing
                  const video = videoRef.current;
                  if (video && isPlaying) {
                    video.pause();
                    wasPlayingRef.current = true;
                  } else {
                    wasPlayingRef.current = false;
                  }
                  // Set highlight timestamp
                  setHighlightTimestamp(timestamp);
                }}
                onFormClose={() => {
                  // Clear highlight
                  setHighlightTimestamp(null);
                  // Clear open timestamp
                  setOpenTimestamp(null);
                  // Note: We don't auto-resume playback - user can manually play
                  wasPlayingRef.current = false;
                }}
              />
              <input
                type="range"
                className="video-controls-below__scrubber-input"
                min="0"
                max={duration || 0}
                value={currentTime}
                onChange={handleSeek}
                onMouseDown={handleSeekStart}
                onMouseUp={handleSeekEnd}
                onTouchStart={handleSeekStart}
                onTouchEnd={handleSeekEnd}
                step={frameStep}
              />
              {/* Contact markers */}
              {ballContacts.length > 0 && duration > 0 && (
                <div className="video-controls-below__contact-markers">
                  {ballContacts.map((contact) => {
                    const position = (contact.video_timestamp / duration) * 100;
                    const isSelected = selectedContactId === contact.id;

                    return (
                      <BallContactMarker
                        key={contact.id}
                        contact={contact}
                        position={position}
                        isSelected={isSelected}
                        onClick={() => {
                          setSelectedContact(contact);
                          setSelectedContactId(contact.id);
                          setIsModalOpen(true);
                        }}
                        onAnalyzeClick={() => {
                          setSelectedContactId(contact.id);
                        }}
                        showAnalysisButton={isPostureSidebarOpen}
                      />
                    );
                  })}
                </div>
              )}
              {hoverTimestamp !== null && duration > 0 && (
                <div
                  className="contact-hover-marker"
                  style={{
                    left: `${(hoverTimestamp / duration) * 100}%`,
                  }}
                />
              )}
              {/* Highlight marker for locked contact timestamp */}
              {highlightTimestamp !== null && duration > 0 && (
                <div
                  className="contact-highlight-marker"
                  style={{
                    left: `${(highlightTimestamp / duration) * 100}%`,
                  }}
                />
              )}
            </div>
            <div className="video-controls-below__time-labels">
              <span>{formattedCurrentTime}</span>
              <span>{formattedDuration}</span>
            </div>
          </div>

          {/* Controls Row */}
          <div className="video-controls-below__controls">
            <div className="video-controls-below__center-controls">
              <button
                className="video-controls-below__nav-btn"
                disabled={!hasPreviousContact}
                onClick={navigateToPreviousContact}
                title={hasPreviousContact ? 'Go to previous contact' : 'No previous contact'}
              >
                <ArrowBackIcon size={16} />
                Previous Contact
              </button>
              <button
                className="video-controls-below__play-btn"
                onClick={togglePlay}
              >
                {isPlaying ? <PauseIcon size={16} /> : <PlayIcon size={16} />}
              </button>
              <button
                className="video-controls-below__next-btn"
                disabled={!hasNextContact}
                onClick={navigateToNextContact}
                title={hasNextContact ? 'Go to next contact' : 'No next contact'}
              >
                Next Contact
                <span className="video-controls-below__arrow-right">
                  <ArrowBackIcon size={16} />
                </span>
              </button>
            </div>
            {hasPoseData && (
              <label className="video-controls-below__annotation-toggle">
                <input
                  type="checkbox"
                  checked={showOverlay}
                  onChange={(e) => setShowOverlay(e.target.checked)}
                  className="video-controls-below__toggle-input"
                />
                <span className="video-controls-below__toggle-slider"></span>
                <span className="video-controls-below__toggle-label">
                  Show Annotation
                </span>
              </label>
            )}
          </div>
        </div>
      )}

      {/* Ball Contact Management Modal */}
      <BallContactModal
        contact={selectedContact}
        isOpen={isModalOpen}
        videoDuration={duration}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedContact(null);
          setSelectedContactId(undefined);
        }}
        onUpdate={async (contactId, updates) => {
          await updateContact(contactId, updates);
        }}
        onDelete={async (contactId) => {
          await deleteContact(contactId);
        }}
      />
    </div>
  );
};

export default VideoPlayer;
