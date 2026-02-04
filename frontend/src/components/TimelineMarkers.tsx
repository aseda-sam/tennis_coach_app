import React, { useCallback, useEffect, useRef, useState } from 'react';
import { formatTime } from '../utils/validation';
import './TimelineMarkers.css';

interface TimelineMarkersProps {
  startTime: number;
  endTime: number;
  videoDuration: number;
  currentTime: number;
  onStartChange: (time: number) => void;
  onEndChange: (time: number) => void;
  contactTime?: number | null;
  onContactChange?: (time: number | null) => void;
  onSeek?: (time: number) => void;
  density?: 'default' | 'compact';
  showHeader?: boolean;
  showActions?: boolean;
  /** When true, the slider maps to the serve window (startTime to endTime) instead of the entire video */
  zoomToWindow?: boolean;
}

type MarkerType = 'start' | 'end' | 'contact' | null;

const TimelineMarkers: React.FC<TimelineMarkersProps> = ({
  startTime,
  endTime,
  videoDuration,
  currentTime,
  onStartChange,
  onEndChange,
  contactTime = null,
  onContactChange,
  onSeek,
  density = 'default',
  showHeader = true,
  showActions = true,
  zoomToWindow = false,
}) => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<MarkerType>(null);
  const [hoverTime, setHoverTime] = useState<number | null>(null);

  // When zoomed to window, calculate relative to the window range
  const windowDuration = endTime - startTime;

  // Calculate percentages for positioning
  // When zoomed to window: start is at 0%, end is at 100%
  // When not zoomed: percentages relative to video duration
  const startPercent = zoomToWindow ? 0 : (startTime / videoDuration) * 100;
  const endPercent = zoomToWindow ? 100 : (endTime / videoDuration) * 100;
  const contactPercent =
    contactTime !== null
      ? zoomToWindow
        ? ((contactTime - startTime) / windowDuration) * 100
        : (contactTime / videoDuration) * 100
      : null;
  // Clamp currentPercent when zoomed to window so it stays within bounds
  const currentPercentRaw = zoomToWindow
    ? ((currentTime - startTime) / windowDuration) * 100
    : (currentTime / videoDuration) * 100;
  const currentPercent = zoomToWindow
    ? Math.max(0, Math.min(100, currentPercentRaw))
    : currentPercentRaw;

  // Get time from mouse position
  // When zoomed to window, map to the window range; otherwise map to video duration
  const getTimeFromPosition = useCallback(
    (clientX: number): number => {
      if (!timelineRef.current) return zoomToWindow ? startTime : 0;
      const rect = timelineRef.current.getBoundingClientRect();
      const x = clientX - rect.left;
      const percent = Math.max(0, Math.min(100, (x / rect.width) * 100));

      if (zoomToWindow) {
        // Map to window range: 0% = startTime, 100% = endTime
        return startTime + (percent / 100) * windowDuration;
      } else {
        // Map to video duration: 0% = 0, 100% = videoDuration
        return (percent / 100) * videoDuration;
      }
    },
    [zoomToWindow, startTime, windowDuration, videoDuration]
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
        // When zoomed to window, allow slight expansion beyond current window
        // but still respect video bounds
        const minTime = zoomToWindow
          ? Math.max(0, startTime - windowDuration * 0.5)
          : 0;
        const maxTime = endTime - 0.1;
        const clampedTime = Math.max(minTime, Math.min(time, maxTime));
        onStartChange(clampedTime);
        if (onSeek) onSeek(clampedTime);
      } else if (dragging === 'end') {
        // When zoomed to window, allow slight expansion beyond current window
        // but still respect video bounds
        const minTime = startTime + 0.1;
        const maxTime = zoomToWindow
          ? Math.min(videoDuration, endTime + windowDuration * 0.5)
          : videoDuration;
        const clampedTime = Math.max(minTime, Math.min(time, maxTime));
        onEndChange(clampedTime);
        if (onSeek) onSeek(clampedTime);
      } else if (dragging === 'contact' && onContactChange) {
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
  }, [
    dragging,
    getTimeFromPosition,
    startTime,
    endTime,
    videoDuration,
    windowDuration,
    zoomToWindow,
    onStartChange,
    onEndChange,
    onContactChange,
    onSeek,
  ]);

  // Handle timeline click
  const handleTimelineClick = useCallback(
    (e: React.MouseEvent) => {
      if (dragging) return; // Don't handle clicks while dragging
      const time = getTimeFromPosition(e.clientX);

      // Determine which marker to set based on click position
      const distToStart = Math.abs(time - startTime);
      const distToEnd = Math.abs(time - endTime);
      const distToContact =
        contactTime !== null ? Math.abs(time - contactTime) : Infinity;

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
      // If clicking between start and end, set contact (if handler exists) or move nearest marker
      else {
        if (onContactChange && e.shiftKey === false) {
          // Shift+click to move start/end, regular click to set contact
          const clampedTime = Math.max(startTime, Math.min(time, endTime));
          onContactChange(clampedTime);
          if (onSeek) onSeek(clampedTime);
        } else {
          // Move the nearest marker (start or end)
          if (distToStart <= distToEnd) {
            const clampedTime = Math.max(0, Math.min(time, endTime - 0.1));
            onStartChange(clampedTime);
            if (onSeek) onSeek(clampedTime);
          } else {
            const clampedTime = Math.max(
              startTime + 0.1,
              Math.min(time, videoDuration)
            );
            onEndChange(clampedTime);
            if (onSeek) onSeek(clampedTime);
          }
        }
      }
    },
    [
      dragging,
      getTimeFromPosition,
      startTime,
      endTime,
      contactTime,
      videoDuration,
      onStartChange,
      onEndChange,
      onContactChange,
      onSeek,
    ]
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

  // Calculate hover indicator position
  const hoverPercent =
    hoverTime !== null
      ? zoomToWindow
        ? ((hoverTime - startTime) / windowDuration) * 100
        : (hoverTime / videoDuration) * 100
      : null;

  return (
    <div
      className={`timeline-markers-container ${
        density === 'compact' ? 'timeline-markers-container--compact' : ''
      }`.trim()}
    >
      {showHeader && (
        <div className="timeline-markers-header">
          <div className="timeline-markers-label">Serve</div>
          <div className="timeline-markers-values">
            <span className="timeline-value">
              START: <strong>{formatTime(startTime)}</strong>
            </span>
            <span className="timeline-value">
              END: <strong>{formatTime(endTime)}</strong>
            </span>
            {contactTime !== null && (
              <span className="timeline-value">
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
        {hoverPercent !== null && !dragging && (
          <div
            className="timeline-hover-indicator"
            style={{ left: `${hoverPercent}%` }}
          >
            <div className="timeline-hover-time">{formatTime(hoverTime!)}</div>
          </div>
        )}

        {/* Start marker */}
        <div
          className={`timeline-marker timeline-marker--start ${dragging === 'start' ? 'is-dragging' : ''}`}
          style={{ left: `${startPercent}%` }}
          onMouseDown={(e) => handleMarkerMouseDown(e, 'start')}
          title={`START: ${formatTime(startTime)}`}
        >
          <div className="timeline-marker-handle" />
          <div className="timeline-marker-label">START</div>
        </div>

        {/* End marker */}
        <div
          className={`timeline-marker timeline-marker--end ${dragging === 'end' ? 'is-dragging' : ''}`}
          style={{ left: `${endPercent}%` }}
          onMouseDown={(e) => handleMarkerMouseDown(e, 'end')}
          title={`END: ${formatTime(endTime)}`}
        >
          <div className="timeline-marker-handle" />
          <div className="timeline-marker-label">END</div>
        </div>

        {/* Contact marker */}
        {contactTime !== null && contactPercent !== null && onContactChange && (
          <div
            className={`timeline-marker timeline-marker--contact ${dragging === 'contact' ? 'is-dragging' : ''}`}
            style={{ left: `${contactPercent}%` }}
            onMouseDown={(e) => handleMarkerMouseDown(e, 'contact')}
            title={`CONTACT: ${formatTime(contactTime)}`}
          >
            <div className="timeline-marker-handle" />
            <div className="timeline-marker-label">CONTACT</div>
          </div>
        )}
      </div>

      {showActions && (
        <div className="timeline-markers-actions">
          <div className="timeline-help-text">
            {onContactChange
              ? 'Click between START/END to set contact • Shift+click to move START/END • Drag to adjust • Press C for contact'
              : 'Click to move the nearest marker • Drag to adjust'}
          </div>
        </div>
      )}
    </div>
  );
};

export default TimelineMarkers;
