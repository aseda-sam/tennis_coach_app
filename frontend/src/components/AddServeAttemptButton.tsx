import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ServeAttemptCreate } from '../services/serveAttemptApi';
import { formatTime, validateManualTimestamp } from '../utils/validation';
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
  openTimestamp?: number;
  onFormOpen?: (timestamp: number) => void;
  onFormClose?: () => void;
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
  openTimestamp,
  onFormOpen,
  onFormClose,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [lockedTimestamp, setLockedTimestamp] = useState<number | null>(null);
  const [formData, setFormData] = useState<
    ServeAttemptCreate & { contact_timestamp: number | null }
  >({
    video_id: videoId,
    start_timestamp: currentTime,
    end_timestamp: currentTime + 3, // Default 3 second window
    contact_timestamp: currentTime + 1.5, // Default contact in middle
    court_side: null,
    serve_number: null,
    serve_subtype: null,
    in_out: null,
  });

  const lastOpenRequestId = useRef<number | null>(null);

  const openAtTimestamp = useCallback(
    (timestamp: number) => {
      if (isReadOnly) {
        alert('Manual Serve Attempt Creation is disabled in Demo Mode!');
        return;
      }
      setLockedTimestamp(timestamp);
      setFormData((prev) => ({
        ...prev,
        start_timestamp: timestamp,
        end_timestamp: Math.min(timestamp + 3, videoDuration || timestamp + 3),
        contact_timestamp: timestamp + 1.5,
      }));
      setIsOpen(true);
      onFormOpen?.(timestamp);
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
    onFormClose?.();
  };

  useEffect(() => {
    if (!isOpen && lockedTimestamp === null) {
      setFormData((prev) => ({
        ...prev,
        start_timestamp: currentTime,
        end_timestamp: Math.min(currentTime + 3, videoDuration || currentTime + 3),
        contact_timestamp: currentTime + 1.5,
      }));
      setValidationError(null);
    }
  }, [currentTime, isOpen, lockedTimestamp, videoDuration]);

  useEffect(() => {
    if (!openRequestId || openTimestamp === undefined) return;
    if (openRequestId === lastOpenRequestId.current) return;

    lastOpenRequestId.current = openRequestId;
    openAtTimestamp(openTimestamp);
  }, [openRequestId, openTimestamp, openAtTimestamp]);

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
      const contactTimestamp = formData.contact_timestamp ?? null;
      const contactValidation =
        contactTimestamp !== null
          ? validateManualTimestamp(contactTimestamp, videoDuration)
          : { isValid: true };

      if (!startValidation.isValid) {
        setValidationError(startValidation.error || null);
      } else if (!endValidation.isValid) {
        setValidationError(endValidation.error || null);
      } else if (!contactValidation.isValid) {
        setValidationError(contactValidation.error || null);
      } else if (formData.start_timestamp >= formData.end_timestamp) {
        setValidationError('Start time must be before end time');
      } else if (
        contactTimestamp !== null &&
        (contactTimestamp < formData.start_timestamp ||
          contactTimestamp > formData.end_timestamp)
      ) {
        setValidationError('Contact time must be between start and end time');
      } else {
        setValidationError(null);
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
    }

    setIsLoading(true);
    try {
      await onAddServeAttempt(formData);
      handleClose();
      setFormData({
        video_id: videoId,
        start_timestamp: currentTime,
        end_timestamp: Math.min(currentTime + 3, videoDuration || currentTime + 3),
        contact_timestamp: currentTime + 1.5,
        court_side: null,
        serve_number: null,
        serve_subtype: null,
        in_out: null,
      });
    } catch (error) {
      alert('Failed to add serve attempt. Please try again.');
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

  const containerClassName = `add-contact-container ${
    placement === 'scrubber' ? 'add-contact-container--scrubber' : ''
  } ${isOpen ? 'is-open' : ''}`.trim();
  const buttonClassName = `add-contact-btn ${
    placement === 'scrubber' ? 'add-contact-btn--scrubber' : ''
  } ${isReadOnly ? 'add-contact-btn--readonly' : ''}`.trim();
  const formClassName = `add-contact-form ${
    placement === 'scrubber' ? 'add-contact-form--scrubber' : ''
  }`.trim();

  return (
    <div className={containerClassName}>
      {!isOpen ? (
        placement !== 'scrubber' && (
          <button
            className={buttonClassName}
            onClick={(e) => {
              e.stopPropagation();
              handleOpen();
            }}
            title={
              isReadOnly
                ? 'Demo mode: manual serve attempt creation is disabled'
                : `Manually add serve attempt at ${formatTime(currentTime)}`
            }
            aria-disabled={isReadOnly}
          >
            <span className="add-icon">+</span>
            <span className="add-text">Tag Serve Attempt</span>
          </button>
        )
      ) : (
        <div
          className={formClassName}
          onClick={(e) => e.stopPropagation()}
          style={formPosition}
        >
          <div className="form-header">
            <div className="timestamp-header">
              <div className="timestamp-label">Tag serve attempt:</div>
              <div className="timestamp-display">
                {formatTime(lockedTimestamp ?? 0)}
                {lockedFrameNumber !== null && (
                  <span className="frame-number"> (frame {lockedFrameNumber})</span>
                )}
              </div>
            </div>
            <button
              className="close-form-btn"
              onClick={(e) => {
                e.stopPropagation();
                handleClose();
              }}
            >
              ×
            </button>
          </div>

          <div className="form-fields">
            <div className="form-row">
              <div className="form-group form-group--compact">
                <label>Start (s)</label>
                <input
                  type="number"
                  step="0.001"
                  min="0"
                  max={videoDuration}
                  value={formData.start_timestamp.toFixed(3)}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      start_timestamp: parseFloat(e.target.value) || 0,
                    })
                  }
                />
              </div>

              <div className="form-group form-group--compact">
                <label>End (s)</label>
                <input
                  type="number"
                  step="0.001"
                  min="0"
                  max={videoDuration}
                  value={formData.end_timestamp.toFixed(3)}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      end_timestamp: parseFloat(e.target.value) || 0,
                    })
                  }
                />
              </div>

              <div className="form-group form-group--compact">
                <label>Contact (s)</label>
                <input
                  type="number"
                  step="0.001"
                  min="0"
                  max={videoDuration}
                  value={
                    formData.contact_timestamp?.toFixed(3) || ''
                  }
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      contact_timestamp:
                        e.target.value === ''
                          ? null
                          : parseFloat(e.target.value) || null,
                    })
                  }
                  placeholder="Optional"
                />
              </div>
            </div>

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
                      serve_number: e.target.value ? parseInt(e.target.value) : null,
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
            <div className="validation-error" style={{ color: 'red', padding: '8px' }}>
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
              {isLoading ? 'Adding...' : 'Add Serve Attempt'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AddServeAttemptButton;
