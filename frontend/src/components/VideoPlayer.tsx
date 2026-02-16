import { useQueryClient } from '@tanstack/react-query';
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  contactTimestampsQueryKey,
  useContactTimestamps,
} from '../hooks/useContactTimestamps';
import { useServeWindows } from '../hooks/useServeWindows';
import { useServeProposals } from '../hooks/useServeProposals';
import { useVideoMetadata } from '../hooks/useVideos';
import { useVideoUrl } from '../hooks/useVideoUrl';
import { ServeWindow, ServeWindowCreate } from '../services/serveWindowApi';
import AddServeWindowButton from './AddServeWindowButton';
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
import LoadingIndicator from './LoadingIndicator';
import ProposalRange from './ProposalRange';
import ServeWindowModal from './ServeWindowModal';
import ServeWindowRange from './ServeWindowRange';
import StickFigureCanvas from './StickFigureCanvas';
import VideoOverlay from './VideoOverlay';
import './VideoPlayer.css';

// Manual zoom levels available
const ZOOM_LEVELS = [1, 1.25, 1.5, 2, 2.5, 3];

interface VideoPlayerProps {
  videoUrl: string;
  title: string;
  onClose?: () => void;
  showControls?: boolean;
  aspectRatioMode?: 'cover' | 'contain' | 'auto';
  videoId?: number; // Video ID for fetching serve windows
  hasPoseData?: boolean; // Whether pose detection data exists
  controlsBelow?: boolean; // Render controls below video instead of overlaying
  onContactNavigate?: (serveWindowId: number) => void; // Callback when serve window is navigated to
  onNavigateReady?: (navigateFn: (serveWindowId: number) => void) => void; // Callback to expose navigate function
  isDemo?: boolean; // If true, disable manual range tagging and editing
  naturalScroll?: boolean; // Scroll direction: false = traditional (scroll down = forward), true = natural (scroll down = backward)
  lowConfidenceThreshold?: number; // Threshold for coloring proposals as "uncertain"
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
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [videoAspectRatio, setVideoAspectRatio] = useState<number | null>(null);
  const [isScrubbing, setIsScrubbing] = useState(false);
  const [selectedServeWindow, setSelectedServeWindow] =
    useState<ServeWindow | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedServeWindowId, setSelectedServeWindowId] = useState<
    number | undefined
  >();
  // View mode: 'video' = no overlay, 'skeleton' = video + overlay, 'stickfigure' = stick figure only
  type ViewMode = 'video' | 'skeleton' | 'stickfigure';
  const [viewMode, setViewMode] = useState<ViewMode>('video');

  // Manual zoom level
  const [zoomLevel, setZoomLevel] = useState(1);

  // Show scroll hint on first hover
  const [showScrollHint, setShowScrollHint] = useState(false);
  const scrollHintShownRef = useRef(false);
  const naturalScrollRef = useRef(naturalScrollProp);
  const containerRef = useRef<HTMLDivElement>(null);
  const scrubberTrackRef = useRef<HTMLDivElement>(null);
  const [highlightTimestamp, setHighlightTimestamp] = useState<number | null>(
    null
  );
  const wasPlayingRef = useRef<boolean>(false);
  const toastTimeoutRef = useRef<number | null>(null);
  const [openRequestId, setOpenRequestId] = useState(0);
  const [openRange, setOpenRange] = useState<{
    start: number;
    end: number;
  } | null>(null);
  const [rangeInTime, setRangeInTime] = useState<number | null>(null);
  const [rangeOutTime, setRangeOutTime] = useState<number | null>(null);
  const isAddServeWindowVisible = !!videoId && !error && duration > 0;
  const hasPoseDataForDetection = hasPoseData && !!videoId;
  const [detectionMessage, setDetectionMessage] = useState<string | null>(null);

  const queryClient = useQueryClient();

  // Use serve windows hook if videoId is provided
  const {
    serveWindows,
    updateServeWindow,
    deleteServeWindow,
    createServeWindow,
  } = useServeWindows({
    videoId,
    filters: videoId ? { video_id: videoId } : undefined,
    autoRefresh: !!videoId,
  });

  // Contact timestamps from backend (for prev/next contact navigation)
  const { contactTimestamps } = useContactTimestamps(videoId);

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
  const hasExistingDetections =
    detectionStatus &&
    (detectionStatus.pending_proposals > 0 ||
      detectionStatus.serve_windows > 0);

  // Handle auto-detect
  const handleAutoDetect = useCallback(async () => {
    if (!videoId || isRunningDetection) return;

    // If there are existing proposals or serve windows, ask for confirmation
    if (hasExistingDetections && detectionStatus) {
      const hasServeWindows = detectionStatus.serve_windows > 0;
      const hasPendingProposals = detectionStatus.pending_proposals > 0;

      let message = 'This video already has ';
      const parts: string[] = [];
      if (hasServeWindows) {
        parts.push(`${detectionStatus.serve_windows} serve window(s)`);
      }
      if (hasPendingProposals) {
        parts.push(`${detectionStatus.pending_proposals} pending proposal(s)`);
      }
      message += parts.join(' and ') + '. ';

      if (hasServeWindows) {
        message +=
          'Running detection again will only add new proposals. Delete existing serve windows first if you want to start fresh.';
        showDetectionMessage(message);
        return;
      }

      if (hasPendingProposals) {
        const confirmed = window.confirm(
          message +
            'Do you want to clear existing proposals and re-run detection?'
        );
        if (!confirmed) return;
      }
    }

    setIsRunningDetection(true);
    setDetectionMessage(null);
    try {
      // Use force=true if there are pending proposals (we confirmed above)
      const force = detectionStatus?.pending_proposals
        ? detectionStatus.pending_proposals > 0
        : false;
      const response = await runDetection(force);
      if (response.count === 0) {
        showDetectionMessage('No serve windows detected.');
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
  }, [
    videoId,
    isRunningDetection,
    runDetection,
    showDetectionMessage,
    hasExistingDetections,
    detectionStatus,
  ]);

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
  const { resolvedUrl: resolvedVideoUrl, isLoading: isLoadingUrl } =
    useVideoUrl({
      videoId,
      videoUrl,
      expiresIn: 3600,
    });

  // Use React Query hook for video metadata
  const { data: videoMetadata } = useVideoMetadata(videoId);

  // Zoom helper functions
  const zoomIn = useCallback(() => {
    setZoomLevel((prev) => {
      const currentIndex = ZOOM_LEVELS.indexOf(prev);
      if (currentIndex < ZOOM_LEVELS.length - 1) {
        return ZOOM_LEVELS[currentIndex + 1];
      }
      return prev;
    });
  }, []);

  const zoomOut = useCallback(() => {
    setZoomLevel((prev) => {
      const currentIndex = ZOOM_LEVELS.indexOf(prev);
      if (currentIndex > 0) {
        return ZOOM_LEVELS[currentIndex - 1];
      }
      return prev;
    });
  }, []);

  const resetZoom = useCallback(() => {
    setZoomLevel(1);
  }, []);

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
      // Use padding-bottom technique for aspect ratio
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

  const createServeWindowFromMarks = useCallback(() => {
    if (!markedRange) return;
    setOpenRange(markedRange);
    setOpenRequestId((prev) => prev + 1);
  }, [markedRange]);

  // Navigate to a specific serve window by ID (exposed via callback)
  const navigateToServeWindowById = useCallback(
    (serveWindowId: number) => {
      const serveWindow = serveWindows.find((sa) => sa.id === serveWindowId);
      if (!serveWindow) return;

      const video = videoRef.current;
      if (!video) return;

      // Pause if playing
      if (isPlaying) {
        video.pause();
      }

      // Navigate to start of serve window
      const targetTime = serveWindow.start_timestamp;

      // Update state first to ensure overlay gets the new time immediately
      setCurrentTime(targetTime);
      setSelectedServeWindowId(serveWindow.id);

      // Then seek video (this will trigger seeked event which overlay listens to)
      video.currentTime = targetTime;

      onContactNavigate?.(serveWindow.id);
    },
    [serveWindows, isPlaying, onContactNavigate]
  );

  // Get sorted serve windows for navigation (by start_timestamp)
  const sortedServeWindows = useMemo(() => {
    return [...serveWindows].sort((a, b) => {
      return a.start_timestamp - b.start_timestamp;
    });
  }, [serveWindows]);

  // Navigate to previous/next serve window
  const navigateToPreviousServeWindow = useCallback(() => {
    if (sortedServeWindows.length === 0) return;

    const video = videoRef.current;
    const videoTime = video?.currentTime ?? currentTime;

    // Find the serve window before current time (with small tolerance)
    const tolerance = 0.1;
    const previousAttempts = sortedServeWindows.filter((sa) => {
      return sa.start_timestamp < videoTime - tolerance;
    });

    if (previousAttempts.length > 0) {
      const previousAttempt = previousAttempts[previousAttempts.length - 1];
      navigateToServeWindowById(previousAttempt.id);
    }
  }, [sortedServeWindows, currentTime, navigateToServeWindowById]);

  const navigateToNextServeWindow = useCallback(() => {
    if (sortedServeWindows.length === 0) return;

    const video = videoRef.current;
    const videoTime = video?.currentTime ?? currentTime;

    // Find the serve window after current time (with small tolerance)
    const tolerance = 0.1;
    const nextAttempt = sortedServeWindows.find((sa) => {
      return sa.start_timestamp > videoTime + tolerance;
    });

    if (nextAttempt) {
      navigateToServeWindowById(nextAttempt.id);
    }
  }, [sortedServeWindows, currentTime, navigateToServeWindowById]);

  // Check if previous/next navigation is available
  const hasPreviousServeWindow = useMemo(() => {
    const tolerance = 0.1;
    return sortedServeWindows.some((sa) => {
      return sa.start_timestamp < currentTime - tolerance;
    });
  }, [sortedServeWindows, currentTime]);

  const hasNextServeWindow = useMemo(() => {
    const tolerance = 0.1;
    return sortedServeWindows.some((sa) => {
      return sa.start_timestamp > currentTime + tolerance;
    });
  }, [sortedServeWindows, currentTime]);

  const hasAnyContact = contactTimestamps.length > 0;

  // Previous/next contact relative to current time
  // Use tolerance to handle video frame alignment issues - when navigating to a contact
  // timestamp, the video element may round to the nearest frame, causing the actual
  // currentTime to differ slightly from the target timestamp
  const CONTACT_TOLERANCE = 0.1; // 100ms tolerance for frame alignment

  const previousContactTimestamp = useMemo(() => {
    const prev = contactTimestamps.filter(
      (t) => t < currentTime - CONTACT_TOLERANCE
    );
    return prev.length > 0 ? prev[prev.length - 1] : undefined;
  }, [contactTimestamps, currentTime]);

  const nextContactTimestamp = useMemo(() => {
    return contactTimestamps.find((t) => t > currentTime + CONTACT_TOLERANCE);
  }, [contactTimestamps, currentTime]);

  const hasPreviousContact = previousContactTimestamp !== undefined;
  const hasNextContact = nextContactTimestamp !== undefined;

  // Navigate to a specific timestamp (for moments within serve windows)
  const navigateToTimestamp = useCallback(
    (timestamp: number) => {
      const video = videoRef.current;
      if (!video) return;

      // Pause if playing
      if (isPlaying) {
        video.pause();
      }

      setCurrentTime(timestamp);
      video.currentTime = timestamp;
    },
    [isPlaying]
  );

  const navigateToPreviousContact = useCallback(() => {
    if (previousContactTimestamp === undefined) return;
    navigateToTimestamp(previousContactTimestamp);
  }, [previousContactTimestamp, navigateToTimestamp]);

  const navigateToNextContact = useCallback(() => {
    if (nextContactTimestamp === undefined) return;
    navigateToTimestamp(nextContactTimestamp);
  }, [nextContactTimestamp, navigateToTimestamp]);

  const navigateRef = useRef(navigateToServeWindowById);

  useEffect(() => {
    navigateRef.current = navigateToServeWindowById;
  }, [navigateToServeWindowById]);

  const stableNavigateToServeWindowById = useCallback(
    (serveWindowId: number) => {
      navigateRef.current(serveWindowId);
    },
    []
  );

  // Expose navigate function to parent
  useEffect(() => {
    if (onNavigateReady) {
      onNavigateReady(stableNavigateToServeWindowById);
    }
  }, [onNavigateReady, stableNavigateToServeWindowById]);

  // Keyboard shortcuts for frame navigation, play/pause, and serve window navigation
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
          navigateToPreviousServeWindow();
          break;
        case ']':
          event.preventDefault();
          navigateToNextServeWindow();
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
        case '+':
        case '=':
          event.preventDefault();
          zoomIn();
          break;
        case '-':
        case '_':
          event.preventDefault();
          zoomOut();
          break;
        case '0':
          event.preventDefault();
          resetZoom();
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
    navigateToPreviousServeWindow,
    navigateToNextServeWindow,
    isDemo,
    currentTime,
    zoomIn,
    zoomOut,
    resetZoom,
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
      const goForward = naturalScrollRef.current
        ? !scrollingDown
        : scrollingDown;

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
        {/* View mode bar – top of video player (when pose data exists) */}
        {hasPoseData && (
          <div className="video-player-view-bar">
            <span className="video-player-view-bar__label">View</span>
            <div
              className="video-player-view-bar__segmented"
              role="radiogroup"
              aria-label="Overlay mode"
            >
              {(
                [
                  { value: 'video' as ViewMode, label: 'Video' },
                  { value: 'skeleton' as ViewMode, label: 'Skeleton' },
                  { value: 'stickfigure' as ViewMode, label: 'Stick' },
                ] as const
              ).map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={viewMode === value}
                  title={
                    value === 'video'
                      ? 'Video only'
                      : value === 'skeleton'
                        ? 'Video with skeleton overlay'
                        : 'Video with stick figure'
                  }
                  className={`video-player-view-bar__option ${viewMode === value ? 'video-player-view-bar__option--active' : ''}`}
                  onClick={() => setViewMode(value)}
                >
                  {label}
                </button>
              ))}
            </div>
            {/* Manual Zoom Controls */}
            <div className="video-player-zoom-controls">
              <button
                type="button"
                className="video-player-zoom-btn"
                onClick={zoomOut}
                disabled={zoomLevel === ZOOM_LEVELS[0]}
                title="Zoom out"
              >
                −
              </button>
              <button
                type="button"
                className="video-player-zoom-level"
                onClick={resetZoom}
                title="Reset zoom"
              >
                {Math.round(zoomLevel * 100)}%
              </button>
              <button
                type="button"
                className="video-player-zoom-btn"
                onClick={zoomIn}
                disabled={zoomLevel === ZOOM_LEVELS[ZOOM_LEVELS.length - 1]}
                title="Zoom in"
              >
                +
              </button>
            </div>
          </div>
        )}

        {/* Auto-detect row (only when controls overlay, not controls-below) */}
        {hasPoseData && !controlsBelow && hasPoseDataForDetection && (
          <div className="overlay-toggle-container">
            <div className="auto-detect-wrap">
              <button
                className={`auto-detect-btn ${hasExistingDetections ? 'auto-detect-btn--has-detections' : ''}`}
                onClick={handleAutoDetect}
                disabled={isRunningDetection}
                title={
                  hasExistingDetections
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
          </div>
        )}

        <div className="video-player-main">
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
              <div
                className="video-zoom-wrapper"
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  overflow: 'hidden',
                  transform: zoomLevel !== 1 ? `scale(${zoomLevel})` : 'none',
                  transformOrigin: 'center center',
                  transition: 'transform 0.2s ease-out',
                }}
              >
                <video
                  ref={videoRef}
                  src={resolvedVideoUrl}
                  className={`video-element video-element-${aspectRatioMode} ${
                    viewMode === 'stickfigure' && hasPoseData
                      ? 'video-element--hidden'
                      : ''
                  }`}
                  preload="metadata"
                  crossOrigin="anonymous"
                  data-testid="video-element"
                />
              </div>
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
                zoomLevel={zoomLevel}
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
                <LoadingIndicator
                  size="lg"
                  tone="light"
                  label="Loading Video..."
                />
              </div>
            )}

            {/* Add Serve Attempt Button (overlay placement) */}
            {!controlsBelow && (
              <AddServeWindowButton
                currentTime={currentTime}
                videoId={videoId || 0}
                videoDuration={duration}
                fps={videoMetadata?.fps}
                onAddServeWindow={async (serveWindow: ServeWindowCreate) => {
                  await createServeWindow(serveWindow);
                  if (videoId) {
                    queryClient.invalidateQueries({
                      queryKey: contactTimestampsQueryKey(videoId),
                    });
                  }
                  if (openRange) {
                    clearRangeMarks();
                  }
                }}
                isVisible={isAddServeWindowVisible}
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
                    {/* Proposal ranges (shown before serve windows) */}
                    {proposals.length > 0 && duration > 0 && (
                      <div className="proposal-ranges">
                        {proposals.map((proposal) => (
                          <ProposalRange
                            key={proposal.id}
                            proposal={proposal}
                            duration={duration}
                            lowConfidenceThreshold={lowConfidenceThreshold}
                            onClick={() => {
                              // Seek to proposal start
                              seekToTime(proposal.start_timestamp);
                            }}
                            onAccept={async () => {
                              try {
                                await acceptProposal(proposal.id);
                              } catch (err) {
                                console.error(
                                  'Failed to accept proposal:',
                                  err
                                );
                                alert('Failed to accept proposal');
                              }
                            }}
                            onReject={async () => {
                              try {
                                await rejectProposal(proposal.id);
                              } catch (err) {
                                console.error(
                                  'Failed to reject proposal:',
                                  err
                                );
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
                    {/* Serve window ranges */}
                    {serveWindows.length > 0 && duration > 0 && (
                      <div
                        className="serve-window-ranges"
                        data-tour="serve-window-ranges"
                      >
                        {serveWindows.map((serveWindow) => {
                          const isSelected =
                            selectedServeWindowId === serveWindow.id;

                          return (
                            <ServeWindowRange
                              key={serveWindow.id}
                              serveWindow={serveWindow}
                              duration={duration}
                              currentTime={currentTime}
                              isSelected={isSelected}
                              isDemo={isDemo}
                              onClick={() => {
                                setSelectedServeWindow(serveWindow);
                                setSelectedServeWindowId(serveWindow.id);
                                setIsModalOpen(true);
                              }}
                              onContactClick={() => {
                                if (serveWindow.contact_timestamp) {
                                  seekToTime(serveWindow.contact_timestamp);
                                }
                              }}
                              onMarkContact={async (timestamp) => {
                                try {
                                  await updateServeWindow(serveWindow.id, {
                                    contact_timestamp: timestamp,
                                  });
                                  if (videoId) {
                                    queryClient.invalidateQueries({
                                      queryKey:
                                        contactTimestampsQueryKey(videoId),
                                    });
                                  }
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
                          onClick={createServeWindowFromMarks}
                          disabled={!markedRange || isDemo}
                          title={
                            isDemo
                              ? 'Demo mode: range tagging is disabled'
                              : 'Create serve window from marked range'
                          }
                        >
                          Create serve window
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
                    {/* Zoom Controls */}
                    <div className="zoom-controls-inline">
                      <button
                        className="control-btn"
                        onClick={zoomOut}
                        disabled={zoomLevel === ZOOM_LEVELS[0]}
                        title="Zoom out (-)"
                      >
                        −
                      </button>
                      <span
                        className="zoom-level-display"
                        onClick={resetZoom}
                        title="Reset zoom (0)"
                      >
                        {Math.round(zoomLevel * 100)}%
                      </span>
                      <button
                        className="control-btn"
                        onClick={zoomIn}
                        disabled={
                          zoomLevel === ZOOM_LEVELS[ZOOM_LEVELS.length - 1]
                        }
                        title="Zoom in (+)"
                      >
                        +
                      </button>
                    </div>
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

          {/* Posture Analysis Sidebar - Removed: serve windows already have metrics via serve analysis */}
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
              <AddServeWindowButton
                currentTime={currentTime}
                videoId={videoId || 0}
                videoDuration={duration}
                fps={videoMetadata?.fps}
                onAddServeWindow={async (serveWindow: ServeWindowCreate) => {
                  await createServeWindow(serveWindow);
                  if (videoId) {
                    queryClient.invalidateQueries({
                      queryKey: contactTimestampsQueryKey(videoId),
                    });
                  }
                  if (openRange) {
                    clearRangeMarks();
                  }
                }}
                isVisible={isAddServeWindowVisible}
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
              {/* Proposal ranges (shown before serve windows) */}
              {proposals.length > 0 && duration > 0 && (
                <div className="video-controls-below__proposal-ranges">
                  {proposals.map((proposal) => (
                    <ProposalRange
                      key={proposal.id}
                      proposal={proposal}
                      duration={duration}
                      lowConfidenceThreshold={lowConfidenceThreshold}
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
              {/* Serve window ranges */}
              {serveWindows.length > 0 && duration > 0 && (
                <div
                  className="video-controls-below__serve-window-ranges"
                  data-tour="serve-window-ranges"
                >
                  {serveWindows.map((serveWindow) => {
                    const isSelected = selectedServeWindowId === serveWindow.id;

                    return (
                      <ServeWindowRange
                        key={serveWindow.id}
                        serveWindow={serveWindow}
                        duration={duration}
                        currentTime={currentTime}
                        isSelected={isSelected}
                        isDemo={isDemo}
                        onClick={() => {
                          setSelectedServeWindow(serveWindow);
                          setSelectedServeWindowId(serveWindow.id);
                          setIsModalOpen(true);
                        }}
                        onContactClick={() => {
                          if (serveWindow.contact_timestamp) {
                            seekToTime(serveWindow.contact_timestamp);
                          }
                        }}
                        onMarkContact={async (timestamp) => {
                          try {
                            await updateServeWindow(serveWindow.id, {
                              contact_timestamp: timestamp,
                            });
                            if (videoId) {
                              queryClient.invalidateQueries({
                                queryKey: contactTimestampsQueryKey(videoId),
                              });
                            }
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
                    onClick={createServeWindowFromMarks}
                    disabled={!markedRange || isDemo}
                    title={
                      isDemo
                        ? 'Demo mode: range tagging is disabled'
                        : 'Create serve window from marked range'
                    }
                  >
                    Create serve window
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

          {/* Navigation: Contact (when any) | Serve | Play | Serve | Contact */}
          <div className="video-controls-below__nav">
            {hasAnyContact && (
              <button
                className="video-controls-below__contact-btn"
                disabled={!hasPreviousContact}
                onClick={navigateToPreviousContact}
                title={
                  hasPreviousContact
                    ? 'Go to previous contact'
                    : 'No previous contact'
                }
              >
                <ArrowBackIcon size={18} />
                <span className="video-controls-below__contact-icon">◉</span>
                <span>Previous Contact</span>
              </button>
            )}
            <button
              className="video-controls-below__nav-btn"
              disabled={!hasPreviousServeWindow}
              onClick={navigateToPreviousServeWindow}
              title={
                hasPreviousServeWindow
                  ? 'Go to previous serve'
                  : 'No previous serve'
              }
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
              disabled={!hasNextServeWindow}
              onClick={navigateToNextServeWindow}
              title={hasNextServeWindow ? 'Go to next serve' : 'No next serve'}
            >
              <span>Next Serve</span>
              <ArrowBackIcon size={18} />
            </button>
            {hasAnyContact && (
              <button
                className="video-controls-below__contact-btn video-controls-below__contact-btn--next"
                disabled={!hasNextContact}
                onClick={navigateToNextContact}
                title={
                  hasNextContact ? 'Go to next contact' : 'No next contact'
                }
              >
                <span>Next Contact</span>
                <span className="video-controls-below__contact-icon">◉</span>
                <ArrowBackIcon size={18} />
              </button>
            )}
          </div>

          {/* Serve Detail Panel (inline, non-blocking) */}
          {isModalOpen && selectedServeWindow && (
            <div className="video-controls-below__serve-panel">
              <ServeWindowModal
                serveWindow={selectedServeWindow}
                isOpen={isModalOpen}
                videoDuration={duration}
                currentTime={currentTime}
                isDemo={isDemo}
                mode="panel"
                onClose={() => {
                  setIsModalOpen(false);
                  setSelectedServeWindow(null);
                  setSelectedServeWindowId(undefined);
                }}
                onUpdate={async (serveWindowId, updates) => {
                  await updateServeWindow(serveWindowId, updates);
                  if (videoId && updates.contact_timestamp !== undefined) {
                    queryClient.invalidateQueries({
                      queryKey: contactTimestampsQueryKey(videoId),
                    });
                  }
                }}
                onDelete={async (serveWindowId) => {
                  await deleteServeWindow(serveWindowId);
                  if (videoId) {
                    queryClient.invalidateQueries({
                      queryKey: contactTimestampsQueryKey(videoId),
                    });
                  }
                }}
                onSeek={seekToTime}
              />
            </div>
          )}
        </div>
      )}

      {/* Serve Attempt Management Modal (overlay mode for non-controlsBelow) */}
      {!controlsBelow && (
        <ServeWindowModal
          serveWindow={selectedServeWindow}
          isOpen={isModalOpen}
          videoDuration={duration}
          currentTime={currentTime}
          isDemo={isDemo}
          mode="overlay"
          onClose={() => {
            setIsModalOpen(false);
            setSelectedServeWindow(null);
            setSelectedServeWindowId(undefined);
          }}
          onUpdate={async (serveWindowId, updates) => {
            await updateServeWindow(serveWindowId, updates);
            if (videoId && updates.contact_timestamp !== undefined) {
              queryClient.invalidateQueries({
                queryKey: contactTimestampsQueryKey(videoId),
              });
            }
          }}
          onDelete={async (serveWindowId) => {
            await deleteServeWindow(serveWindowId);
            if (videoId) {
              queryClient.invalidateQueries({
                queryKey: contactTimestampsQueryKey(videoId),
              });
            }
          }}
          onSeek={seekToTime}
        />
      )}
    </div>
  );
};

export default VideoPlayer;
