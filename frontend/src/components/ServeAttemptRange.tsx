import React, { useState } from 'react';
import { ServeAttempt } from '../services/serveAttemptApi';
import './ServeAttemptRange.css';

interface ServeAttemptRangeProps {
  serveAttempt: ServeAttempt;
  duration: number;
  currentTime?: number;
  isSelected?: boolean;
  isDemo?: boolean;
  onClick?: () => void;
  onContactClick?: () => void;
  onMarkContact?: (timestamp: number) => void;
}

const ServeAttemptRange: React.FC<ServeAttemptRangeProps> = ({
  serveAttempt,
  duration,
  currentTime = 0,
  isSelected = false,
  isDemo = false,
  onClick,
  onContactClick,
  onMarkContact,
}) => {
  const [showMarkContact, setShowMarkContact] = useState(false);
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

  // Check if current time is within this serve attempt's range
  const isCurrentTimeInRange =
    currentTime >= serveAttempt.start_timestamp &&
    currentTime <= serveAttempt.end_timestamp;

  // Determine if we should show the mark contact button
  const canMarkContact =
    !isDemo &&
    onMarkContact &&
    isCurrentTimeInRange &&
    serveAttempt.contact_timestamp === null;

  const handleMarkContact = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onMarkContact && isCurrentTimeInRange) {
      onMarkContact(currentTime);
    }
  };

  return (
    <div
      className={`serve-attempt-range ${isSelected ? 'selected' : ''} ${showMarkContact && canMarkContact ? 'show-mark-contact' : ''}`}
      style={{
        left: `${startPercent}%`,
        width: `${width}%`,
      }}
      onClick={onClick}
      onMouseEnter={() => setShowMarkContact(true)}
      onMouseLeave={() => setShowMarkContact(false)}
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

      {/* Mark Contact button (shown when hovering and no contact exists) */}
      {canMarkContact && showMarkContact && (
        <button
          className="serve-attempt-range__mark-contact-btn"
          onClick={handleMarkContact}
          title="Set contact point at current video time"
        >
          Mark Contact
        </button>
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
