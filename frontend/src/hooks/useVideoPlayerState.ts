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
import { ServeWindow, ServeWindowCreate } from '../types/serveWindow';

// Re-export for use by VideoPlayer component (used in JSX callbacks)
export { contactTimestampsQueryKey };
export type { ServeWindowCreate };

// Manual zoom levels available
export const ZOOM_LEVELS = [1, 1.25, 1.5, 2, 2.5, 3];

export type ViewMode = 'video' | 'skeleton' | 'stickfigure';

interface UseVideoPlayerStateParams {
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

export interface UseVideoPlayerStateReturn {
  // Refs
  videoRef: React.RefObject<HTMLVideoElement | null>;
  containerRef: React.RefObject<HTMLDivElement | null>;
  scrubberTrackRef: React.RefObject<HTMLDivElement | null>;

  // Video playback state
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;
  error: string | null;

  // Video loading
  videoAspectRatio: number | null;
  resolvedVideoUrl: string;
  isLoadingUrl: boolean;
  videoMetadata: ReturnType<typeof useVideoMetadata>['data'];

  // Scrubbing
  isScrubbing: boolean;

  // Serve window modal state
  selectedServeWindow: ServeWindow | null;
  setSelectedServeWindow: React.Dispatch<
    React.SetStateAction<ServeWindow | null>
  >;
  isModalOpen: boolean;
  setIsModalOpen: React.Dispatch<React.SetStateAction<boolean>>;
  selectedServeWindowId: number | undefined;
  setSelectedServeWindowId: React.Dispatch<
    React.SetStateAction<number | undefined>
  >;

  // View mode
  viewMode: ViewMode;
  setViewMode: React.Dispatch<React.SetStateAction<ViewMode>>;

  // Zoom
  zoomLevel: number;
  zoomIn: () => void;
  zoomOut: () => void;
  resetZoom: () => void;

  // Scroll hint
  showScrollHint: boolean;

  // Range marks
  rangeInTime: number | null;
  rangeOutTime: number | null;
  openRange: { start: number; end: number } | null;
  openRequestId: number;
  markedRange: { start: number; end: number } | null;
  hasRangeMarks: boolean;
  clearRangeMarks: () => void;
  createServeWindowFromMarks: () => void;

  // Highlight
  highlightTimestamp: number | null;
  setHighlightTimestamp: React.Dispatch<React.SetStateAction<number | null>>;

  // Detection
  isRunningDetection: boolean;
  detectionMessage: string | null;
  handleAutoDetect: () => Promise<void>;
  handleClearProposals: () => Promise<void>;
  showDetectionMessage: (message: string) => void;
  hasExistingDetections: boolean | null;

  // Computed visibility flags
  isAddServeWindowVisible: boolean;
  hasPoseDataForDetection: boolean;

  // Playback handlers
  togglePlay: () => Promise<void>;
  handleSeek: (e: React.ChangeEvent<HTMLInputElement>) => void;
  seekToTime: (time: number) => void;
  handleSeekStart: () => void;
  handleSeekEnd: () => void;
  handleVolumeChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  toggleMute: () => void;
  formatTime: (time: number) => string;

  // Frame navigation
  frameStep: number;
  navigateFrame: (direction: 'forward' | 'backward') => void;
  navigateToNextFrame: () => void;
  navigateToPreviousFrame: () => void;

  // Serve window navigation
  navigateToServeWindowById: (serveWindowId: number) => void;
  navigateToPreviousServeWindow: () => void;
  navigateToNextServeWindow: () => void;
  hasPreviousServeWindow: boolean;
  hasNextServeWindow: boolean;

  // Contact navigation
  navigateToPreviousContact: () => void;
  navigateToNextContact: () => void;
  hasPreviousContact: boolean;
  hasNextContact: boolean;
  hasAnyContact: boolean;

  // Timestamp navigation
  navigateToTimestamp: (timestamp: number) => void;

  // Video click / fullscreen
  handleVideoClick: () => void;
  toggleFullscreen: () => void;

  // Formatted labels
  formattedCurrentTime: string;
  formattedDuration: string;
  rangeInLabel: string;
  rangeOutLabel: string;

  // Serve windows data (from hook)
  serveWindows: ServeWindow[];
  updateServeWindow: ReturnType<typeof useServeWindows>['updateServeWindow'];
  deleteServeWindow: ReturnType<typeof useServeWindows>['deleteServeWindow'];
  createServeWindow: ReturnType<typeof useServeWindows>['createServeWindow'];

  // Proposals data (from hook)
  proposals: ReturnType<typeof useServeProposals>['proposals'];
  detectionStatus: ReturnType<typeof useServeProposals>['detectionStatus'];
  acceptProposal: ReturnType<typeof useServeProposals>['acceptProposal'];
  rejectProposal: ReturnType<typeof useServeProposals>['rejectProposal'];
  editProposal: ReturnType<typeof useServeProposals>['editProposal'];

  // Contact timestamps
  contactTimestamps: number[];

  // Query client (for invalidations in JSX callbacks)
  queryClient: ReturnType<typeof useQueryClient>;

  // Refs exposed for JSX callbacks
  wasPlayingRef: React.MutableRefObject<boolean>;
  setOpenRange: React.Dispatch<
    React.SetStateAction<{ start: number; end: number } | null>
  >;
}

export function useVideoPlayerState({
  videoUrl,
  videoId,
  hasPoseData = false,
  controlsBelow = false,
  onContactNavigate,
  onNavigateReady,
  isDemo = false,
  naturalScroll: naturalScrollProp = false,
  aspectRatioMode = 'contain',
}: UseVideoPlayerStateParams): UseVideoPlayerStateReturn {
  // ── Refs ──────────────────────────────────────────────────────────────
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const scrubberTrackRef = useRef<HTMLDivElement>(null);
  const scrollHintShownRef = useRef(false);
  const naturalScrollRef = useRef(naturalScrollProp);
  const wasPlayingRef = useRef<boolean>(false);
  const toastTimeoutRef = useRef<number | null>(null);

  // ── State: video playback ─────────────────────────────────────────────
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── State: video aspect ratio / loading ───────────────────────────────
  const [videoAspectRatio, setVideoAspectRatio] = useState<number | null>(null);

  // ── State: scrubbing ──────────────────────────────────────────────────
  const [isScrubbing, setIsScrubbing] = useState(false);

  // ── State: serve window modal ─────────────────────────────────────────
  const [selectedServeWindow, setSelectedServeWindow] =
    useState<ServeWindow | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedServeWindowId, setSelectedServeWindowId] = useState<
    number | undefined
  >();

  // ── State: view mode ──────────────────────────────────────────────────
  const [viewMode, setViewMode] = useState<ViewMode>('video');

  // ── State: zoom ───────────────────────────────────────────────────────
  const [zoomLevel, setZoomLevel] = useState(1);

  // ── State: scroll hint ────────────────────────────────────────────────
  const [showScrollHint, setShowScrollHint] = useState(false);

  // ── State: highlight ──────────────────────────────────────────────────
  const [highlightTimestamp, setHighlightTimestamp] = useState<number | null>(
    null
  );

  // ── State: range marks ────────────────────────────────────────────────
  const [openRequestId, setOpenRequestId] = useState(0);
  const [openRange, setOpenRange] = useState<{
    start: number;
    end: number;
  } | null>(null);
  const [rangeInTime, setRangeInTime] = useState<number | null>(null);
  const [rangeOutTime, setRangeOutTime] = useState<number | null>(null);

  // ── State: detection ──────────────────────────────────────────────────
  const [detectionMessage, setDetectionMessage] = useState<string | null>(null);
  const [isRunningDetection, setIsRunningDetection] = useState(false);

  // ── Computed flags ────────────────────────────────────────────────────
  const isAddServeWindowVisible = !!videoId && !error && duration > 0;
  const hasPoseDataForDetection = hasPoseData && !!videoId;

  // ── External hooks ────────────────────────────────────────────────────
  const queryClient = useQueryClient();

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

  const { contactTimestamps } = useContactTimestamps(videoId);

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

  const { resolvedUrl: resolvedVideoUrl, isLoading: isLoadingUrl } =
    useVideoUrl({
      videoId,
      videoUrl,
      expiresIn: 3600,
    });

  const { data: videoMetadata } = useVideoMetadata(videoId);

  // ── Detection message toast ───────────────────────────────────────────
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

  const hasExistingDetections =
    detectionStatus &&
    (detectionStatus.pending_proposals > 0 ||
      detectionStatus.serve_windows > 0);

  // ── Auto-detect handler ───────────────────────────────────────────────
  const handleAutoDetect = useCallback(async () => {
    if (!videoId || isRunningDetection) return;

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

  // ── Clear proposals handler ───────────────────────────────────────────
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

  // ── Zoom helpers ──────────────────────────────────────────────────────
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

  // ── Playback handlers ────────────────────────────────────────────────
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
      if (err instanceof Error && err.name === 'AbortError') {
        return;
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

    if (isPlaying) {
      video.pause();
    }
  };

  const handleSeekEnd = () => {
    const video = videoRef.current;
    if (!video) return;

    setIsScrubbing(false);
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

  // ── Frame navigation ─────────────────────────────────────────────────
  const frameStep = useMemo(() => {
    if (videoMetadata?.fps && videoMetadata.fps > 0) {
      return 1 / videoMetadata.fps;
    }
    return 0.1;
  }, [videoMetadata?.fps]);

  const navigateFrame = useCallback(
    (direction: 'forward' | 'backward') => {
      const video = videoRef.current;
      if (!video || !videoMetadata?.fps) return;

      const frameTime = 1 / videoMetadata.fps;
      const newTime =
        direction === 'forward'
          ? Math.min(video.currentTime + frameTime, duration)
          : Math.max(video.currentTime - frameTime, 0);

      setCurrentTime(newTime);
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

  // ── Range marks ───────────────────────────────────────────────────────
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

  // ── Serve window navigation ───────────────────────────────────────────
  const navigateToServeWindowById = useCallback(
    (serveWindowId: number) => {
      const serveWindow = serveWindows.find((sa) => sa.id === serveWindowId);
      if (!serveWindow) return;

      const video = videoRef.current;
      if (!video) return;

      if (isPlaying) {
        video.pause();
      }

      const targetTime = serveWindow.start_timestamp;

      setCurrentTime(targetTime);
      setSelectedServeWindowId(serveWindow.id);

      video.currentTime = targetTime;

      onContactNavigate?.(serveWindow.id);
    },
    [serveWindows, isPlaying, onContactNavigate]
  );

  const sortedServeWindows = useMemo(() => {
    return [...serveWindows].sort((a, b) => {
      return a.start_timestamp - b.start_timestamp;
    });
  }, [serveWindows]);

  const navigateToPreviousServeWindow = useCallback(() => {
    if (sortedServeWindows.length === 0) return;

    const video = videoRef.current;
    const videoTime = video?.currentTime ?? currentTime;

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

    const tolerance = 0.1;
    const nextAttempt = sortedServeWindows.find((sa) => {
      return sa.start_timestamp > videoTime + tolerance;
    });

    if (nextAttempt) {
      navigateToServeWindowById(nextAttempt.id);
    }
  }, [sortedServeWindows, currentTime, navigateToServeWindowById]);

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

  // ── Contact navigation ────────────────────────────────────────────────
  const hasAnyContact = contactTimestamps.length > 0;

  const CONTACT_TOLERANCE = 0.1;

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

  const navigateToTimestamp = useCallback(
    (timestamp: number) => {
      const video = videoRef.current;
      if (!video) return;

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

  // ── Video click / fullscreen ──────────────────────────────────────────
  const handleVideoClick = () => {
    if (controlsBelow) {
      togglePlay();
    }
  };

  const toggleFullscreen = () => {
    const video = videoRef.current;
    if (!video) return;

    if (!document.fullscreenElement) {
      video.requestFullscreen().catch(() => {
        // Silently handle fullscreen errors
      });
    } else {
      document.exitFullscreen().catch(() => {
        // Silently handle fullscreen exit errors
      });
    }
  };

  // ── Formatted labels ──────────────────────────────────────────────────
  const formattedCurrentTime = useMemo(
    () => formatTime(currentTime),
    [currentTime, formatTime]
  );
  const formattedDuration = useMemo(
    () => formatTime(duration),
    [duration, formatTime]
  );
  const rangeInLabel =
    rangeInTime !== null ? formatTime(rangeInTime) : '\u2014';
  const rangeOutLabel =
    rangeOutTime !== null ? formatTime(rangeOutTime) : '\u2014';

  // ── Effects ───────────────────────────────────────────────────────────

  // Cleanup toast timeout on unmount
  useEffect(() => {
    return () => {
      if (toastTimeoutRef.current) {
        window.clearTimeout(toastTimeoutRef.current);
      }
    };
  }, []);

  // Reset aspect ratio when video URL changes
  useEffect(() => {
    setVideoAspectRatio(null);
  }, [resolvedVideoUrl, videoId, videoUrl]);

  // Clear error state when URL changes
  useEffect(() => {
    setError(null);
  }, [resolvedVideoUrl]);

  // Video element event listeners
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      const currentVideo = videoRef.current;
      if (!currentVideo) return;
      setDuration(currentVideo.duration);
      setError(null);

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

    const handleError = (_e: Event) => {
      const currentVideo = videoRef.current;
      if (!currentVideo) return;

      if (isLoadingUrl) {
        return;
      }

      if (!currentVideo.currentSrc || currentVideo.currentSrc === '') {
        return;
      }

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
      container.style.paddingBottom = '';
    }

    return () => {
      if (container) {
        container.style.paddingBottom = '';
      }
    };
  }, [aspectRatioMode, videoAspectRatio]);

  // Stable navigate ref for exposing to parent
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

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
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

    document.addEventListener('keydown', handleKeyDown);

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

  // Sync naturalScroll prop to ref
  useEffect(() => {
    naturalScrollRef.current = naturalScrollProp;
  }, [naturalScrollProp]);

  // Mouse wheel for frame-by-frame navigation
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (event: WheelEvent) => {
      if (!videoMetadata?.fps) return;

      event.preventDefault();

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

    const handleMouseEnter = () => {
      if (!scrollHintShownRef.current && videoMetadata?.fps) {
        setShowScrollHint(true);
        scrollHintShownRef.current = true;
        setTimeout(() => setShowScrollHint(false), 3000);
      }
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    container.addEventListener('mouseenter', handleMouseEnter);

    return () => {
      container.removeEventListener('wheel', handleWheel);
      container.removeEventListener('mouseenter', handleMouseEnter);
    };
  }, [videoMetadata?.fps, navigateToNextFrame, navigateToPreviousFrame]);

  // ── Return ────────────────────────────────────────────────────────────
  return {
    // Refs
    videoRef,
    containerRef,
    scrubberTrackRef,

    // Video playback state
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    error,

    // Video loading
    videoAspectRatio,
    resolvedVideoUrl,
    isLoadingUrl,
    videoMetadata,

    // Scrubbing
    isScrubbing,

    // Serve window modal state
    selectedServeWindow,
    setSelectedServeWindow,
    isModalOpen,
    setIsModalOpen,
    selectedServeWindowId,
    setSelectedServeWindowId,

    // View mode
    viewMode,
    setViewMode,

    // Zoom
    zoomLevel,
    zoomIn,
    zoomOut,
    resetZoom,

    // Scroll hint
    showScrollHint,

    // Range marks
    rangeInTime,
    rangeOutTime,
    openRange,
    openRequestId,
    markedRange,
    hasRangeMarks,
    clearRangeMarks,
    createServeWindowFromMarks,

    // Highlight
    highlightTimestamp,
    setHighlightTimestamp,

    // Detection
    isRunningDetection,
    detectionMessage,
    handleAutoDetect,
    handleClearProposals,
    showDetectionMessage,
    hasExistingDetections: hasExistingDetections ?? false,

    // Computed visibility flags
    isAddServeWindowVisible,
    hasPoseDataForDetection,

    // Playback handlers
    togglePlay,
    handleSeek,
    seekToTime,
    handleSeekStart,
    handleSeekEnd,
    handleVolumeChange,
    toggleMute,
    formatTime,

    // Frame navigation
    frameStep,
    navigateFrame,
    navigateToNextFrame,
    navigateToPreviousFrame,

    // Serve window navigation
    navigateToServeWindowById,
    navigateToPreviousServeWindow,
    navigateToNextServeWindow,
    hasPreviousServeWindow,
    hasNextServeWindow,

    // Contact navigation
    navigateToPreviousContact,
    navigateToNextContact,
    hasPreviousContact,
    hasNextContact,
    hasAnyContact,

    // Timestamp navigation
    navigateToTimestamp,

    // Video click / fullscreen
    handleVideoClick,
    toggleFullscreen,

    // Formatted labels
    formattedCurrentTime,
    formattedDuration,
    rangeInLabel,
    rangeOutLabel,

    // Serve windows data
    serveWindows,
    updateServeWindow,
    deleteServeWindow,
    createServeWindow,

    // Proposals data
    proposals,
    detectionStatus,
    acceptProposal,
    rejectProposal,
    editProposal,

    // Contact timestamps
    contactTimestamps,

    // Query client
    queryClient,

    // Refs exposed for JSX callbacks
    wasPlayingRef,
    setOpenRange,
  };
}
