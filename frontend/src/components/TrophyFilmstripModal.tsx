import React, { useCallback, useEffect } from 'react';
import { ServeWindow } from '../types/serveWindow';
import {
  TrophyFrame,
  useVideoTrophyFrames,
} from '../hooks/useVideoTrophyFrames';
import './TrophyFilmstripModal.css';

/** Map raw backend method strings to human-readable labels. */
const METHOD_LABELS: Record<string, string> = {
  both_arms_raised: 'Both arms raised',
  any_wrist_above_shoulder_fallback: 'Wrist above shoulder',
  fallback_peak_wrist_height: 'Peak wrist height',
  toss_wrist_above_shoulder: 'Toss arm raised',
  max_dominant_wrist_y: 'Peak dominant wrist',
  no_search_range: 'Fallback',
};

function formatMethod(method: string): string {
  return METHOD_LABELS[method] ?? method.replaceAll('_', ' ');
}

interface TrophyFilmstripModalProps {
  isOpen: boolean;
  onClose: () => void;
  serveWindows: ServeWindow[];
  videoUrl: string;
  videoFilename: string;
}

function downloadCompositeImage(frames: TrophyFrame[], filename: string): void {
  const validFrames = frames.filter((f) => f.dataUrl);
  if (validFrames.length === 0) return;

  // Load all images first, then composite
  const images: HTMLImageElement[] = [];
  let loaded = 0;

  validFrames.forEach((frame, i) => {
    const img = new Image();
    img.onload = () => {
      images[i] = img;
      loaded++;
      if (loaded === validFrames.length) {
        compositeAndDownload(images, validFrames, filename);
      }
    };
    img.src = frame.dataUrl!;
  });
}

function compositeAndDownload(
  images: HTMLImageElement[],
  frames: TrophyFrame[],
  filename: string
): void {
  const cellWidth = 280;
  const cellHeight = 220;
  const labelHeight = 40;
  const gap = 16;
  const padding = 24;

  const totalWidth =
    padding * 2 + images.length * cellWidth + (images.length - 1) * gap;
  const totalHeight = padding * 2 + cellHeight + labelHeight;

  const canvas = document.createElement('canvas');
  canvas.width = totalWidth;
  canvas.height = totalHeight;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  // Background
  ctx.fillStyle = '#1a1a2e';
  ctx.fillRect(0, 0, totalWidth, totalHeight);

  images.forEach((img, i) => {
    const x = padding + i * (cellWidth + gap);
    const y = padding;

    // Draw frame with object-fit: contain logic
    const scale = Math.min(cellWidth / img.width, cellHeight / img.height);
    const drawWidth = img.width * scale;
    const drawHeight = img.height * scale;
    const offsetX = x + (cellWidth - drawWidth) / 2;
    const offsetY = y + (cellHeight - drawHeight) / 2;
    ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);

    // Label
    ctx.fillStyle = '#ffffff';
    ctx.font = '600 13px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(frames[i].label, x + cellWidth / 2, y + cellHeight + 18);

    ctx.fillStyle = '#888888';
    ctx.font = '11px sans-serif';
    ctx.fillText(
      `${formatMethod(frames[i].method)} · ${frames[i].confidence.toFixed(2)}`,
      x + cellWidth / 2,
      y + cellHeight + 34
    );
  });

  // Trigger download
  const link = document.createElement('a');
  const baseName = filename.replace(/\.[^.]+$/, '');
  link.download = `${baseName}_trophy_positions.png`;
  link.href = canvas.toDataURL('image/png');
  link.click();
}

const TrophyFilmstripModal: React.FC<TrophyFilmstripModalProps> = ({
  isOpen,
  onClose,
  serveWindows,
  videoUrl,
  videoFilename,
}) => {
  const { frames, isLoading } = useVideoTrophyFrames(
    serveWindows,
    videoUrl,
    isOpen
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div className="trophy-filmstrip-overlay" onClick={onClose}>
      <div className="trophy-filmstrip" onClick={(e) => e.stopPropagation()}>
        <div className="trophy-filmstrip__header">
          <h2 className="trophy-filmstrip__title">
            Trophy Positions
            <span className="trophy-filmstrip__subtitle">{videoFilename}</span>
          </h2>
          <button
            className="trophy-filmstrip__close"
            onClick={onClose}
            type="button"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="trophy-filmstrip__content">
          {isLoading ? (
            <div className="trophy-filmstrip__loading">
              <div className="trophy-filmstrip__spinner" />
              <span>Capturing trophy frames...</span>
            </div>
          ) : frames.length === 0 ? (
            <div className="trophy-filmstrip__empty">
              No trophy positions detected.
            </div>
          ) : (
            <div className="trophy-filmstrip__strip">
              {frames.map((frame) => (
                <div key={frame.serveIndex} className="trophy-filmstrip__cell">
                  <div className="trophy-filmstrip__frame">
                    {frame.dataUrl ? (
                      <img
                        className="trophy-filmstrip__img"
                        src={frame.dataUrl}
                        alt={frame.label}
                      />
                    ) : (
                      <span className="trophy-filmstrip__placeholder">
                        No frame
                      </span>
                    )}
                  </div>
                  <span className="trophy-filmstrip__label">{frame.label}</span>
                  <span className="trophy-filmstrip__meta">
                    {formatMethod(frame.method)} · {frame.confidence.toFixed(2)}{' '}
                    conf
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {frames.length > 0 && !isLoading && (
          <div className="trophy-filmstrip__footer">
            <button
              className="trophy-filmstrip__download"
              onClick={() => downloadCompositeImage(frames, videoFilename)}
              type="button"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Download PNG
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TrophyFilmstripModal;
