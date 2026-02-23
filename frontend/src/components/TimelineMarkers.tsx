import React from 'react';
import { useTimelineDrag } from '../hooks/useTimelineDrag';
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
  // When zoomed to window, calculate relative to the window range
  const windowDuration = endTime - startTime;

  const {
    timelineRef,
    dragging,
    hoverTime,
    handleMarkerMouseDown,
    handleTimelineClick,
    handleTimelineMouseMove,
    handleTimelineMouseLeave,
  } = useTimelineDrag({
    startTime,
    endTime,
    videoDuration,
    windowDuration,
    zoomToWindow,
    contactTime,
    onStartChange,
    onEndChange,
    onContactChange,
    onSeek,
  });

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
