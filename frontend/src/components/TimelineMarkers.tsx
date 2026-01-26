import React, { useCallback, useEffect, useRef, useState } from 'react';
import { formatTime } from '../utils/validation';
import './TimelineMarkers.css';

interface TimelineMarkersProps {
  startTime: number;
  endTime: number;
  contactTime: number | null;
  videoDuration: number;
  currentTime: number;
  onStartChange: (time: number) => void;
  onEndChange: (time: number) => void;
  onContactChange: (time: number | null) => void;
  onSeek?: (time: number) => void;
  density?: 'default' | 'compact';
  showHeader?: boolean;
  showActions?: boolean;
}

type MarkerType = 'start' | 'end' | 'contact' | null;

const TimelineMarkers: React.FC<TimelineMarkersProps> = ({
  startTime,
  endTime,
  contactTime,
  videoDuration,
  currentTime,
  onStartChange,
  onEndChange,
  onContactChange,
  onSeek,
  density = 'default',
  showHeader = true,
  showActions = true,
}) => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<MarkerType>(null);
  const [hoverTime, setHoverTime] = useState<number | null>(null);

  // Calculate percentages for positioning
  const startPercent = (startTime / videoDuration) * 100;
  const endPercent = (endTime / videoDuration) * 100;
  const contactPercent = contactTime ? (contactTime / videoDuration) * 100 : null;
  const currentPercent = (currentTime / videoDuration) * 100;

  // Get time from mouse position
  const getTimeFromPosition = useCallback(
    (clientX: number): number => {
      if (!timelineRef.current) return 0;
      const rect = timelineRef.current.getBoundingClientRect();
      const x = clientX - rect.left;
      const percent = Math.max(0, Math.min(100, (x / rect.width) * 100));
      return (percent / 100) * videoDuration;
    },
    [videoDuration]
  );

  // Handle mouse down on marker
  const handleMarkerMouseDown = useCallback(
    (e: React.MouseEvent, markerType: MarkerType) => {
      e.preventDefault();
      e.stopPropagation();
      setDragging(markerType);
    },
    []
  );

  // Handle mouse move
  useEffect(() => {
    if (!dragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const time = getTimeFromPosition(e.clientX);

      if (dragging === 'start') {
        const clampedTime = Math.max(0, Math.min(time, endTime - 0.1));
        onStartChange(clampedTime);
        if (onSeek) onSeek(clampedTime);
      } else if (dragging === 'end') {
        const clampedTime = Math.max(startTime + 0.1, Math.min(time, videoDuration));
        onEndChange(clampedTime);
        if (onSeek) onSeek(clampedTime);
      } else if (dragging === 'contact') {
        const clampedTime = Math.max(startTime, Math.min(time, endTime));
        onContactChange(clampedTime);
        if (onSeek) onSeek(clampedTime);
      }
    };

    const handleMouseUp = () => {
      setDragging(null);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [dragging, getTimeFromPosition, startTime, endTime, videoDuration, onStartChange, onEndChange, onContactChange, onSeek]);

  // Handle timeline click
  const handleTimelineClick = useCallback(
    (e: React.MouseEvent) => {
      if (dragging) return; // Don't handle clicks while dragging
      const time = getTimeFromPosition(e.clientX);
      
      // Determine which marker to set based on click position
      const distToStart = Math.abs(time - startTime);
      const distToEnd = Math.abs(time - endTime);
      const distToContact = contactTime ? Math.abs(time - contactTime) : Infinity;
      
      // If clicking near a marker, don't do anything (let drag handle it)
      if (distToStart < 0.5 || distToEnd < 0.5 || distToContact < 0.5) {
        return;
      }
      
      // If clicking before start, set start
      if (time < startTime) {
        onStartChange(Math.max(0, time));
        if (onSeek) onSeek(time);
      }
      // If clicking after end, set end
      else if (time > endTime) {
        onEndChange(Math.min(videoDuration, time));
        if (onSeek) onSeek(time);
      }
      // If clicking between start and end, set contact
      else {
        onContactChange(time);
        if (onSeek) onSeek(time);
      }
    },
    [dragging, getTimeFromPosition, startTime, endTime, contactTime, videoDuration, onStartChange, onEndChange, onContactChange, onSeek]
  );

  // Handle timeline hover
  const handleTimelineMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (dragging) return;
      const time = getTimeFromPosition(e.clientX);
      setHoverTime(time);
    },
    [dragging, getTimeFromPosition]
  );

  const handleTimelineMouseLeave = useCallback(() => {
    if (!dragging) {
      setHoverTime(null);
    }
  }, [dragging]);

  return (
    <div
      className={`timeline-markers-container ${
        density === 'compact' ? 'timeline-markers-container--compact' : ''
      }`.trim()}
    >
      {showHeader && (
        <div className="timeline-markers-header">
          <div className="timeline-markers-label">Set Range</div>
          <div className="timeline-markers-values">
            <span className="timeline-value">
              IN: <strong>{formatTime(startTime)}</strong>
            </span>
            <span className="timeline-value">
              OUT: <strong>{formatTime(endTime)}</strong>
            </span>
            {contactTime !== null && (
              <span className="timeline-value timeline-value--contact">
                CONTACT: <strong>{formatTime(contactTime)}</strong>
              </span>
            )}
          </div>
        </div>
      )}

      <div
        ref={timelineRef}
        className="timeline-markers-track"
        onClick={handleTimelineClick}
        onMouseMove={handleTimelineMouseMove}
        onMouseLeave={handleTimelineMouseLeave}
      >
        {/* Background track */}
        <div className="timeline-track-bg" />

        {/* Selected range highlight */}
        <div
          className="timeline-range"
          style={{
            left: `${startPercent}%`,
            width: `${endPercent - startPercent}%`,
          }}
        />

        {/* Current time indicator */}
        <div
          className="timeline-current-time"
          style={{ left: `${currentPercent}%` }}
        />

        {/* Hover indicator */}
        {hoverTime !== null && !dragging && (
          <div
            className="timeline-hover-indicator"
            style={{ left: `${(hoverTime / videoDuration) * 100}%` }}
          >
            <div className="timeline-hover-time">{formatTime(hoverTime)}</div>
          </div>
        )}

        {/* Start marker (IN) */}
        <div
          className={`timeline-marker timeline-marker--start ${dragging === 'start' ? 'is-dragging' : ''}`}
          style={{ left: `${startPercent}%` }}
          onMouseDown={(e) => handleMarkerMouseDown(e, 'start')}
          title={`IN: ${formatTime(startTime)}`}
        >
          <div className="timeline-marker-handle" />
          <div className="timeline-marker-label">IN</div>
        </div>

        {/* End marker (OUT) */}
        <div
          className={`timeline-marker timeline-marker--end ${dragging === 'end' ? 'is-dragging' : ''}`}
          style={{ left: `${endPercent}%` }}
          onMouseDown={(e) => handleMarkerMouseDown(e, 'end')}
          title={`OUT: ${formatTime(endTime)}`}
        >
          <div className="timeline-marker-handle" />
          <div className="timeline-marker-label">OUT</div>
        </div>

        {/* Contact marker */}
        {contactTime !== null && (
          <div
            className={`timeline-marker timeline-marker--contact ${dragging === 'contact' ? 'is-dragging' : ''}`}
            style={{ left: `${contactPercent}%` }}
            onMouseDown={(e) => handleMarkerMouseDown(e, 'contact')}
            title={`CONTACT: ${formatTime(contactTime)}`}
          >
            <div className="timeline-marker-handle timeline-marker-handle--contact" />
            <div className="timeline-marker-label timeline-marker-label--contact">
              CONTACT
            </div>
          </div>
        )}
      </div>

      {showActions && (
        <div className="timeline-markers-actions">
          <button
            className="timeline-action-btn"
            onClick={() => {
              const newContact =
                contactTime === null ? (startTime + endTime) / 2 : null;
              onContactChange(newContact);
            }}
            title={contactTime === null ? 'Add contact marker' : 'Remove contact marker'}
          >
            {contactTime === null ? '✓ Add Contact' : '✕ Remove Contact'}
          </button>
          <div className="timeline-help-text">
            Click timeline to set markers • Drag to adjust
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineMarkers;
