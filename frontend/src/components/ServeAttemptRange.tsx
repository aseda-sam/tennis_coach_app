import React from 'react';
import { ServeAttempt } from '../services/serveAttemptApi';
import './ServeAttemptRange.css';

interface ServeAttemptRangeProps {
  serveAttempt: ServeAttempt;
  duration: number;
  isSelected?: boolean;
  onClick?: () => void;
}

const ServeAttemptRange: React.FC<ServeAttemptRangeProps> = ({
  serveAttempt,
  duration,
  isSelected = false,
  onClick,
}) => {
  if (duration === 0) return null;

  const startPercent = (serveAttempt.start_timestamp / duration) * 100;
  const endPercent = (serveAttempt.end_timestamp / duration) * 100;
  const width = endPercent - startPercent;

  const hasMetrics = serveAttempt.elbow_angle_at_contact !== null;
  const hasContact = serveAttempt.contact_timestamp !== null;

  // Color based on whether metrics are available
  const rangeColor = hasMetrics
    ? '#3b82f6' // blue - has metrics
    : '#6b7280'; // gray - no metrics yet

  // Contact point position within the range
  const contactPercent = hasContact
    ? ((serveAttempt.contact_timestamp! - serveAttempt.start_timestamp) /
        (serveAttempt.end_timestamp - serveAttempt.start_timestamp)) *
      100
    : null;

  return (
    <div
      className={`serve-attempt-range ${isSelected ? 'selected' : ''}`}
      style={{
        left: `${startPercent}%`,
        width: `${width}%`,
      }}
      onClick={onClick}
      title={`Serve attempt: ${serveAttempt.start_timestamp.toFixed(2)}s - ${serveAttempt.end_timestamp.toFixed(2)}s`}
    >
      {/* Range band */}
      <div
        className="serve-attempt-range__band"
        style={{
          backgroundColor: rangeColor,
          opacity: isSelected ? 0.8 : 0.4,
        }}
      />

      {/* Contact point indicator */}
      {hasContact && contactPercent !== null && (
        <div
          className="serve-attempt-range__contact-point"
          style={{
            left: `${contactPercent}%`,
          }}
        />
      )}

      {/* Start marker */}
      <div className="serve-attempt-range__start-marker" />

      {/* End marker */}
      <div className="serve-attempt-range__end-marker" />

      {/* Tooltip on hover */}
      <div className="serve-attempt-range__tooltip">
        <div className="tooltip-content">
          <div className="tooltip-header">
            <span>Serve Attempt</span>
            {serveAttempt.serve_number && (
              <span>#{serveAttempt.serve_number}</span>
            )}
          </div>
          <div className="tooltip-details">
            <div>Start: {serveAttempt.start_timestamp.toFixed(2)}s</div>
            <div>End: {serveAttempt.end_timestamp.toFixed(2)}s</div>
            {hasContact && (
              <div>Contact: {serveAttempt.contact_timestamp!.toFixed(2)}s</div>
            )}
            {hasMetrics && (
              <div>
                Elbow Angle: {Math.round(serveAttempt.elbow_angle_at_contact!)}°
              </div>
            )}
            {serveAttempt.court_side && (
              <div>
                Court: {serveAttempt.court_side.charAt(0).toUpperCase() + serveAttempt.court_side.slice(1)}
              </div>
            )}
            {serveAttempt.serve_subtype && (
              <div>
                Type: {serveAttempt.serve_subtype.charAt(0).toUpperCase() + serveAttempt.serve_subtype.slice(1)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServeAttemptRange;
