import React, { useCallback, useEffect } from 'react';
import { ServeWindow } from '../types/serveWindow';
import {
  TrophyFrameData,
  useVideoTrophyFrames,
} from '../hooks/useVideoTrophyFrames';
import { useServeWindowFrame } from '../hooks/useServeWindowFrame';
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

export function formatMethod(method: string): string {
  return METHOD_LABELS[method] ?? method.replaceAll('_', ' ');
}

/* ─── Reusable frame cell ─── */

export interface TrophyFrameCellProps {
  serveWindowId: number;
  label: string;
  method: string;
  confidence: number;
}

export const TrophyFrameCell: React.FC<TrophyFrameCellProps> = ({
  serveWindowId,
  label,
  method,
  confidence,
}) => {
  const { frameUrl, isLoading } = useServeWindowFrame(serveWindowId);

  return (
    <div className="trophy-filmstrip__cell">
      <div className="trophy-filmstrip__frame">
        {isLoading ? (
          <div className="trophy-filmstrip__cell-loading">
            <div className="trophy-filmstrip__spinner" />
          </div>
        ) : frameUrl ? (
          <img className="trophy-filmstrip__img" src={frameUrl} alt={label} />
        ) : (
          <span className="trophy-filmstrip__placeholder">No frame</span>
        )}
      </div>
      <span className="trophy-filmstrip__label">{label}</span>
      <span className="trophy-filmstrip__meta">
        {formatMethod(method)}
        <br />
        {confidence.toFixed(2)} conf
      </span>
    </div>
  );
};

/* ─── Modal ─── */

interface TrophyFilmstripModalProps {
  isOpen: boolean;
  onClose: () => void;
  serveWindows: ServeWindow[];
  videoFilename: string;
}

const TrophyFilmstripModal: React.FC<TrophyFilmstripModalProps> = ({
  isOpen,
  onClose,
  serveWindows,
  videoFilename,
}) => {
  const { trophyData, isLoading } = useVideoTrophyFrames(serveWindows, isOpen);

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
              <span>Loading trophy data...</span>
            </div>
          ) : trophyData.length === 0 ? (
            <div className="trophy-filmstrip__empty">
              No trophy positions detected.
            </div>
          ) : (
            <div className="trophy-filmstrip__strip">
              {trophyData.map((td: TrophyFrameData) => (
                <TrophyFrameCell
                  key={td.serveWindowId}
                  serveWindowId={td.serveWindowId}
                  label={`Serve ${td.serveIndex + 1}`}
                  method={td.method}
                  confidence={td.confidence}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TrophyFilmstripModal;
