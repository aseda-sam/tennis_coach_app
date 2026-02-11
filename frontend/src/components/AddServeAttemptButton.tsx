import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ServeAttemptCreate } from '../services/serveAttemptApi';
import {
  formatTime,
  validateContactTimestamp,
  validateManualTimestamp,
} from '../utils/validation';
import TimelineMarkers from './TimelineMarkers';
import './AddContactButton.css'; // Reuse styles

interface AddServeAttemptButtonProps {
  currentTime: number;
  videoId: number;
  videoDuration: number;
  fps?: number;
  onAddServeAttempt: (serveAttempt: ServeAttemptCreate) => Promise<void>;
  isVisible: boolean;
  isReadOnly?: boolean;
  placement?: 'overlay' | 'scrubber';
  openRequestId?: number;
  openRange?: { start: number; end: number };
  onFormOpen?: (timestamp: number) => void;
  onFormClose?: () => void;
  onSeek?: (time: number) => void;
}

const AddServeAttemptButton: React.FC<AddServeAttemptButtonProps> = ({
  currentTime,
  videoId,
  videoDuration,
  fps,
  onAddServeAttempt,
  isVisible,
  isReadOnly = false,
  placement = 'overlay',
  openRequestId,
  openRange,
  onFormOpen,
  onFormClose,
  onSeek,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [lockedTimestamp, setLockedTimestamp] = useState<number | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [formData, setFormData] = useState<ServeAttemptCreate>({
    video_id: videoId,
    start_timestamp: currentTime,
    end_timestamp: currentTime + 3, // Default 3 second window
    contact_timestamp: null,
    court_side: null,
    serve_number: null,
    serve_subtype: null,
    in_out: null,
  });

  const lastOpenRequestId = useRef<number | null>(null);

  const openAtTimestamp = useCallback(
    (timestamp: number) => {
      if (isReadOnly) {
        alert('Manual serve creation is disabled in Demo Mode!');
        return;
      }
      setLockedTimestamp(timestamp);
      setShowAdvanced(false);
      setFormData((prev) => ({
        ...prev,
        start_timestamp: timestamp,
        end_timestamp: Math.min(timestamp + 3, videoDuration || timestamp + 3),
        contact_timestamp: null,
      }));
      setIsOpen(true);
      onFormOpen?.(timestamp);
    },
    [isReadOnly, onFormOpen, videoDuration]
  );

  const openAtRange = useCallback(
    (rangeStart: number, rangeEnd: number) => {
      if (isReadOnly) {
        alert('Manual serve creation is disabled in Demo Mode!');
        return;
      }

      const start = Math.max(0, Math.min(rangeStart, rangeEnd));
      const end = Math.min(
        videoDuration || rangeEnd,
        Math.max(rangeStart, rangeEnd)
      );
      const clampedEnd = Math.max(start + 0.1, end);

      setLockedTimestamp(start);
      setShowAdvanced(false);
      setFormData((prev) => ({
        ...prev,
        start_timestamp: start,
        end_timestamp: clampedEnd,
        contact_timestamp: null,
      }));
      setIsOpen(true);
      onFormOpen?.(start);
    },
    [isReadOnly, onFormOpen, videoDuration]
  );

  const handleOpen = () => {
    openAtTimestamp(currentTime);
  };

  const handleClose = () => {
    setIsOpen(false);
    setLockedTimestamp(null);
    setValidationError(null);
    setShowAdvanced(false);
    onFormClose?.();
  };

  useEffect(() => {
    if (!isOpen && lockedTimestamp === null) {
      setFormData((prev) => ({
        ...prev,
        start_timestamp: currentTime,
        end_timestamp: Math.min(
          currentTime + 3,
          videoDuration || currentTime + 3
        ),
        contact_timestamp: null,
      }));
      setValidationError(null);
    }
  }, [currentTime, isOpen, lockedTimestamp, videoDuration]);

  useEffect(() => {
    if (!openRequestId) return;
    if (openRequestId === lastOpenRequestId.current) return;

    lastOpenRequestId.current = openRequestId;

    if (openRange) {
      openAtRange(openRange.start, openRange.end);
    }
  }, [openRequestId, openRange, openAtRange]);

  // Keyboard shortcut for contact timestamp (C key)
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't handle if typing in an input field
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement ||
        event.target instanceof HTMLSelectElement
      ) {
        return;
      }

      if (event.key === 'c' || event.key === 'C') {
        event.preventDefault();
        // Set contact timestamp to current time, clamped to serve attempt range
        setFormData((prev) => {
          const clampedTime = Math.max(
            prev.start_timestamp,
            Math.min(currentTime, prev.end_timestamp)
          );
          if (onSeek) onSeek(clampedTime);
          return {
            ...prev,
            contact_timestamp: clampedTime,
          };
        });
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    isOpen,
    formData.start_timestamp,
    formData.end_timestamp,
    currentTime,
    onSeek,
  ]);

  useEffect(() => {
    if (videoDuration > 0) {
      const startValidation = validateManualTimestamp(
        formData.start_timestamp,
        videoDuration
      );
      const endValidation = validateManualTimestamp(
        formData.end_timestamp,
        videoDuration
      );
      if (!startValidation.isValid) {
        setValidationError(startValidation.error || null);
      } else if (!endValidation.isValid) {
        setValidationError(endValidation.error || null);
      } else if (formData.start_timestamp >= formData.end_timestamp) {
        setValidationError('Start time must be before end time');
      } else {
        const contactValidation = validateContactTimestamp(
          formData.contact_timestamp ?? null,
          formData.start_timestamp,
          formData.end_timestamp,
          videoDuration
        );
        if (!contactValidation.isValid) {
          setValidationError(contactValidation.error || null);
        } else {
          setValidationError(null);
        }
      }
    }
  }, [formData, videoDuration]);

  const handleAddServeAttempt = async () => {
    if (videoDuration > 0) {
      const startValidation = validateManualTimestamp(
        formData.start_timestamp,
        videoDuration
      );
      const endValidation = validateManualTimestamp(
        formData.end_timestamp,
        videoDuration
      );
      if (!startValidation.isValid || !endValidation.isValid) {
        setValidationError(
          startValidation.error || endValidation.error || 'Invalid timestamp'
        );
        return;
      }

      if (formData.start_timestamp >= formData.end_timestamp) {
        setValidationError('Start time must be before end time');
        return;
      }

      const contactValidation = validateContactTimestamp(
        formData.contact_timestamp ?? null,
        formData.start_timestamp,
        formData.end_timestamp,
        videoDuration
      );
      if (!contactValidation.isValid) {
        setValidationError(contactValidation.error || 'Invalid timestamp');
        return;
      }
    }

    setIsLoading(true);
    try {
      await onAddServeAttempt(formData);
      handleClose();
      setFormData({
        video_id: videoId,
        start_timestamp: currentTime,
        end_timestamp: Math.min(
          currentTime + 3,
          videoDuration || currentTime + 3
        ),
        contact_timestamp: null,
        court_side: null,
        serve_number: null,
        serve_subtype: null,
        in_out: null,
      });
    } catch (error) {
      alert('Failed to add serve. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const getFrameNumber = (timestamp: number): number | null => {
    if (fps && fps > 0) {
      return Math.floor(timestamp * fps);
    }
    return null;
  };

  const lockedFrameNumber =
    lockedTimestamp !== null ? getFrameNumber(lockedTimestamp) : null;

  const formPosition =
    placement === 'scrubber' && lockedTimestamp !== null && videoDuration > 0
      ? {
          left: `${(lockedTimestamp / videoDuration) * 100}%`,
        }
      : undefined;

  if (!isVisible) return null;

  const supportsCompact = placement === 'overlay';
  const isCompact = supportsCompact && !showAdvanced;
  const isAdvancedPanel = supportsCompact && showAdvanced;
  const containerClassName = `add-contact-container ${
    placement === 'scrubber' ? 'add-contact-container--scrubber' : ''
  } ${placement === 'overlay' ? 'add-contact-container--overlay' : ''} ${
    isOpen ? 'is-open' : ''
  }`.trim();
  const buttonClassName = `add-contact-btn ${
    placement === 'scrubber' ? 'add-contact-btn--scrubber' : ''
  } ${isReadOnly ? 'add-contact-btn--readonly' : ''}`.trim();
  const isOverlayPlacement = placement === 'overlay';
  const formClassName = `add-contact-form ${
    placement === 'scrubber' ? 'add-contact-form--scrubber' : ''
  } ${isCompact ? 'add-contact-form--compact' : ''} ${
    isAdvancedPanel ? 'add-contact-form--advanced' : ''
  }`.trim();

  const formContent = (
    <div
      className={formClassName}
      onClick={(e) => e.stopPropagation()}
      style={isOverlayPlacement ? undefined : formPosition}
    >
      {isCompact ? (
        <>
          <div className="compact-form-header">
            <div className="compact-form-title">Create Serve</div>
            <button
              className="close-form-btn"
              onClick={(e) => {
                e.stopPropagation();
                handleClose();
              }}
              aria-label="Close"
            >
              ×
            </button>
          </div>
          <div className="compact-range-row">
            <span className="compact-range-label">Range</span>
            <span className="compact-range-values">
              {formatTime(formData.start_timestamp)} –{' '}
              {formatTime(formData.end_timestamp)}
            </span>
          </div>

          <TimelineMarkers
            startTime={formData.start_timestamp}
            endTime={formData.end_timestamp}
            videoDuration={videoDuration}
            currentTime={currentTime}
            onStartChange={(time) =>
              setFormData({
                ...formData,
                start_timestamp: time,
              })
            }
            onEndChange={(time) =>
              setFormData({
                ...formData,
                end_timestamp: time,
              })
            }
            onSeek={onSeek}
            density="compact"
            showHeader={false}
            showActions={false}
          />

          <div className="compact-actions">
            <div className="compact-actions-right">
              <button
                className="compact-btn compact-btn--secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClose();
                }}
                disabled={isLoading}
              >
                Cancel
              </button>
              <button
                className="compact-btn compact-btn--primary"
                onClick={(e) => {
                  e.stopPropagation();
                  handleAddServeAttempt();
                }}
                disabled={isLoading || !!validationError}
              >
                {isLoading ? 'Creating...' : 'Create'}
              </button>
              <button
                className="compact-btn compact-btn--details"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowAdvanced(true);
                }}
              >
                Details
              </button>
            </div>
          </div>

          {validationError && (
            <div className="validation-error validation-error--compact">
              {validationError}
            </div>
          )}
        </>
      ) : (
        <>
          <div className="form-header">
            <div className="timestamp-header">
              <div className="timestamp-label">Serve</div>
              <div className="timestamp-display">
                {formatTime(formData.start_timestamp)} –{' '}
                {formatTime(formData.end_timestamp)}
                {lockedFrameNumber !== null && (
                  <span className="frame-number">
                    {' '}
                    (frame {lockedFrameNumber})
                  </span>
                )}
              </div>
            </div>
            <div className="form-header-actions">
              {supportsCompact && (
                <button
                  className="compact-toggle-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowAdvanced(false);
                  }}
                >
                  Range only
                </button>
              )}
              <button
                className="close-form-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClose();
                }}
                aria-label="Close"
              >
                ×
              </button>
            </div>
          </div>

          <div className="form-fields">
            <TimelineMarkers
              startTime={formData.start_timestamp}
              endTime={formData.end_timestamp}
              contactTime={formData.contact_timestamp}
              onContactChange={(time) =>
                setFormData({
                  ...formData,
                  contact_timestamp: time,
                })
              }
              videoDuration={videoDuration}
              currentTime={currentTime}
              onStartChange={(time) =>
                setFormData({
                  ...formData,
                  start_timestamp: time,
                })
              }
              onEndChange={(time) =>
                setFormData({
                  ...formData,
                  end_timestamp: time,
                })
              }
              onSeek={onSeek}
            />

            {formData.contact_timestamp != null && (
              <div className="form-group">
                <label>Contact Timestamp</label>
                <div className="timestamp-display-readonly">
                  {formatTime(formData.contact_timestamp as number)}
                  <button
                    className="use-current-time-btn"
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFormData({
                        ...formData,
                        contact_timestamp: null,
                      });
                    }}
                  >
                    Clear
                  </button>
                </div>
              </div>
            )}

            <div className="form-row">
              <div className="form-group form-group--compact">
                <label>Court Side</label>
                <select
                  value={formData.court_side || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      court_side: e.target.value || null,
                    })
                  }
                >
                  <option value="">Optional</option>
                  <option value="deuce">Deuce</option>
                  <option value="ad">Ad</option>
                </select>
              </div>
              <div className="form-group form-group--compact">
                <label>Serve #</label>
                <select
                  value={formData.serve_number || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      serve_number: e.target.value
                        ? parseInt(e.target.value)
                        : null,
                    })
                  }
                >
                  <option value="">Optional</option>
                  <option value="1">1</option>
                  <option value="2">2</option>
                </select>
              </div>

              <div className="form-group form-group--compact">
                <label>Type</label>
                <select
                  value={formData.serve_subtype || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      serve_subtype: e.target.value || null,
                    })
                  }
                >
                  <option value="">Optional</option>
                  <option value="flat">Flat</option>
                  <option value="slice">Slice</option>
                  <option value="kick">Kick</option>
                </select>
              </div>

              <div className="form-group form-group--compact">
                <label>In/Out</label>
                <select
                  value={formData.in_out || ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      in_out: e.target.value || null,
                    })
                  }
                >
                  <option value="">Optional</option>
                  <option value="in">In</option>
                  <option value="out_long">Out (Long)</option>
                  <option value="out_wide">Out (Wide)</option>
                  <option value="net">Net</option>
                  <option value="unknown">Unknown</option>
                </select>
              </div>
            </div>
          </div>

          {validationError && (
            <div
              className="validation-error"
              style={{ color: 'red', padding: '8px' }}
            >
              {validationError}
            </div>
          )}

          <div className="form-actions">
            <button
              className="btn btn-secondary"
              onClick={(e) => {
                e.stopPropagation();
                handleClose();
              }}
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              className="btn btn-primary"
              onClick={(e) => {
                e.stopPropagation();
                handleAddServeAttempt();
              }}
              disabled={isLoading || !!validationError}
            >
              {isLoading ? 'Creating...' : 'Create Serve'}
            </button>
          </div>
        </>
      )}
    </div>
  );

  return (
    <div className={containerClassName}>
      {!isOpen
        ? placement !== 'scrubber' && (
            <button
              className={buttonClassName}
              onClick={(e) => {
                e.stopPropagation();
                handleOpen();
              }}
              title={
                isReadOnly
                  ? 'Demo mode: manual serve attempt creation is disabled'
                  : `Tag serve near ${formatTime(currentTime)}`
              }
              aria-disabled={isReadOnly}
            >
              <span className="add-icon">+</span>
              <span className="add-text">Tag Serve</span>
            </button>
          )
        : createPortal(
            <div className="serve-attempt-modal-backdrop" onClick={handleClose}>
              <div
                className="serve-attempt-modal-container"
                onClick={(e) => e.stopPropagation()}
              >
                {formContent}
              </div>
            </div>,
            document.body
          )}
    </div>
  );
};

export default AddServeAttemptButton;
