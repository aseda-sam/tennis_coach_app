import React from 'react';
import {
  type UseVideoPlayerStateReturn,
  contactTimestampsQueryKey,
} from '../hooks/useVideoPlayerState';
import type { ServeWindowCreate } from '../types/serveWindow';
import AddServeWindowButton from './AddServeWindowButton';
import { ArrowBackIcon, PauseIcon, PlayIcon } from './Icons';
import ProposalRange from './ProposalRange';
import ServeWindowModal from './ServeWindowModal';
import ServeWindowRange from './ServeWindowRange';
import './VideoPlayer.css';

interface VideoPlayerTimelineProps {
  state: UseVideoPlayerStateReturn;
  videoId?: number;
  isDemo: boolean;
  lowConfidenceThreshold: number;
}

const VideoPlayerTimeline: React.FC<VideoPlayerTimelineProps> = ({
  state,
  videoId,
  isDemo,
  lowConfidenceThreshold,
}) => {
  const {
    isPlaying,
    currentTime,
    duration,
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
    openRange,
    openRequestId,
    isAddServeWindowVisible,
    // Handlers
    handleSeek,
    handleSeekStart,
    handleSeekEnd,
    togglePlay,
    seekToTime,
    clearRangeMarks,
    createServeWindowFromMarks,
    navigateToPreviousServeWindow,
    navigateToNextServeWindow,
    navigateToPreviousContact,
    navigateToNextContact,
    hasPreviousServeWindow,
    hasNextServeWindow,
    hasPreviousContact,
    hasNextContact,
    hasAnyContact,
    // Refs
    scrubberTrackRef,
    videoRef,
    wasPlayingRef,
    // Data
    serveWindows,
    proposals,
    selectedServeWindow,
    selectedServeWindowId,
    setSelectedServeWindow,
    setSelectedServeWindowId,
    isModalOpen,
    setIsModalOpen,
    updateServeWindow,
    deleteServeWindow,
    createServeWindow,
    acceptProposal,
    rejectProposal,
    editProposal,
    queryClient,
    setHighlightTimestamp,
    setOpenRange,
    videoMetadata,
  } = state;

  return (
    <div className="video-controls-below">
      {/* Video Scrubber */}
      <div className="video-controls-below__scrubber">
        <div
          className="video-controls-below__scrubber-track"
          ref={scrubberTrackRef}
        >
          <AddServeWindowButton
            currentTime={currentTime}
            videoId={videoId || 0}
            videoDuration={duration}
            fps={videoMetadata?.fps}
            onAddServeWindow={async (serveWindow: ServeWindowCreate) => {
              await createServeWindow(serveWindow);
              if (videoId) {
                queryClient.invalidateQueries({
                  queryKey: contactTimestampsQueryKey(videoId),
                });
              }
              if (openRange) {
                clearRangeMarks();
              }
            }}
            isVisible={isAddServeWindowVisible}
            isReadOnly={isDemo}
            placement="scrubber"
            onSeek={seekToTime}
            openRequestId={openRequestId}
            openRange={openRange ?? undefined}
            onFormOpen={(timestamp) => {
              // Pause video if playing
              const video = videoRef.current;
              if (video && isPlaying) {
                video.pause();
                wasPlayingRef.current = true;
              } else {
                wasPlayingRef.current = false;
              }
              // Set highlight timestamp
              setHighlightTimestamp(timestamp);
            }}
            onFormClose={() => {
              // Clear highlight
              setHighlightTimestamp(null);
              setOpenRange(null);
              // Note: We don't auto-resume playback - user can manually play
              wasPlayingRef.current = false;
            }}
          />
          <input
            type="range"
            className="video-controls-below__scrubber-input"
            min="0"
            max={duration || 0}
            value={currentTime}
            onChange={handleSeek}
            onMouseDown={handleSeekStart}
            onMouseUp={handleSeekEnd}
            onTouchStart={handleSeekStart}
            onTouchEnd={handleSeekEnd}
            step={frameStep}
          />
          {/* Proposal ranges (shown before serve windows) */}
          {proposals.length > 0 && duration > 0 && (
            <div className="video-controls-below__proposal-ranges">
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
              className="video-controls-below__serve-window-ranges"
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
        <div className="video-controls-below__time-labels">
          <span>{formattedCurrentTime}</span>
          <span>{formattedDuration}</span>
        </div>
        {hasRangeMarks && (
          <div className="range-marked-row range-marked-row--below">
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

      {/* Navigation: Contact (when any) | Serve | Play | Serve | Contact */}
      <div className="video-controls-below__nav">
        {hasAnyContact && (
          <button
            className="video-controls-below__contact-btn"
            disabled={!hasPreviousContact}
            onClick={navigateToPreviousContact}
            title={
              hasPreviousContact
                ? 'Go to previous contact'
                : 'No previous contact'
            }
          >
            <ArrowBackIcon size={18} />
            <span className="video-controls-below__contact-icon">&#x25C9;</span>
            <span>Previous Contact</span>
          </button>
        )}
        <button
          className="video-controls-below__nav-btn"
          disabled={!hasPreviousServeWindow}
          onClick={navigateToPreviousServeWindow}
          title={
            hasPreviousServeWindow
              ? 'Go to previous serve'
              : 'No previous serve'
          }
        >
          <ArrowBackIcon size={18} />
          <span>Previous Serve</span>
        </button>
        <button
          className="video-controls-below__play-btn"
          onClick={togglePlay}
          title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
        >
          {isPlaying ? <PauseIcon size={24} /> : <PlayIcon size={24} />}
        </button>
        <button
          className="video-controls-below__nav-btn video-controls-below__nav-btn--next"
          disabled={!hasNextServeWindow}
          onClick={navigateToNextServeWindow}
          title={hasNextServeWindow ? 'Go to next serve' : 'No next serve'}
        >
          <span>Next Serve</span>
          <ArrowBackIcon size={18} />
        </button>
        {hasAnyContact && (
          <button
            className="video-controls-below__contact-btn video-controls-below__contact-btn--next"
            disabled={!hasNextContact}
            onClick={navigateToNextContact}
            title={hasNextContact ? 'Go to next contact' : 'No next contact'}
          >
            <span>Next Contact</span>
            <span className="video-controls-below__contact-icon">&#x25C9;</span>
            <ArrowBackIcon size={18} />
          </button>
        )}
      </div>

      {/* Serve Detail Panel (inline, non-blocking) */}
      {isModalOpen && selectedServeWindow && (
        <div className="video-controls-below__serve-panel">
          <ServeWindowModal
            serveWindow={selectedServeWindow}
            isOpen={isModalOpen}
            videoDuration={duration}
            currentTime={currentTime}
            isDemo={isDemo}
            mode="panel"
            onClose={() => {
              setIsModalOpen(false);
              setSelectedServeWindow(null);
              setSelectedServeWindowId(undefined);
            }}
            onUpdate={async (serveWindowId, updates) => {
              await updateServeWindow(serveWindowId, updates);
              if (videoId && updates.contact_timestamp !== undefined) {
                queryClient.invalidateQueries({
                  queryKey: contactTimestampsQueryKey(videoId),
                });
              }
            }}
            onDelete={async (serveWindowId) => {
              await deleteServeWindow(serveWindowId);
              if (videoId) {
                queryClient.invalidateQueries({
                  queryKey: contactTimestampsQueryKey(videoId),
                });
              }
            }}
            onSeek={seekToTime}
          />
        </div>
      )}
    </div>
  );
};

export default VideoPlayerTimeline;
