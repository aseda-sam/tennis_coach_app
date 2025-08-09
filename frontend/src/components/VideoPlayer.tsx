import React, { useEffect, useRef, useState } from 'react';
import {
    CloseIcon,
    FullscreenIcon,
    PauseIcon,
    PlayIcon,
    VolumeIcon,
    VolumeOffIcon
} from './Icons';
import './VideoPlayer.css';

interface VideoPlayerProps {
  videoUrl: string;
  title: string;
  onClose?: () => void;
  showControls?: boolean;
}

const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoUrl,
  title,
  onClose,
  showControls = true,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [showPlayOverlay, setShowPlayOverlay] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      setDuration(video.duration);
      setError(null);
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

    const handleError = () => {
      setError('Failed to load video. Please check if the video file exists.');
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
  }, []);

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

  const formatTime = (time: number): string => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleVideoClick = () => {
    if (showPlayOverlay) {
      togglePlay();
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
        </div>
      )}

      <div className="video-player-wrapper">
        <div className="video-container" onClick={handleVideoClick}>
          <video
            ref={videoRef}
            src={videoUrl}
            className="video-element"
            preload="metadata"
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
        </div>

        {showControls && (
          <div className="video-controls">
            <div className="progress-container">
              <input
                type="range"
                className="progress-bar"
                min="0"
                max={duration || 0}
                value={currentTime}
                onChange={handleSeek}
                step="0.1"
              />
              <div className="time-display">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            <div className="controls-row">
              <div className="left-controls">
                <button
                  className="control-btn play-btn"
                  onClick={togglePlay}
                >
                  {isPlaying ? <PauseIcon size={20} /> : <PlayIcon size={20} />}
                </button>

                <div className="volume-control">
                  <button
                    className="control-btn volume-btn"
                    onClick={toggleMute}
                  >
                    {isMuted ? <VolumeOffIcon size={20} /> : <VolumeIcon size={20} />}
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
                <button className="control-btn fullscreen-btn">
                  <FullscreenIcon size={20} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoPlayer;