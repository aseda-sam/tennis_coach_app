import React, { useMemo } from 'react';
import {
  type UseVideoPlayerStateReturn,
  ZOOM_LEVELS,
  contactTimestampsQueryKey,
} from '../hooks/useVideoPlayerState';
import {
  FullscreenIcon,
  PauseIcon,
  PlayIcon,
  VolumeIcon,
  VolumeOffIcon,
} from './Icons';
import ServeWindowRange from './ServeWindowRange';
import './VideoPlayer.css';

interface VideoPlayerControlsProps {
  state: UseVideoPlayerStateReturn;
  videoId?: number;
  isDemo: boolean;
}

const VideoPlayerControls: React.FC<VideoPlayerControlsProps> = ({
  state,
  videoId,
  isDemo,
}) => {
  const {
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    zoomLevel,
    rangeInTime,
    rangeOutTime,
    highlightTimestamp,
    markedRange,
    hasRangeMarks,
    frameStep,
    formattedCurrentTime,
    formattedDuration,
    rangeInLabel,
    rangeOutLabel,
    // Handlers
    handleSeek,
    handleSeekStart,
    handleSeekEnd,
    handleVolumeChange,
    togglePlay,
    toggleMute,
    toggleFullscreen,
    zoomIn,
    zoomOut,
    resetZoom,
    seekToTime,
    clearRangeMarks,
    createServeWindowFromMarks,
    // Data
    serveWindows,
    selectedServeWindowId,
    setSelectedServeWindow,
    setSelectedServeWindowId,
    setIsModalOpen,
    updateServeWindow,
    queryClient,
  } = state;

  // Serve window containing current playback time (if any)
  const activeServeWindow = useMemo(
    () =>
      serveWindows.find(
        (sw) =>
          currentTime >= sw.start_timestamp && currentTime <= sw.end_timestamp
      ) ?? null,
    [serveWindows, currentTime]
  );

  const handleSetContact = async () => {
    if (!activeServeWindow) return;
    try {
      await updateServeWindow(activeServeWindow.id, {
        contact_timestamp: currentTime,
      });
      if (videoId) {
        queryClient.invalidateQueries({
          queryKey: contactTimestampsQueryKey(videoId),
        });
        queryClient.invalidateQueries({
          queryKey: ['biomechanics-report', activeServeWindow.id],
        });
      }
    } catch (err) {
      console.error('Failed to set contact:', err);
    }
  };

  // Prevent control buttons from stealing keyboard focus from the video
  // container. Clicks still fire normally (via mouseup/click), but focus stays
  // where it is so keyboard shortcuts remain responsive.
  const noFocusSteal = (e: React.MouseEvent) => e.preventDefault();

  return (
    <div className="video-controls">
      <div className="progress-container">
        <div className="progress-bar-wrapper">
          <input
            type="range"
            className="progress-bar"
            min="0"
            max={duration || 0}
            value={currentTime}
            onChange={handleSeek}
            onMouseDown={handleSeekStart}
            onMouseUp={handleSeekEnd}
            onTouchStart={handleSeekStart}
            onTouchEnd={handleSeekEnd}
            onKeyDown={(e) => {
              if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                handleSeekStart();
              }
            }}
            onKeyUp={(e) => {
              if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                handleSeekEnd();
              }
            }}
            step={frameStep}
          />
          {/* Serve window ranges */}
          {serveWindows.length > 0 && duration > 0 && (
            <div
              className="serve-window-ranges"
              data-tour="serve-window-ranges"
            >
              {serveWindows.map((serveWindow) => {
                const isSelected = selectedServeWindowId === serveWindow.id;

                return (
                  <ServeWindowRange
                    key={serveWindow.id}
                    serveWindow={serveWindow}
                    duration={duration}
                    currentTime={currentTime}
                    isSelected={isSelected}
                    isDemo={isDemo}
                    onClick={() => {
                      setSelectedServeWindow(serveWindow);
                      setSelectedServeWindowId(serveWindow.id);
                      setIsModalOpen(true);
                    }}
                    onContactClick={() => {
                      if (serveWindow.contact_timestamp) {
                        seekToTime(serveWindow.contact_timestamp);
                      }
                    }}
                    onMarkContact={async (timestamp) => {
                      try {
                        await updateServeWindow(serveWindow.id, {
                          contact_timestamp: timestamp,
                        });
                        if (videoId) {
                          queryClient.invalidateQueries({
                            queryKey: contactTimestampsQueryKey(videoId),
                          });
                        }
                      } catch (err) {
                        console.error('Failed to mark contact:', err);
                      }
                    }}
                  />
                );
              })}
            </div>
          )}
          {rangeInTime !== null && duration > 0 && (
            <div
              className="range-mark-marker range-mark-marker--start"
              style={{
                left: `${(rangeInTime / duration) * 100}%`,
              }}
            >
              <span>START</span>
            </div>
          )}
          {rangeOutTime !== null && duration > 0 && (
            <div
              className="range-mark-marker range-mark-marker--end"
              style={{
                left: `${(rangeOutTime / duration) * 100}%`,
              }}
            >
              <span>END</span>
            </div>
          )}
          {/* Highlight marker for locked range anchor */}
          {highlightTimestamp !== null && duration > 0 && (
            <div
              className="contact-highlight-marker"
              style={{
                left: `${(highlightTimestamp / duration) * 100}%`,
              }}
            />
          )}
        </div>
        <div className="time-display">
          <span>{formattedCurrentTime}</span>
          <span>{formattedDuration}</span>
        </div>
        {hasRangeMarks && (
          <div className="range-marked-row">
            <div className="range-marked-info">
              <span>START {rangeInLabel}</span>
              <span>END {rangeOutLabel}</span>
            </div>
            <div className="range-marked-actions">
              <button
                className="range-marked-btn"
                onClick={createServeWindowFromMarks}
                disabled={!markedRange || isDemo}
                title={
                  isDemo
                    ? 'Demo mode: range tagging is disabled'
                    : 'Create serve window from marked range'
                }
              >
                Create serve window
              </button>
              <button
                className="range-marked-btn range-marked-btn--ghost"
                onClick={clearRangeMarks}
              >
                Clear
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="controls-row">
        <div className="left-controls">
          <button
            className="control-btn play-btn"
            onClick={togglePlay}
            onMouseDown={noFocusSteal}
          >
            {isPlaying ? <PauseIcon size={20} /> : <PlayIcon size={20} />}
          </button>

          <div className="volume-control">
            <button
              className="control-btn volume-btn"
              onClick={toggleMute}
              onMouseDown={noFocusSteal}
            >
              {isMuted ? <VolumeOffIcon size={20} /> : <VolumeIcon size={20} />}
            </button>
            <input
              type="range"
              className="volume-slider"
              min="0"
              max="1"
              step="0.1"
              value={isMuted ? 0 : volume}
              onChange={handleVolumeChange}
            />
          </div>

          {/* Contact point button — only shown when inside a serve window */}
          {!isDemo && activeServeWindow && (
            <button
              className="control-btn contact-btn"
              onClick={handleSetContact}
              onMouseDown={noFocusSteal}
              title="Set ball contact at current time (C)"
            >
              <span className="contact-btn__diamond">◆</span>
              {activeServeWindow.contact_timestamp !== null
                ? activeServeWindow.contact_timestamp.toFixed(2) + 's'
                : 'Contact'}
            </button>
          )}
        </div>

        <div className="right-controls">
          {/* Zoom Controls */}
          <div className="zoom-controls-inline">
            <button
              className="control-btn"
              onClick={zoomOut}
              onMouseDown={noFocusSteal}
              disabled={zoomLevel === ZOOM_LEVELS[0]}
              title="Zoom out (-)"
            >
              −
            </button>
            <span
              className="zoom-level-display"
              onClick={resetZoom}
              title="Reset zoom (0)"
            >
              {Math.round(zoomLevel * 100)}%
            </span>
            <button
              className="control-btn"
              onClick={zoomIn}
              onMouseDown={noFocusSteal}
              disabled={zoomLevel === ZOOM_LEVELS[ZOOM_LEVELS.length - 1]}
              title="Zoom in (+)"
            >
              +
            </button>
          </div>
          <button
            className="control-btn fullscreen-btn"
            onClick={toggleFullscreen}
            onMouseDown={noFocusSteal}
          >
            <FullscreenIcon size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default VideoPlayerControls;
