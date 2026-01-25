import React from 'react';
import { ServeAttempt } from '../services/serveAttemptApi';
import './BallContactMarker.css'; // Reuse styles

interface ServeAttemptMarkerProps {
  serveAttempt: ServeAttempt;
  position: number; // Position as percentage (0-100) along the timeline (using start_timestamp)
  isSelected?: boolean;
  onClick?: () => void;
}

const ServeAttemptMarker: React.FC<ServeAttemptMarkerProps> = ({
  serveAttempt,
  position,
  isSelected = false,
  onClick,
}) => {
  const formatElbowAngle = (angle: number | null): string => {
    if (angle === null || angle === undefined) return 'N/A';
    return `${Math.round(angle)}°`;
  };

  const getAngleDescription = (angle: number | null): string => {
    if (angle === null || angle === undefined) return 'Not analyzed';

    if (angle < 90) return 'Very bent';
    if (angle < 120) return 'Bent';
    if (angle < 150) return 'Good range';
    return 'Straight';
  };

  const getServeTypeColor = (): string => {
    // Color coding for serve attempts
    if (serveAttempt.elbow_angle_at_contact !== null) {
      return '#3b82f6'; // blue-500 - has metrics
    }
    return '#6b7280'; // gray-500 - no metrics yet
  };

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
            {serveAttempt.contact_timestamp
              ? `${serveAttempt.contact_timestamp.toFixed(3)}s`
              : `${serveAttempt.start_timestamp.toFixed(3)}s`}
          </span>
        </div>
      </div>

      <div className="marker-tooltip">
        <div className="tooltip-content">
          <div className="tooltip-header">
            <span className="contact-hand">
              Serve Attempt #{serveAttempt.serve_number || '?'}
            </span>
            {serveAttempt.court_side && (
              <span className="stroke-type">
                {serveAttempt.court_side.charAt(0).toUpperCase() + serveAttempt.court_side.slice(1)} Court
              </span>
            )}
          </div>

          {serveAttempt.serve_subtype && (
            <div className="stroke-subtype">
              {serveAttempt.serve_subtype.charAt(0).toUpperCase() + serveAttempt.serve_subtype.slice(1)}
            </div>
          )}

          {serveAttempt.elbow_angle_at_contact !== null ? (
            <div className="posture-info">
              <div className="elbow-angle">
                <strong>Elbow Angle:</strong>{' '}
                {formatElbowAngle(serveAttempt.elbow_angle_at_contact)}
              </div>
              <div className="angle-assessment">
                {getAngleDescription(serveAttempt.elbow_angle_at_contact)}
              </div>
            </div>
          ) : (
            <div className="no-analysis">No metrics yet - run serve analysis</div>
          )}

          <div className="contact-details">
            <div>
              Start: {serveAttempt.start_timestamp.toFixed(3)}s
            </div>
            <div>
              End: {serveAttempt.end_timestamp.toFixed(3)}s
            </div>
            {serveAttempt.contact_timestamp && (
              <div>
                Contact: {serveAttempt.contact_timestamp.toFixed(3)}s
              </div>
            )}
            {serveAttempt.in_out && (
              <div>
                Result: {serveAttempt.in_out.replace('_', ' ')}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServeAttemptMarker;
