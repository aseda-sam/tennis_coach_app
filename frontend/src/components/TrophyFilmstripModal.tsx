import React, { useCallback, useEffect } from 'react';
import { ServeWindow } from '../types/serveWindow';
import { useVideoTrophyFrames } from '../hooks/useVideoTrophyFrames';
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
                    {formatMethod(frame.method)}
                    <br />
                    {frame.confidence.toFixed(2)} conf
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TrophyFilmstripModal;
