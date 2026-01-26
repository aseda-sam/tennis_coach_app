import React from 'react';
import { ServeAttempt } from '../services/serveAttemptApi';
import './ServeAttemptRange.css';

interface ServeAttemptRangeProps {
  serveAttempt: ServeAttempt;
  duration: number;
  isSelected?: boolean;
  onClick?: () => void;
  onContactClick?: () => void;
}

const ServeAttemptRange: React.FC<ServeAttemptRangeProps> = ({
  serveAttempt,
  duration,
  isSelected = false,
  onClick,
  onContactClick,
}) => {
  if (duration === 0) return null;

  const startPercent = (serveAttempt.start_timestamp / duration) * 100;
  const endPercent = (serveAttempt.end_timestamp / duration) * 100;
  const width = endPercent - startPercent;
  
  // Calculate contact marker position relative to the range
  const contactPercent = serveAttempt.contact_timestamp !== null
    ? ((serveAttempt.contact_timestamp - serveAttempt.start_timestamp) / (serveAttempt.end_timestamp - serveAttempt.start_timestamp)) * 100
    : null;

  const hasMetrics = serveAttempt.elbow_angle_at_contact !== null;

  // Color based on whether metrics are available
  const rangeColor = hasMetrics
    ? '#3b82f6' // blue - has metrics
    : '#6b7280'; // gray - no metrics yet

  return (
    <div
      className={`serve-attempt-range ${isSelected ? 'selected' : ''}`}
      style={{
        left: `${startPercent}%`,
        width: `${width}%`,
      }}
      onClick={onClick}
      title={`Serve: ${serveAttempt.start_timestamp.toFixed(2)}s - ${serveAttempt.end_timestamp.toFixed(2)}s`}
    >
      {/* Range band */}
      <div
        className="serve-attempt-range__band"
        style={{
          backgroundColor: rangeColor,
          opacity: isSelected ? 0.8 : 0.4,
        }}
      />

      {/* Start marker */}
      <div className="serve-attempt-range__start-marker" />

      {/* End marker */}
      <div className="serve-attempt-range__end-marker" />

      {/* Contact marker (if contact timestamp exists) */}
      {contactPercent !== null && (
        <div
          className="serve-attempt-range__contact-marker"
          style={{ left: `${contactPercent}%` }}
          title={`Contact: ${serveAttempt.contact_timestamp!.toFixed(2)}s (click to go to contact)`}
          onClick={(e) => {
            e.stopPropagation();
            onContactClick?.();
          }}
        />
      )}

      {/* Tooltip on hover */}
      <div className="serve-attempt-range__tooltip">
        <div className="tooltip-content">
          <div className="tooltip-header">
            <span>Serve</span>
            {serveAttempt.serve_number && (
              <span>#{serveAttempt.serve_number}</span>
            )}
          </div>
          <div className="tooltip-details">
            <div>{serveAttempt.start_timestamp.toFixed(2)}s - {serveAttempt.end_timestamp.toFixed(2)}s</div>
            {serveAttempt.contact_timestamp !== null && (
              <div>
                Contact: {serveAttempt.contact_timestamp.toFixed(2)}s
              </div>
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
