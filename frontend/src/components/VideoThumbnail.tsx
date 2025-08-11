import React, { useCallback, useEffect, useRef, useState } from 'react';
import { VideoIcon, PlayIcon } from './Icons';

interface VideoThumbnailProps {
  videoFilename: string;
  className?: string;
  showPlayIcon?: boolean;
  onThumbnailClick?: () => void;
}

const VideoThumbnail: React.FC<VideoThumbnailProps> = ({
  videoFilename,
  className = '',
  showPlayIcon = true,
  onThumbnailClick
}) => {
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const generateThumbnail = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      setError(true);
      setLoading(false);
      return;
    }

    const handleVideoLoad = () => {
      try {
        // Set canvas dimensions to match video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        // Draw the current frame to canvas
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert canvas to data URL
        const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
        setThumbnailUrl(dataUrl);

        // Cache the thumbnail
        const cacheKey = `thumbnail_${videoFilename}`;
        try {
          localStorage.setItem(cacheKey, dataUrl);
        } catch (e) {
          // Handle localStorage quota exceeded
          console.warn('Failed to cache thumbnail:', e);
        }

        setLoading(false);
      } catch (err) {
        console.error('Error generating thumbnail:', err);
        setError(true);
        setLoading(false);
      }
    };

    const handleVideoError = () => {
      console.error('Error loading video for thumbnail');
      setError(true);
      setLoading(false);
    };

    video.addEventListener('loadeddata', handleVideoLoad);
    video.addEventListener('error', handleVideoError);
    
    // Set video source to trigger loading
    video.src = `/api/videos/${videoFilename}/stream`;
    video.currentTime = 0.1; // Seek to 0.1 seconds to avoid black frames

    return () => {
      video.removeEventListener('loadeddata', handleVideoLoad);
      video.removeEventListener('error', handleVideoError);
    };
  }, [videoFilename]);

  useEffect(() => {
    // Check if we have a cached thumbnail first
    const cacheKey = `thumbnail_${videoFilename}`;
    const cachedThumbnail = localStorage.getItem(cacheKey);
    
    if (cachedThumbnail) {
      setThumbnailUrl(cachedThumbnail);
      setLoading(false);
      return;
    }

    generateThumbnail();
  }, [videoFilename, generateThumbnail]);

  const handleClick = () => {
    if (onThumbnailClick) {
      onThumbnailClick();
    }
  };

  if (loading) {
    return (
      <div className={`video-thumbnail loading ${className}`} onClick={handleClick}>
        <VideoIcon size={48} color="#94a3b8" />
        <div className="thumbnail-loading">
          <div className="loading-spinner-small"></div>
        </div>
        {showPlayIcon && (
          <div className="play-overlay">
            <PlayIcon size={32} color="#3b82f6" />
          </div>
        )}
      </div>
    );
  }

  if (error || !thumbnailUrl) {
    return (
      <div className={`video-thumbnail error ${className}`} onClick={handleClick}>
        <VideoIcon size={48} color="#94a3b8" />
        {showPlayIcon && (
          <div className="play-overlay">
            <PlayIcon size={32} color="#3b82f6" />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`video-thumbnail ${className}`} onClick={handleClick}>
      <img 
        src={thumbnailUrl} 
        alt={`Thumbnail for ${videoFilename}`}
        className="thumbnail-image"
      />
      {showPlayIcon && (
        <div className="play-overlay">
          <PlayIcon size={32} color="#3b82f6" />
        </div>
      )}
      
      {/* Hidden elements for thumbnail generation */}
      <video
        ref={videoRef}
        style={{ display: 'none' }}
        muted
        playsInline
        preload="metadata"
      />
      <canvas
        ref={canvasRef}
        style={{ display: 'none' }}
      />
    </div>
  );
};

export default VideoThumbnail;