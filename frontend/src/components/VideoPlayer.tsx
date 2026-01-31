import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useServeAttempts } from '../hooks/useServeAttempts';
import { useServeProposals } from '../hooks/useServeProposals';
import { useVideoMetadata } from '../hooks/useVideos';
import { useVideoUrl } from '../hooks/useVideoUrl';
import { ServeAttempt, ServeAttemptCreate } from '../services/serveAttemptApi';
import AddServeAttemptButton from './AddServeAttemptButton';
import ProposalRange from './ProposalRange';
import ServeAttemptRange from './ServeAttemptRange';
import ServeAttemptModal from './ServeAttemptModal';
import {
  ArrowBackIcon,
  CloseIcon,
  FullscreenIcon,
  PauseIcon,
  PlayIcon,
  VolumeIcon,
  VolumeOffIcon,
  WarningIcon,
} from './Icons';
import VideoOverlay from './VideoOverlay';
import StickFigureCanvas from './StickFigureCanvas';
import './VideoPlayer.css';

interface VideoPlayerProps {
  videoUrl: string;
  title: string;
  onClose?: () => void;
  showControls?: boolean;
  aspectRatioMode?: 'cover' | 'contain' | 'auto';
  videoId?: number; // Video ID for fetching serve attempts
  hasPoseData?: boolean; // Whether pose detection data exists
  controlsBelow?: boolean; // Render controls below video instead of overlaying
  onContactNavigate?: (serveAttemptId: number) => void; // Callback when serve attempt is navigated to
  onNavigateReady?: (navigateFn: (serveAttemptId: number) => void) => void; // Callback to expose navigate function
  isDemo?: boolean; // If true, disable manual range tagging and editing
  naturalScroll?: boolean; // Scroll direction: false = traditional (scroll down = forward), true = natural (scroll down = backward)
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
  const [selectedServeAttempt, setSelectedServeAttempt] = useState<ServeAttempt | null>(
    null
  );
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedServeAttemptId, setSelectedServeAttemptId] = useState<
    number | undefined
  >();
  // View mode: 'video' = no overlay, 'skeleton' = video + overlay, 'stickfigure' = stick figure only
  type ViewMode = 'video' | 'skeleton' | 'stickfigure';
  const [viewMode, setViewMode] = useState<ViewMode>('video');
  
  // Show scroll hint on first hover
  const [showScrollHint, setShowScrollHint] = useState(false);
  const scrollHintShownRef = useRef(false);
  const naturalScrollRef = useRef(naturalScrollProp);
  const containerRef = useRef<HTMLDivElement>(null);
  const scrubberTrackRef = useRef<HTMLDivElement>(null);
  const [highlightTimestamp, setHighlightTimestamp] = useState<number | null>(null);
  const wasPlayingRef = useRef<boolean>(false);
  const toastTimeoutRef = useRef<number | null>(null);
  const [openRequestId, setOpenRequestId] = useState(0);
  const [openRange, setOpenRange] = useState<{ start: number; end: number } | null>(
    null
  );
  const [rangeInTime, setRangeInTime] = useState<number | null>(null);
  const [rangeOutTime, setRangeOutTime] = useState<number | null>(null);
  const isAddServeAttemptVisible = !!videoId && !error && duration > 0;
  const hasPoseDataForDetection = hasPoseData && !!videoId;
  const [detectionMessage, setDetectionMessage] = useState<string | null>(null);

  // Use serve attempts hook if videoId is provided
  const {
    serveAttempts,
    updateServeAttempt,
    deleteServeAttempt,
    createServeAttempt,
  } = useServeAttempts({
    videoId,
    filters: videoId ? { video_id: videoId } : undefined,
    autoRefresh: !!videoId,
  });

  // Use serve proposals hook if videoId is provided
  const {
    proposals,
    detectionStatus,
    runDetection,
    clearProposals,
    acceptProposal,
    rejectProposal,
    editProposal,
  } = useServeProposals({
    videoId,
    autoRefresh: !!videoId,
  });

  const [isRunningDetection, setIsRunningDetection] = useState(false);

  const showDetectionMessage = useCallback((message: string) => {
    setDetectionMessage(message);
    if (toastTimeoutRef.current) {
      window.clearTimeout(toastTimeoutRef.current);
    }
    toastTimeoutRef.current = window.setTimeout(() => {
      setDetectionMessage(null);
      toastTimeoutRef.current = null;
    }, 4000);
  }, []);

  // Determine auto-detect button state
  const hasExistingDetections = detectionStatus && (
    detectionStatus.pending_proposals > 0 ||
    detectionStatus.serve_attempts > 0
  );

  // Handle auto-detect
  const handleAutoDetect = useCallback(async () => {
    if (!videoId || isRunningDetection) return;

    // If there are existing proposals or serve attempts, ask for confirmation
    if (hasExistingDetections && detectionStatus) {
      const hasServeAttempts = detectionStatus.serve_attempts > 0;
      const hasPendingProposals = detectionStatus.pending_proposals > 0;

      let message = 'This video already has ';
      const parts: string[] = [];
      if (hasServeAttempts) {
        parts.push(`${detectionStatus.serve_attempts} serve attempt(s)`);
      }
      if (hasPendingProposals) {
        parts.push(`${detectionStatus.pending_proposals} pending proposal(s)`);
      }
      message += parts.join(' and ') + '. ';

      if (hasServeAttempts) {
        message += 'Running detection again will only add new proposals. Delete existing serve attempts first if you want to start fresh.';
        showDetectionMessage(message);
        return;
      }

      if (hasPendingProposals) {
        const confirmed = window.confirm(
          message + 'Do you want to clear existing proposals and re-run detection?'
        );
        if (!confirmed) return;
      }
    }

    setIsRunningDetection(true);
    setDetectionMessage(null);
    try {
      // Use force=true if there are pending proposals (we confirmed above)
      const force = detectionStatus?.pending_proposals ? detectionStatus.pending_proposals > 0 : false;
      const response = await runDetection(force);
      if (response.count === 0) {
        showDetectionMessage("No serve windows detected.");
      } else {
        showDetectionMessage(`Found ${response.count} proposals.`);
      }
    } catch (err) {
      console.error('Failed to run detection:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      if (errorMessage.includes('already has')) {
        showDetectionMessage(errorMessage);
      } else {
        showDetectionMessage(
          'Serve detection failed. Please ensure pose detection is completed.'
        );
      }
    } finally {
      setIsRunningDetection(false);
    }
  }, [videoId, isRunningDetection, runDetection, showDetectionMessage, hasExistingDetections, detectionStatus]);

  // Handle clearing proposals
  const handleClearProposals = useCallback(async () => {
    if (!videoId) return;

    const confirmed = window.confirm(
      'Are you sure you want to clear all pending proposals? This cannot be undone.'
    );
    if (!confirmed) return;

    try {
      const response = await clearProposals();
      showDetectionMessage(`Cleared ${response.cleared_count} proposal(s).`);
    } catch (err) {
      console.error('Failed to clear proposals:', err);
      showDetectionMessage('Failed to clear proposals.');
    }
  }, [videoId, clearProposals, showDetectionMessage]);

  useEffect(() => {
    return () => {
      if (toastTimeoutRef.current) {
        window.clearTimeout(toastTimeoutRef.current);
      }
    };
  }, []);

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
  }, [resolvedVideoUrl, videoId, videoUrl]);

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

  const seekToTime = useCallback((time: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = time;
    setCurrentTime(time);
  }, []);

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
    // For range tagging, we want it to stay paused for precision
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

  const markedRange = useMemo(() => {
    if (rangeInTime === null || rangeOutTime === null) return null;
    const start = Math.min(rangeInTime, rangeOutTime);
    const end = Math.max(rangeInTime, rangeOutTime);
    return { start, end };
  }, [rangeInTime, rangeOutTime]);

  const hasRangeMarks = rangeInTime !== null || rangeOutTime !== null;

  const clearRangeMarks = useCallback(() => {
    setRangeInTime(null);
    setRangeOutTime(null);
    setOpenRange(null);
  }, []);

  const createServeAttemptFromMarks = useCallback(() => {
    if (!markedRange) return;
    setOpenRange(markedRange);
    setOpenRequestId((prev) => prev + 1);
  }, [markedRange]);

  // Navigate to a specific serve attempt by ID (exposed via callback)
  const navigateToServeAttemptById = useCallback(
    (serveAttemptId: number) => {
      const serveAttempt = serveAttempts.find((sa) => sa.id === serveAttemptId);
      if (!serveAttempt) return;

      const video = videoRef.current;
      if (!video) return;

      // Pause if playing
      if (isPlaying) {
        video.pause();
      }

      // Navigate to start of serve attempt
      const targetTime = serveAttempt.start_timestamp;

      // Update state first to ensure overlay gets the new time immediately
      setCurrentTime(targetTime);
      setSelectedServeAttemptId(serveAttempt.id);
      
      // Then seek video (this will trigger seeked event which overlay listens to)
      video.currentTime = targetTime;
      
      onContactNavigate?.(serveAttempt.id);
    },
    [serveAttempts, isPlaying, onContactNavigate]
  );

  // Get sorted serve attempts for navigation (by start_timestamp)
  const sortedServeAttempts = useMemo(() => {
    return [...serveAttempts].sort((a, b) => {
      return a.start_timestamp - b.start_timestamp;
    });
  }, [serveAttempts]);

  // Navigate to previous/next serve attempt
  const navigateToPreviousServeAttempt = useCallback(() => {
    if (sortedServeAttempts.length === 0) return;

    const video = videoRef.current;
    const videoTime = video?.currentTime ?? currentTime;

    // Find the serve attempt before current time (with small tolerance)
    const tolerance = 0.1;
    const previousAttempts = sortedServeAttempts.filter((sa) => {
      return sa.start_timestamp < videoTime - tolerance;
    });

    if (previousAttempts.length > 0) {
      const previousAttempt = previousAttempts[previousAttempts.length - 1];
      navigateToServeAttemptById(previousAttempt.id);
    }
  }, [sortedServeAttempts, currentTime, navigateToServeAttemptById]);

  const navigateToNextServeAttempt = useCallback(() => {
    if (sortedServeAttempts.length === 0) return;

    const video = videoRef.current;
    const videoTime = video?.currentTime ?? currentTime;

    // Find the serve attempt after current time (with small tolerance)
    const tolerance = 0.1;
    const nextAttempt = sortedServeAttempts.find((sa) => {
      return sa.start_timestamp > videoTime + tolerance;
    });

    if (nextAttempt) {
      navigateToServeAttemptById(nextAttempt.id);
    }
  }, [sortedServeAttempts, currentTime, navigateToServeAttemptById]);

  // Check if previous/next navigation is available
  const hasPreviousServeAttempt = useMemo(() => {
    const tolerance = 0.1;
    return sortedServeAttempts.some((sa) => {
      return sa.start_timestamp < currentTime - tolerance;
    });
  }, [sortedServeAttempts, currentTime]);

  const hasNextServeAttempt = useMemo(() => {
    const tolerance = 0.1;
    return sortedServeAttempts.some((sa) => {
      return sa.start_timestamp > currentTime + tolerance;
    });
  }, [sortedServeAttempts, currentTime]);

  // Find the serve attempt that contains the current time
  const currentServeAttempt = useMemo(() => {
    return sortedServeAttempts.find((sa) => {
      return currentTime >= sa.start_timestamp && currentTime <= sa.end_timestamp;
    });
  }, [sortedServeAttempts, currentTime]);

  // Check if current serve attempt has a contact point
  const hasContactPoint = useMemo(() => {
    return currentServeAttempt?.contact_timestamp !== null && currentServeAttempt?.contact_timestamp !== undefined;
  }, [currentServeAttempt]);

  // Navigate to a specific timestamp (for moments within serve attempts)
  const navigateToTimestamp = useCallback((timestamp: number) => {
    const video = videoRef.current;
    if (!video) return;

    // Pause if playing
    if (isPlaying) {
      video.pause();
    }

    setCurrentTime(timestamp);
    video.currentTime = timestamp;
  }, [isPlaying]);

  // Navigate to contact point in current serve attempt
  const navigateToContact = useCallback(() => {
    if (!currentServeAttempt || !currentServeAttempt.contact_timestamp) return;
    navigateToTimestamp(currentServeAttempt.contact_timestamp);
  }, [currentServeAttempt, navigateToTimestamp]);

  const navigateRef = useRef(navigateToServeAttemptById);

  useEffect(() => {
    navigateRef.current = navigateToServeAttemptById;
  }, [navigateToServeAttemptById]);

  const stableNavigateToServeAttemptById = useCallback((serveAttemptId: number) => {
    navigateRef.current(serveAttemptId);
  }, []);

  // Expose navigate function to parent
  useEffect(() => {
    if (onNavigateReady) {
      onNavigateReady(stableNavigateToServeAttemptById);
    }
  }, [onNavigateReady, stableNavigateToServeAttemptById]);

  // Keyboard shortcuts for frame navigation, play/pause, and serve attempt navigation
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
          navigateToPreviousServeAttempt();
          break;
        case ']':
          event.preventDefault();
          navigateToNextServeAttempt();
          break;
        case 's':
        case 'S':
          event.preventDefault();
          if (isDemo) {
            alert('Range tagging is disabled in Demo Mode!');
            break;
          }
          setRangeInTime(videoRef.current?.currentTime ?? currentTime);
          break;
        case 'e':
        case 'E':
          event.preventDefault();
          if (isDemo) {
            alert('Range tagging is disabled in Demo Mode!');
            break;
          }
          setRangeOutTime(videoRef.current?.currentTime ?? currentTime);
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
    navigateToPreviousServeAttempt,
    navigateToNextServeAttempt,
    isDemo,
    currentTime,
  ]);

  useEffect(() => {
    naturalScrollRef.current = naturalScrollProp;
  }, [naturalScrollProp]);

  // Mouse wheel for frame-by-frame navigation
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (event: WheelEvent) => {
      // Only handle if we have video metadata (FPS)
      if (!videoMetadata?.fps) return;

      // Prevent default scroll behavior
      event.preventDefault();

      // Determine direction based on naturalScroll setting
      // Traditional: scroll down (deltaY > 0) = forward/next frame
      // Natural: scroll down (deltaY > 0) = backward/previous frame
      const scrollingDown = event.deltaY > 0;
      const goForward = naturalScrollRef.current ? !scrollingDown : scrollingDown;

      if (goForward) {
        navigateToNextFrame();
      } else {
        navigateToPreviousFrame();
      }
    };

    // Show scroll hint on first mouse enter
    const handleMouseEnter = () => {
      if (!scrollHintShownRef.current && videoMetadata?.fps) {
        setShowScrollHint(true);
        scrollHintShownRef.current = true;
        // Auto-hide after 3 seconds
        setTimeout(() => setShowScrollHint(false), 3000);
      }
    };

    // Use passive: false to allow preventDefault
    container.addEventListener('wheel', handleWheel, { passive: false });
    container.addEventListener('mouseenter', handleMouseEnter);

    return () => {
      container.removeEventListener('wheel', handleWheel);
      container.removeEventListener('mouseenter', handleMouseEnter);
    };
  }, [videoMetadata?.fps, navigateToNextFrame, navigateToPreviousFrame]);

  // Memoize formatted time strings to prevent unnecessary re-renders
  const formattedCurrentTime = useMemo(
    () => formatTime(currentTime),
    [currentTime, formatTime]
  );
  const formattedDuration = useMemo(
    () => formatTime(duration),
    [duration, formatTime]
  );
  const rangeInLabel = rangeInTime !== null ? formatTime(rangeInTime) : '—';
  const rangeOutLabel = rangeOutTime !== null ? formatTime(rangeOutTime) : '—';

  const handleVideoClick = () => {
    // When controlsBelow is true, clicking video toggles play/pause
    if (controlsBelow) {
      togglePlay();
    }
  };


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
      {detectionMessage && (
        <div className="auto-detect-toast" role="status">
          {detectionMessage}
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
        {/* Controls row (kept minimal) - only show when controlsBelow is false */}
        {hasPoseData && !controlsBelow && (
          <div className="overlay-toggle-container">
            <div className="view-mode-selector">
              <label className="view-mode-label">View:</label>
              <select
                value={viewMode}
                onChange={(e) => setViewMode(e.target.value as ViewMode)}
                className="view-mode-select"
              >
                <option value="video">Video Only</option>
                <option value="skeleton">Video + Skeleton</option>
                <option value="stickfigure">Stick Figure</option>
              </select>
            </div>
            {hasPoseDataForDetection && (
              <div className="auto-detect-wrap">
                <button
                  className={`auto-detect-btn ${hasExistingDetections ? 'auto-detect-btn--has-detections' : ''}`}
                  onClick={handleAutoDetect}
                  disabled={isRunningDetection}
                  title={hasExistingDetections
                    ? 'Detection already run - click to re-detect'
                    : 'Auto-detect serve windows'
                  }
                >
                  {isRunningDetection ? 'Detecting...' : 'Auto-detect serves'}
                </button>
                {proposals.length > 0 && (
                  <button
                    className="auto-detect-clear-btn"
                    onClick={handleClearProposals}
                    disabled={isRunningDetection}
                    title="Clear all pending proposals"
                  >
                    Clear
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        <div
          className="video-player-main"
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
                className={`video-element video-element-${aspectRatioMode} ${
                  viewMode === 'stickfigure' && hasPoseData ? 'video-element--hidden' : ''
                }`}
                preload="metadata"
                crossOrigin="anonymous"
                data-testid="video-element"
              />
            )}

            {/* Stick Figure Mode - shown when viewMode is 'stickfigure' */}
            {videoId && viewMode === 'stickfigure' && hasPoseData && (
              <StickFigureCanvas
                videoId={videoId}
                currentTime={currentTime}
                fps={videoMetadata?.fps}
                isPlaying={isPlaying}
              />
            )}

            {/* Video Overlay - shown when viewMode is 'skeleton' */}
            {videoId && viewMode === 'skeleton' && hasPoseData && (
              <VideoOverlay
                videoId={videoId}
                videoElement={videoRef.current}
                showOverlay={true}
                hasPoseData={hasPoseData}
                currentTime={currentTime}
              />
            )}

            {/* Scroll hint */}
            {showScrollHint && (
              <div className="scroll-hint">
                <span className="scroll-hint__icon">⟳</span>
                <span>Use scroll wheel to navigate frames</span>
              </div>
            )}

            {/* Loading overlay while resolving URL */}
            {isLoadingUrl && (
              <div className="loading-overlay">
                <div className="loading-spinner" />
                <p>Loading video...</p>
              </div>
            )}

            {/* Add Serve Attempt Button (overlay placement) */}
            {!controlsBelow && (
              <AddServeAttemptButton
                currentTime={currentTime}
                videoId={videoId || 0}
                videoDuration={duration}
                fps={videoMetadata?.fps}
                onAddServeAttempt={async (serveAttempt: ServeAttemptCreate) => {
                  await createServeAttempt(serveAttempt);
                  if (openRange) {
                    clearRangeMarks();
                  }
                }}
                isVisible={isAddServeAttemptVisible}
                isReadOnly={isDemo}
                placement="overlay"
                onSeek={seekToTime}
                openRequestId={openRequestId}
                openRange={openRange ?? undefined}
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
                  setOpenRange(null);
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
              {/* Proposal ranges (shown before serve attempts) */}
              {proposals.length > 0 && duration > 0 && (
                <div className="proposal-ranges">
                  {proposals.map((proposal) => (
                    <ProposalRange
                      key={proposal.id}
                      proposal={proposal}
                      duration={duration}
                      onClick={() => {
                        // Seek to proposal start
                        seekToTime(proposal.start_timestamp);
                      }}
                      onAccept={async () => {
                        try {
                          await acceptProposal(proposal.id);
                        } catch (err) {
                          console.error('Failed to accept proposal:', err);
                          alert('Failed to accept proposal');
                        }
                      }}
                      onReject={async () => {
                        try {
                          await rejectProposal(proposal.id);
                        } catch (err) {
                          console.error('Failed to reject proposal:', err);
                          alert('Failed to reject proposal');
                        }
                      }}
                      onEdit={async () => {
                        // For now, just accept with current timestamps
                        // In future, could open a modal to edit timestamps
                        try {
                          await editProposal(proposal.id, {
                            start_timestamp: proposal.start_timestamp,
                            end_timestamp: proposal.end_timestamp,
                          });
                        } catch (err) {
                          console.error('Failed to edit proposal:', err);
                          alert('Failed to edit proposal');
                        }
                      }}
                    />
                  ))}
                </div>
              )}
              {/* Serve attempt ranges */}
              {serveAttempts.length > 0 && duration > 0 && (
                <div className="serve-attempt-ranges" data-tour="serve-attempt-ranges">
                  {serveAttempts.map((serveAttempt) => {
                    const isSelected = selectedServeAttemptId === serveAttempt.id;

                    return (
                      <ServeAttemptRange
                        key={serveAttempt.id}
                        serveAttempt={serveAttempt}
                        duration={duration}
                        currentTime={currentTime}
                        isSelected={isSelected}
                        isDemo={isDemo}
                        onClick={() => {
                          setSelectedServeAttempt(serveAttempt);
                          setSelectedServeAttemptId(serveAttempt.id);
                          setIsModalOpen(true);
                        }}
                        onContactClick={() => {
                          if (serveAttempt.contact_timestamp) {
                            seekToTime(serveAttempt.contact_timestamp);
                          }
                        }}
                        onMarkContact={async (timestamp) => {
                          try {
                            await updateServeAttempt(serveAttempt.id, {
                              contact_timestamp: timestamp,
                            });
                          } catch (err) {
                            console.error('Failed to mark contact:', err);
                          }
                        }}
                      />
                    );
                  })}
                </div>
              )}
                    {rangeInTime !== null && duration > 0 && (
                      <div
                        className="range-mark-marker range-mark-marker--start"
                        style={{
                          left: `${(rangeInTime / duration) * 100}%`,
                        }}
                      >
                        <span>START</span>
                      </div>
                    )}
                    {rangeOutTime !== null && duration > 0 && (
                      <div
                        className="range-mark-marker range-mark-marker--end"
                        style={{
                          left: `${(rangeOutTime / duration) * 100}%`,
                        }}
                      >
                        <span>END</span>
                      </div>
                    )}
                    {/* Highlight marker for locked range anchor */}
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
                  {hasRangeMarks && (
                    <div className="range-marked-row">
                      <div className="range-marked-info">
                        <span>START {rangeInLabel}</span>
                        <span>END {rangeOutLabel}</span>
                      </div>
                      <div className="range-marked-actions">
                        <button
                          className="range-marked-btn"
                          onClick={createServeAttemptFromMarks}
                          disabled={!markedRange || isDemo}
                          title={
                            isDemo
                              ? 'Demo mode: range tagging is disabled'
                              : 'Create serve attempt from marked range'
                          }
                        >
                          Create serve attempt
                        </button>
                        <button
                          className="range-marked-btn range-marked-btn--ghost"
                          onClick={clearRangeMarks}
                        >
                          Clear
                        </button>
                      </div>
                    </div>
                  )}
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

          {/* Posture Analysis Sidebar - Removed: serve attempts already have metrics via serve analysis */}
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
              <AddServeAttemptButton
                currentTime={currentTime}
                videoId={videoId || 0}
                videoDuration={duration}
                fps={videoMetadata?.fps}
                onAddServeAttempt={async (serveAttempt: ServeAttemptCreate) => {
                  await createServeAttempt(serveAttempt);
                  if (openRange) {
                    clearRangeMarks();
                  }
                }}
                isVisible={isAddServeAttemptVisible}
                isReadOnly={isDemo}
                placement="scrubber"
                onSeek={seekToTime}
                openRequestId={openRequestId}
                openRange={openRange ?? undefined}
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
                  setOpenRange(null);
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
              {/* Proposal ranges (shown before serve attempts) */}
              {proposals.length > 0 && duration > 0 && (
                <div className="video-controls-below__proposal-ranges">
                  {proposals.map((proposal) => (
                    <ProposalRange
                      key={proposal.id}
                      proposal={proposal}
                      duration={duration}
                      onClick={() => {
                        seekToTime(proposal.start_timestamp);
                      }}
                      onAccept={async () => {
                        try {
                          await acceptProposal(proposal.id);
                        } catch (err) {
                          console.error('Failed to accept proposal:', err);
                          alert('Failed to accept proposal');
                        }
                      }}
                      onReject={async () => {
                        try {
                          await rejectProposal(proposal.id);
                        } catch (err) {
                          console.error('Failed to reject proposal:', err);
                          alert('Failed to reject proposal');
                        }
                      }}
                      onEdit={async () => {
                        try {
                          await editProposal(proposal.id, {
                            start_timestamp: proposal.start_timestamp,
                            end_timestamp: proposal.end_timestamp,
                          });
                        } catch (err) {
                          console.error('Failed to edit proposal:', err);
                          alert('Failed to edit proposal');
                        }
                      }}
                    />
                  ))}
                </div>
              )}
              {/* Serve attempt ranges */}
              {serveAttempts.length > 0 && duration > 0 && (
                <div
                  className="video-controls-below__serve-attempt-ranges"
                  data-tour="serve-attempt-ranges"
                >
                  {serveAttempts.map((serveAttempt) => {
                    const isSelected = selectedServeAttemptId === serveAttempt.id;

                    return (
                      <ServeAttemptRange
                        key={serveAttempt.id}
                        serveAttempt={serveAttempt}
                        duration={duration}
                        currentTime={currentTime}
                        isSelected={isSelected}
                        isDemo={isDemo}
                        onClick={() => {
                          setSelectedServeAttempt(serveAttempt);
                          setSelectedServeAttemptId(serveAttempt.id);
                          setIsModalOpen(true);
                        }}
                        onContactClick={() => {
                          if (serveAttempt.contact_timestamp) {
                            seekToTime(serveAttempt.contact_timestamp);
                          }
                        }}
                        onMarkContact={async (timestamp) => {
                          try {
                            await updateServeAttempt(serveAttempt.id, {
                              contact_timestamp: timestamp,
                            });
                          } catch (err) {
                            console.error('Failed to mark contact:', err);
                          }
                        }}
                      />
                    );
                  })}
                </div>
              )}
              {rangeInTime !== null && duration > 0 && (
                <div
                  className="range-mark-marker range-mark-marker--start"
                  style={{
                    left: `${(rangeInTime / duration) * 100}%`,
                  }}
                >
                  <span>START</span>
                </div>
              )}
              {rangeOutTime !== null && duration > 0 && (
                <div
                  className="range-mark-marker range-mark-marker--end"
                  style={{
                    left: `${(rangeOutTime / duration) * 100}%`,
                  }}
                >
                  <span>END</span>
                </div>
              )}
              {/* Highlight marker for locked range anchor */}
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
            {hasRangeMarks && (
              <div className="range-marked-row range-marked-row--below">
                <div className="range-marked-info">
                  <span>START {rangeInLabel}</span>
                  <span>END {rangeOutLabel}</span>
                </div>
                <div className="range-marked-actions">
                  <button
                    className="range-marked-btn"
                    onClick={createServeAttemptFromMarks}
                    disabled={!markedRange || isDemo}
                    title={
                      isDemo
                        ? 'Demo mode: range tagging is disabled'
                        : 'Create serve attempt from marked range'
                    }
                  >
                    Create serve attempt
                  </button>
                  <button
                    className="range-marked-btn range-marked-btn--ghost"
                    onClick={clearRangeMarks}
                  >
                    Clear
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Navigation Controls */}
          <div className="video-controls-below__nav">
            <button
              className="video-controls-below__nav-btn"
              disabled={!hasPreviousServeAttempt}
              onClick={navigateToPreviousServeAttempt}
              title={hasPreviousServeAttempt ? 'Go to previous serve' : 'No previous serve'}
            >
              <ArrowBackIcon size={18} />
              <span>Previous Serve</span>
            </button>
            <button
              className="video-controls-below__play-btn"
              onClick={togglePlay}
              title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
            >
              {isPlaying ? <PauseIcon size={24} /> : <PlayIcon size={24} />}
            </button>
            <button
              className="video-controls-below__nav-btn video-controls-below__nav-btn--next"
              disabled={!hasNextServeAttempt}
              onClick={navigateToNextServeAttempt}
              title={hasNextServeAttempt ? 'Go to next serve' : 'No next serve'}
            >
              <span>Next Serve</span>
              <ArrowBackIcon size={18} />
            </button>
            {hasContactPoint && (
              <button
                className="video-controls-below__contact-btn"
                onClick={navigateToContact}
                title="Jump to the ball contact moment"
              >
                <span className="video-controls-below__contact-icon">◉</span>
                <span>Go to Contact</span>
              </button>
            )}
            {/* View mode selector - subtle placement */}
            {hasPoseData && (
              <div className="video-controls-below__view-mode">
                <select
                  value={viewMode}
                  onChange={(e) => setViewMode(e.target.value as ViewMode)}
                  className="video-controls-below__view-select"
                  title="Change video overlay"
                >
                  <option value="video">Video Only</option>
                  <option value="skeleton">+ Skeleton</option>
                  <option value="stickfigure">Stick Figure</option>
                </select>
              </div>
            )}
          </div>

          {/* Serve Detail Panel (inline, non-blocking) */}
          {isModalOpen && selectedServeAttempt && (
            <div className="video-controls-below__serve-panel">
              <ServeAttemptModal
                serveAttempt={selectedServeAttempt}
                isOpen={isModalOpen}
                videoDuration={duration}
                currentTime={currentTime}
                isDemo={isDemo}
                mode="panel"
                onClose={() => {
                  setIsModalOpen(false);
                  setSelectedServeAttempt(null);
                  setSelectedServeAttemptId(undefined);
                }}
                onUpdate={async (serveAttemptId, updates) => {
                  await updateServeAttempt(serveAttemptId, updates);
                }}
                onDelete={async (serveAttemptId) => {
                  await deleteServeAttempt(serveAttemptId);
                }}
                onSeek={seekToTime}
              />
            </div>
          )}
        </div>
      )}

      {/* Serve Attempt Management Modal (overlay mode for non-controlsBelow) */}
      {!controlsBelow && (
        <ServeAttemptModal
          serveAttempt={selectedServeAttempt}
          isOpen={isModalOpen}
          videoDuration={duration}
          currentTime={currentTime}
          isDemo={isDemo}
          mode="overlay"
          onClose={() => {
            setIsModalOpen(false);
            setSelectedServeAttempt(null);
            setSelectedServeAttemptId(undefined);
          }}
          onUpdate={async (serveAttemptId, updates) => {
            await updateServeAttempt(serveAttemptId, updates);
          }}
          onDelete={async (serveAttemptId) => {
            await deleteServeAttempt(serveAttemptId);
          }}
          onSeek={seekToTime}
        />
      )}
    </div>
  );
};

export default VideoPlayer;
