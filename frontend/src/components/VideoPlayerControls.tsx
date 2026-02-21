import React from 'react';
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
import ProposalRange from './ProposalRange';
import ServeWindowRange from './ServeWindowRange';
import './VideoPlayer.css';

interface VideoPlayerControlsProps {
  state: UseVideoPlayerStateReturn;
  videoId?: number;
  isDemo: boolean;
  lowConfidenceThreshold: number;
}

const VideoPlayerControls: React.FC<VideoPlayerControlsProps> = ({
  state,
  videoId,
  isDemo,
  lowConfidenceThreshold,
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
    proposals,
    selectedServeWindowId,
    setSelectedServeWindow,
    setSelectedServeWindowId,
    setIsModalOpen,
    updateServeWindow,
    acceptProposal,
    rejectProposal,
    editProposal,
    queryClient,
  } = state;

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
          {/* Proposal ranges (shown before serve windows) */}
          {proposals.length > 0 && duration > 0 && (
            <div className="proposal-ranges">
              {proposals.map((proposal) => (
                <ProposalRange
                  key={proposal.id}
                  proposal={proposal}
                  duration={duration}
                  lowConfidenceThreshold={lowConfidenceThreshold}
                  onClick={() => {
                    seekToTime(proposal.start_timestamp);
                  }}
                  onAccept={async () => {
                    try {
                      await acceptProposal(proposal.id);
                    } catch (err) {
                      console.error('Failed to accept proposal:', err);
                      alert('Failed to accept proposal');
                    }
                  }}
                  onReject={async () => {
                    try {
                      await rejectProposal(proposal.id);
                    } catch (err) {
                      console.error('Failed to reject proposal:', err);
                      alert('Failed to reject proposal');
                    }
                  }}
                  onEdit={async () => {
                    try {
                      await editProposal(proposal.id, {
                        start_timestamp: proposal.start_timestamp,
                        end_timestamp: proposal.end_timestamp,
                      });
                    } catch (err) {
                      console.error('Failed to edit proposal:', err);
                      alert('Failed to edit proposal');
                    }
                  }}
                />
              ))}
            </div>
          )}
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
          <button className="control-btn play-btn" onClick={togglePlay}>
            {isPlaying ? <PauseIcon size={20} /> : <PlayIcon size={20} />}
          </button>

          <div className="volume-control">
            <button className="control-btn volume-btn" onClick={toggleMute}>
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
        </div>

        <div className="right-controls">
          {/* Zoom Controls */}
          <div className="zoom-controls-inline">
            <button
              className="control-btn"
              onClick={zoomOut}
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
              disabled={zoomLevel === ZOOM_LEVELS[ZOOM_LEVELS.length - 1]}
              title="Zoom in (+)"
            >
              +
            </button>
          </div>
          <button
            className="control-btn fullscreen-btn"
            onClick={toggleFullscreen}
          >
            <FullscreenIcon size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default VideoPlayerControls;
