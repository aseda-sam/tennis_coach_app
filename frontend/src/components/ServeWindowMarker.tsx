import React from 'react';
import { ServeWindow } from '../services/serveWindowApi';
import './BallContactMarker.css'; // Reuse styles

interface ServeWindowMarkerProps {
  serveWindow: ServeWindow;
  position: number; // Position as percentage (0-100) along the timeline (using start_timestamp)
  isSelected?: boolean;
  onClick?: () => void;
}

const ServeWindowMarker: React.FC<ServeWindowMarkerProps> = ({
  serveWindow,
  position,
  isSelected = false,
  onClick,
}) => {
  const getServeTypeColor = (): string => '#6b7280';

  return (
    <div
      className={`ball-contact-marker ${isSelected ? 'selected' : ''}`}
      style={{ left: `${position}%` }}
      onClick={onClick}
    >
      <div className="marker-content">
        <div
          className="marker-dot"
          style={{ backgroundColor: getServeTypeColor() }}
        >
          <span className="marker-time">
            {serveWindow.contact_timestamp
              ? `${serveWindow.contact_timestamp.toFixed(3)}s`
              : `${serveWindow.start_timestamp.toFixed(3)}s`}
          </span>
        </div>
      </div>

      <div className="marker-tooltip">
        <div className="tooltip-content">
          <div className="tooltip-header">
            <span className="contact-hand">
              Serve Attempt #{serveWindow.serve_number || '?'}
            </span>
            {serveWindow.court_side && (
              <span className="stroke-type">
                {serveWindow.court_side.charAt(0).toUpperCase() +
                  serveWindow.court_side.slice(1)}{' '}
                Court
              </span>
            )}
          </div>

          {serveWindow.serve_subtype && (
            <div className="stroke-subtype">
              {serveWindow.serve_subtype.charAt(0).toUpperCase() +
                serveWindow.serve_subtype.slice(1)}
            </div>
          )}

          <div className="contact-details">
            <div>Start: {serveWindow.start_timestamp.toFixed(3)}s</div>
            <div>End: {serveWindow.end_timestamp.toFixed(3)}s</div>
            {serveWindow.contact_timestamp && (
              <div>Contact: {serveWindow.contact_timestamp.toFixed(3)}s</div>
            )}
            {serveWindow.in_out && (
              <div>Result: {serveWindow.in_out.replace('_', ' ')}</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServeWindowMarker;
