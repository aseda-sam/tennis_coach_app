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
  isReadOnly?: boolean; // If true, disable creation in demo mode
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
      if (isReadOnly) {
        alert('Manual Contact Creation is disabled in Demo Mode!');
        return;
      }
      setLockedTimestamp(timestamp);
      setFormData((prev) => ({
        ...prev,
        video_timestamp: timestamp,
      }));
      setIsOpen(true);
      onFormOpen?.(timestamp);
    },
    [isReadOnly, onFormOpen]
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
      alert('Failed to manually add contact. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Calculate frame number from timestamp
  const getFrameNumber = (timestamp: number): number | null => {
    if (fps && fps > 0) {
      return Math.floor(timestamp * fps);
    }
    return null;
  };

  const lockedFrameNumber = lockedTimestamp !== null ? getFrameNumber(lockedTimestamp) : null;

  // Calculate position for scrubber placement
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
                ? 'Demo mode: manual contact creation is disabled'
                : `Manually add contact at ${formatTime(currentTime)}`
            }
            aria-disabled={isReadOnly}
          >
            <span className="add-icon">+</span>
            <span className="add-text">Manually Add Contact</span>
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
              <div className="timestamp-label">Manually add contact at:</div>
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
                <label>Hand</label>
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

              <div className="form-group form-group--compact">
                <label>Stroke</label>
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
                  <option value="">Type</option>
                  {Object.entries(STROKE_TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              {formData.stroke_type && (
                <div className="form-group form-group--compact">
                  <label>Subtype</label>
                  <select
                    value={formData.stroke_subtype || ''}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        stroke_subtype: e.target.value || undefined,
                      })
                    }
                  >
                    <option value="">Optional</option>
                    {getSubtypesForType(formData.stroke_type).map((subtype) => (
                      <option key={subtype} value={subtype}>
                        {STROKE_SUBTYPE_LABELS[subtype] || subtype}
                      </option>
                    ))}
                  </select>
                </div>
              )}
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
              {isLoading ? 'Adding...' : 'Add Manual'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default AddContactButton;
