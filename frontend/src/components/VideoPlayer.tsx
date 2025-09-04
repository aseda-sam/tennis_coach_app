import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useBallContacts } from '../hooks/useBallContacts';
import { BallContact, BallContactCreate } from '../services/ballContactApi';
import AddContactButton from './AddContactButton';
import BallContactMarker from './BallContactMarker';
import BallContactModal from './BallContactModal';
import {
  CloseIcon,
  FullscreenIcon,
  PauseIcon,
  PlayIcon,
  VolumeIcon,
  VolumeOffIcon,
} from './Icons';
import PostureAnalysisSidebar from './PostureAnalysisSidebar';
import './VideoPlayer.css';

interface VideoPlayerProps {
  videoUrl: string;
  title: string;
  onClose?: () => void;
  showControls?: boolean;
  aspectRatioMode?: 'cover' | 'contain' | 'auto';
  videoId?: number; // Video ID for fetching ball contacts
  showPostureAnalysis?: boolean; // Show posture analysis sidebar
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoUrl,
  title,
  onClose,
  showControls = true,
  aspectRatioMode = 'contain',
  videoId,
  showPostureAnalysis = false,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [showPlayOverlay, setShowPlayOverlay] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [videoAspectRatio, setVideoAspectRatio] = useState<number | null>(null);
  const [selectedContact, setSelectedContact] = useState<BallContact | null>(
    null
  );
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isPostureSidebarOpen, setIsPostureSidebarOpen] =
    useState(showPostureAnalysis);
  const [selectedContactId, setSelectedContactId] = useState<
    number | undefined
  >();
  const containerRef = useRef<HTMLDivElement>(null);

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

  // Reset aspect ratio when video URL changes
  useEffect(() => {
    setVideoAspectRatio(null);
  }, [videoUrl]);

  useEffect(() => {
    console.log('VideoPlayer: videoUrl changed to:', videoUrl);
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      console.log('Video loaded metadata - duration:', video.duration);
      setDuration(video.duration);
      setError(null);

      // Calculate and store the video's natural aspect ratio
      if (video.videoWidth && video.videoHeight) {
        const aspectRatio = video.videoWidth / video.videoHeight;
        setVideoAspectRatio(aspectRatio);
        console.log('Video aspect ratio:', aspectRatio);
      }
    };

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
    };

    const handlePlay = () => {
      setIsPlaying(true);
      setShowPlayOverlay(false);
    };

    const handlePause = () => {
      setIsPlaying(false);
      setShowPlayOverlay(true);
    };

    const handleError = (e: Event) => {
      console.error('Video error event:', e);
      const video = videoRef.current;
      if (video) {
        console.error('Video error code:', video.error?.code);
        console.error('Video error message:', video.error?.message);
        console.error('Video ready state:', video.readyState);
        console.error('Video network state:', video.networkState);
      }

      // Provide more specific error messages based on error type
      let errorMessage =
        'Failed to load video. Please check if the video file exists.';
      if (video?.error) {
        switch (video.error.code) {
          case MediaError.MEDIA_ERR_ABORTED:
            errorMessage = 'Video loading was aborted.';
            break;
          case MediaError.MEDIA_ERR_NETWORK:
            errorMessage = 'Network error occurred while loading video.';
            break;
          case MediaError.MEDIA_ERR_DECODE:
            errorMessage = 'Video format is not supported or corrupted.';
            break;
          case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
            errorMessage = 'Video format is not supported by your browser.';
            break;
        }
      }

      setError(errorMessage);
      setShowPlayOverlay(true);
      setIsPlaying(false);
    };

    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('error', handleError);

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('error', handleError);
    };
  }, [videoUrl]);

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

  const togglePlay = async () => {
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
        console.log('Play request was interrupted - this is normal behavior');
        return; // Don't show error for this case
      }
      console.error('Error playing video:', err);
      setError('Failed to play video. Please try again.');
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current;
    if (!video) return;

    const newTime = parseFloat(e.target.value);
    video.currentTime = newTime;
    setCurrentTime(newTime);
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
    if (showPlayOverlay) {
      togglePlay();
    }
  };

  const toggleFullscreen = () => {
    const video = videoRef.current;
    if (!video) return;

    if (!document.fullscreenElement) {
      video.requestFullscreen().catch((err) => {
        console.error('Error attempting to enable fullscreen:', err);
      });
    } else {
      document.exitFullscreen().catch((err) => {
        console.error('Error attempting to exit fullscreen:', err);
      });
    }
  };

  return (
    <div className="video-player-container">
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
              📊
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
        {/* Video Container */}
        <div
          ref={containerRef}
          className={`video-container video-container-${aspectRatioMode} ${
            isPlaying ? 'playing' : 'paused'
          }`}
          onClick={handleVideoClick}
        >
          <video
            ref={videoRef}
            src={videoUrl}
            className={`video-element video-element-${aspectRatioMode}`}
            preload="metadata"
            data-testid="video-element"
          />

          {/* Add Contact Button */}
          <AddContactButton
            currentTime={currentTime}
            videoId={videoId || 0}
            videoDuration={duration}
            onAddContact={async (contact: BallContactCreate) => {
              await createContact(contact);
            }}
            isVisible={!!videoId && !error && duration > 0}
          />

          {error && (
            <div className="error-overlay">
              <div className="error-message">
                <span className="error-icon">⚠️</span>
                <p>{error}</p>
              </div>
            </div>
          )}

          {showPlayOverlay && !error && (
            <div className="play-overlay">
              <div className="play-button">
                <PlayIcon size={32} color="#3b82f6" />
              </div>
            </div>
          )}

          {showControls && (
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
                    step="0.1"
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
                </div>
                <div className="time-display">
                  <span>{formattedCurrentTime}</span>
                  <span>{formattedDuration}</span>
                </div>
              </div>

              <div className="controls-row">
                <div className="left-controls">
                  <button className="control-btn play-btn" onClick={togglePlay}>
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
