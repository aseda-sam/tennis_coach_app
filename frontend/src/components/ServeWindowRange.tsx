import React, { useState } from 'react';
import { ServeWindow } from '../services/serveWindowApi';
import './ServeWindowRange.css';

interface ServeWindowRangeProps {
  serveWindow: ServeWindow;
  duration: number;
  currentTime?: number;
  isSelected?: boolean;
  isDemo?: boolean;
  onClick?: () => void;
  onContactClick?: () => void;
  onMarkContact?: (timestamp: number) => void;
}

const ServeWindowRange: React.FC<ServeWindowRangeProps> = ({
  serveWindow,
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

  const startPercent = (serveWindow.start_timestamp / duration) * 100;
  const endPercent = (serveWindow.end_timestamp / duration) * 100;
  const width = endPercent - startPercent;

  // Calculate contact marker position relative to the range
  const contactPercent =
    serveWindow.contact_timestamp !== null
      ? ((serveWindow.contact_timestamp - serveWindow.start_timestamp) /
          (serveWindow.end_timestamp - serveWindow.start_timestamp)) *
        100
      : null;

  const rangeColor = '#6b7280';

  // Check if current time is within this serve window's range
  const isCurrentTimeInRange =
    currentTime >= serveWindow.start_timestamp &&
    currentTime <= serveWindow.end_timestamp;

  // Determine if we should show the mark contact button
  const canMarkContact =
    !isDemo &&
    onMarkContact &&
    isCurrentTimeInRange &&
    serveWindow.contact_timestamp === null;

  const handleMarkContact = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onMarkContact && isCurrentTimeInRange) {
      onMarkContact(currentTime);
    }
  };

  return (
    <div
      className={`serve-window-range ${isSelected ? 'selected' : ''} ${showMarkContact && canMarkContact ? 'show-mark-contact' : ''}`}
      style={{
        left: `${startPercent}%`,
        width: `${width}%`,
      }}
      onClick={onClick}
      onMouseEnter={() => setShowMarkContact(true)}
      onMouseLeave={() => setShowMarkContact(false)}
      title={`Serve: ${serveWindow.start_timestamp.toFixed(2)}s - ${serveWindow.end_timestamp.toFixed(2)}s`}
    >
      {/* Range band */}
      <div
        className="serve-window-range__band"
        style={{
          backgroundColor: rangeColor,
          opacity: isSelected ? 0.8 : 0.4,
        }}
      />

      {/* Start marker */}
      <div className="serve-window-range__start-marker" />

      {/* End marker */}
      <div className="serve-window-range__end-marker" />

      {/* Contact marker (if contact timestamp exists) */}
      {contactPercent !== null && (
        <div
          className="serve-window-range__contact-marker"
          style={{ left: `${contactPercent}%` }}
          title={`Contact: ${serveWindow.contact_timestamp!.toFixed(2)}s (click to go to contact)`}
          onClick={(e) => {
            e.stopPropagation();
            onContactClick?.();
          }}
        />
      )}

      {/* Mark Contact button (shown when hovering and no contact exists) */}
      {canMarkContact && showMarkContact && (
        <button
          className="serve-window-range__mark-contact-btn"
          onClick={handleMarkContact}
          title="Set contact point at current video time"
        >
          Mark Contact
        </button>
      )}

      {/* Tooltip on hover */}
      <div className="serve-window-range__tooltip">
        <div className="tooltip-content">
          <div className="tooltip-header">
            <span>Serve</span>
            {serveWindow.serve_number && (
              <span>#{serveWindow.serve_number}</span>
            )}
          </div>
          <div className="tooltip-details">
            <div>
              {serveWindow.start_timestamp.toFixed(2)}s -{' '}
              {serveWindow.end_timestamp.toFixed(2)}s
            </div>
            {serveWindow.contact_timestamp !== null && (
              <div>Contact: {serveWindow.contact_timestamp.toFixed(2)}s</div>
            )}
            {serveWindow.court_side && (
              <div>
                Court:{' '}
                {serveWindow.court_side.charAt(0).toUpperCase() +
                  serveWindow.court_side.slice(1)}
              </div>
            )}
            {serveWindow.serve_subtype && (
              <div>
                Type:{' '}
                {serveWindow.serve_subtype.charAt(0).toUpperCase() +
                  serveWindow.serve_subtype.slice(1)}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServeWindowRange;
