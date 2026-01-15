import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  STROKE_SUBTYPE_LABELS,
  STROKE_TYPE_LABELS,
  getSubtypesForType,
  type StrokeType,
} from '../constants/shotTypes';
import { BallContactCreate } from '../services/ballContactApi';
import { formatTime, validateManualTimestamp } from '../utils/validation';
import './AddContactButton.css';

interface AddContactButtonProps {
  currentTime: number;
  videoId: number;
  videoDuration: number;
  fps?: number; // FPS for frame number calculation
  onAddContact: (contact: BallContactCreate) => Promise<void>;
  isVisible: boolean;
  placement?: 'overlay' | 'scrubber';
  openRequestId?: number;
  openTimestamp?: number;
  onFormOpen?: (timestamp: number) => void; // Callback when form opens
  onFormClose?: () => void; // Callback when form closes
}

const AddContactButton: React.FC<AddContactButtonProps> = ({
  currentTime,
  videoId,
  videoDuration,
  fps,
  onAddContact,
  isVisible,
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
  const [formData, setFormData] = useState<BallContactCreate>({
    video_id: videoId,
    video_timestamp: currentTime,
    contact_hand: 'right',
    stroke_type: 'ground_stroke',
    stroke_subtype: '',
    detection_source: 'manual',
  });

  const lastOpenRequestId = useRef<number | null>(null);

  const openAtTimestamp = useCallback(
    (timestamp: number) => {
      setLockedTimestamp(timestamp);
      setFormData((prev) => ({
        ...prev,
        video_timestamp: timestamp,
      }));
      setIsOpen(true);
      onFormOpen?.(timestamp);
    },
    [onFormOpen]
  );

  // Lock timestamp when form opens
  const handleOpen = () => {
    openAtTimestamp(currentTime);
  };

  // Unlock timestamp when form closes
  const handleClose = () => {
    setIsOpen(false);
    setLockedTimestamp(null);
    setValidationError(null);
    onFormClose?.();
  };

  // Update video_timestamp only when form is closed (not locked)
  useEffect(() => {
    if (!isOpen && lockedTimestamp === null) {
      setFormData((prev) => ({
        ...prev,
        video_timestamp: currentTime,
      }));
      setValidationError(null);
    }
  }, [currentTime, isOpen, lockedTimestamp]);

  useEffect(() => {
    if (!openRequestId || openTimestamp === undefined) return;
    if (openRequestId === lastOpenRequestId.current) return;

    lastOpenRequestId.current = openRequestId;
    openAtTimestamp(openTimestamp);
  }, [openRequestId, openTimestamp, openAtTimestamp]);

  // Validate timestamp whenever form data changes
  useEffect(() => {
    if (videoDuration > 0) {
      const validation = validateManualTimestamp(
        formData.video_timestamp,
        videoDuration
      );
      setValidationError(validation.isValid ? null : validation.error || null);
    }
  }, [formData.video_timestamp, videoDuration]);

  const handleAddContact = async () => {
    // Validate before submitting
    if (videoDuration > 0) {
      const validation = validateManualTimestamp(
        formData.video_timestamp,
        videoDuration
      );
      if (!validation.isValid) {
        setValidationError(validation.error || 'Invalid timestamp');
        return;
      }
    }

    setIsLoading(true);
    try {
      await onAddContact(formData);
      handleClose();
      setFormData({
        video_id: videoId,
        video_timestamp: currentTime,
        contact_hand: 'right',
        stroke_type: 'ground_stroke',
        stroke_subtype: undefined,
        detection_source: 'manual',
      });
    } catch (error) {
      // Error is shown to user via alert
      alert('Failed to add contact. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUseCurrentTime = () => {
    const newTimestamp = currentTime;
    setLockedTimestamp(newTimestamp);
    setFormData((prev) => ({
      ...prev,
      video_timestamp: newTimestamp,
    }));
    setValidationError(null);
  };

  // Calculate frame number from timestamp
  const getFrameNumber = (timestamp: number): number | null => {
    if (fps && fps > 0) {
      return Math.floor(timestamp * fps);
    }
    return null;
  };

  const lockedFrameNumber = lockedTimestamp !== null ? getFrameNumber(lockedTimestamp) : null;

  const handleTimestampChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTimestamp = parseFloat(e.target.value) || 0;
    setFormData({
      ...formData,
      video_timestamp: newTimestamp,
    });
  };

  if (!isVisible) return null;

  const containerClassName = `add-contact-container ${
    placement === 'scrubber' ? 'add-contact-container--scrubber' : ''
  } ${isOpen ? 'is-open' : ''}`.trim();
  const buttonClassName = `add-contact-btn ${
    placement === 'scrubber' ? 'add-contact-btn--scrubber' : ''
  }`.trim();
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
            title={`Add ball contact at ${formatTime(currentTime)}`}
          >
            <span className="add-icon">+</span>
            <span className="add-text">Add Contact</span>
          </button>
        )
      ) : (
        <div className={formClassName} onClick={(e) => e.stopPropagation()}>
          <div className="form-header">
            <div className="timestamp-header">
              <div className="timestamp-label">Add contact at:</div>
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
            <div className="form-group">
              <label>Timestamp (seconds):</label>
              <div className="timestamp-input-group">
                <input
                  type="number"
                  step={fps && fps > 0 ? 1 / fps : 0.1}
                  min="0"
                  max={videoDuration > 0 ? videoDuration : undefined}
                  value={formData.video_timestamp}
                  onChange={handleTimestampChange}
                  className={validationError ? 'error' : ''}
                />
                <button
                  type="button"
                  className="use-current-time-btn"
                  onClick={handleUseCurrentTime}
                  title={`Use current time: ${formatTime(currentTime)}`}
                >
                  Use current time
                </button>
              </div>
              {validationError && (
                <div className="validation-error">{validationError}</div>
              )}
              {videoDuration > 0 && (
                <div className="timestamp-info">
                  Video duration: {formatTime(videoDuration)}
                  {fps && fps > 0 && ` • ${fps.toFixed(1)} fps`}
                </div>
              )}
            </div>

            <div className="form-group">
              <label>Contact Hand:</label>
              <select
                value={formData.contact_hand}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    contact_hand: e.target.value as 'left' | 'right',
                  })
                }
              >
                <option value="right">Right</option>
                <option value="left">Left</option>
              </select>
            </div>

            <div className="form-group">
              <label>Stroke Type:</label>
              <select
                value={formData.stroke_type || ''}
                onChange={(e) => {
                  const newStrokeType = e.target.value as
                    | StrokeType
                    | undefined;
                  const allowedSubtypes = getSubtypesForType(newStrokeType);
                  setFormData({
                    ...formData,
                    stroke_type: newStrokeType || undefined,
                    stroke_subtype: allowedSubtypes.includes(
                      formData.stroke_subtype || ''
                    )
                      ? formData.stroke_subtype
                      : undefined,
                  });
                }}
              >
                <option value="">Select stroke type</option>
                {Object.entries(STROKE_TYPE_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Stroke Subtype:</label>
              <select
                value={formData.stroke_subtype || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    stroke_subtype: e.target.value || undefined,
                  })
                }
                disabled={!formData.stroke_type}
              >
                <option value="">Select subtype (optional)</option>
                {getSubtypesForType(formData.stroke_type).map((subtype) => (
                  <option key={subtype} value={subtype}>
                    {STROKE_SUBTYPE_LABELS[subtype] || subtype}
                  </option>
                ))}
              </select>
            </div>
          </div>

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
                handleAddContact();
              }}
              disabled={isLoading || !!validationError}
            >
              {isLoading ? 'Adding...' : 'Add Contact'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AddContactButton;
