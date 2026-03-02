import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ServeWindow } from '../types/serveWindow';
import './ServeThumbnailStrip.css';

interface ServeThumbnailStripProps {
  serveWindows: ServeWindow[];
  currentIndex: number;
  videoUrl: string;
  onNavigate: (index: number) => void;
}

/**
 * Capture a frame from a video at a given timestamp and return a data URL.
 * Uses a hidden <video> element + canvas.
 */
function captureFrame(
  videoUrl: string,
  timestamp: number
): Promise<string | null> {
  return new Promise((resolve) => {
    const video = document.createElement('video');
    video.crossOrigin = 'anonymous';
    video.preload = 'metadata';
    video.muted = true;

    const cleanup = () => {
      video.removeAttribute('src');
      video.load();
    };

    video.addEventListener(
      'seeked',
      () => {
        try {
          const canvas = document.createElement('canvas');
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext('2d');
          if (ctx) {
            ctx.drawImage(video, 0, 0);
            resolve(canvas.toDataURL('image/jpeg', 0.6));
          } else {
            resolve(null);
          }
        } catch {
          resolve(null);
        } finally {
          cleanup();
        }
      },
      { once: true }
    );

    video.addEventListener(
      'error',
      () => {
        cleanup();
        resolve(null);
      },
      { once: true }
    );

    video.src = videoUrl;
    video.addEventListener(
      'loadedmetadata',
      () => {
        video.currentTime = Math.min(timestamp, video.duration);
      },
      { once: true }
    );
  });
}

const ServeThumbnailStrip: React.FC<ServeThumbnailStripProps> = ({
  serveWindows,
  currentIndex,
  videoUrl,
  onNavigate,
}) => {
  const [thumbnails, setThumbnails] = useState<(string | null)[]>(() =>
    new Array(serveWindows.length).fill(null)
  );
  const stripRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLButtonElement>(null);

  // Generate thumbnails
  useEffect(() => {
    let cancelled = false;

    async function generate() {
      const results: (string | null)[] = new Array(serveWindows.length).fill(
        null
      );

      for (let i = 0; i < serveWindows.length; i++) {
        if (cancelled) return;
        const sw = serveWindows[i];
        const captureTime =
          sw.contact_timestamp ?? (sw.start_timestamp + sw.end_timestamp) / 2;
        const thumb = await captureFrame(videoUrl, captureTime);
        results[i] = thumb;
        if (!cancelled) {
          setThumbnails([...results]);
        }
      }
    }

    generate();
    return () => {
      cancelled = true;
    };
  }, [serveWindows, videoUrl]);

  // Scroll active thumbnail into view
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center',
      });
    }
  }, [currentIndex]);

  const handleClick = useCallback(
    (index: number) => {
      onNavigate(index);
    },
    [onNavigate]
  );

  if (serveWindows.length === 0) return null;

  return (
    <div
      className="thumbnail-strip"
      ref={stripRef}
      role="tablist"
      data-tour-step="thumbnail-strip"
    >
      {serveWindows.map((sw, i) => {
        const isActive = i === currentIndex;
        const distance = Math.abs(i - currentIndex);
        const courtSide = sw.court_side
          ? sw.court_side.charAt(0).toUpperCase() + sw.court_side.slice(1)
          : null;

        return (
          <button
            key={sw.id}
            ref={isActive ? activeRef : undefined}
            className={`thumbnail-strip__item${isActive ? ' thumbnail-strip__item--active' : ''}`}
            style={
              !isActive
                ? ({ '--distance': distance } as React.CSSProperties)
                : undefined
            }
            onClick={() => handleClick(i)}
            role="tab"
            aria-selected={isActive}
            aria-label={`Serve ${i + 1}${courtSide ? `, ${courtSide} Court` : ''}`}
            type="button"
          >
            <div className="thumbnail-strip__frame">
              {thumbnails[i] ? (
                <img
                  className="thumbnail-strip__img"
                  src={thumbnails[i]!}
                  alt={`Serve ${i + 1}`}
                />
              ) : (
                <span className="thumbnail-strip__placeholder">{i + 1}</span>
              )}
            </div>
            {thumbnails[i] && (
              <span className="thumbnail-strip__badge">{i + 1}</span>
            )}
            {courtSide && (
              <span className="thumbnail-strip__side">{courtSide}</span>
            )}
          </button>
        );
      })}
    </div>
  );
};

export default ServeThumbnailStrip;
