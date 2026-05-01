import React from 'react';
import { useServeWindowFrameAtTimestamp } from '../hooks/useServeWindowFrame';
import KneeAngleArc from './KneeAngleArc';
import './KneeFrameOverlay.css';

interface KneeFrameOverlayProps {
  serveWindowId: number;
  timestamp: number;
  angle: number;
}

/**
 * Shows a cropped player frame at min knee flexion.
 * Falls back to KneeAngleArc if the frame can't be loaded.
 */
const KneeFrameOverlay: React.FC<KneeFrameOverlayProps> = ({
  serveWindowId,
  timestamp,
  angle,
}) => {
  const { frameUrl, isLoading } = useServeWindowFrameAtTimestamp(
    serveWindowId,
    timestamp,
    'lower_body'
  );

  if (isLoading) {
    return (
      <div className="knee-frame-overlay knee-frame-overlay--loading">
        <KneeAngleArc angle={angle} />
      </div>
    );
  }

  if (!frameUrl) {
    return (
      <div className="knee-frame-overlay">
        <KneeAngleArc angle={angle} />
      </div>
    );
  }

  return (
    <div className="knee-frame-overlay">
      <img
        src={frameUrl}
        alt={`Player at ${Math.round(angle)}° knee bend`}
        className="knee-frame-overlay__img"
      />
    </div>
  );
};

export default KneeFrameOverlay;
