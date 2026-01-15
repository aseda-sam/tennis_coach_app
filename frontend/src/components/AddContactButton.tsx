import React, { useEffect, useState } from 'react';
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
  videoDuration: number; // Add video duration prop
  onAddContact: (contact: BallContactCreate) => Promise<void>;
  isVisible: boolean;
}

const AddContactButton: React.FC<AddContactButtonProps> = ({
  currentTime,
  videoId,
  videoDuration,
  onAddContact,
  isVisible,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [formData, setFormData] = useState<BallContactCreate>({
    video_id: videoId,
    video_timestamp: currentTime,
    contact_hand: 'right',
    stroke_type: 'ground_stroke',
    stroke_subtype: '',
    detection_source: 'manual',
  });

  // Update video_timestamp when currentTime changes
  useEffect(() => {
    setFormData((prev) => ({
      ...prev,
      video_timestamp: currentTime,
    }));
    // Clear validation error when current time changes
    setValidationError(null);
  }, [currentTime]);

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
      setIsOpen(false);
      setFormData({
        video_id: videoId,
        video_timestamp: currentTime,
        contact_hand: 'right',
        stroke_type: 'ground_stroke',
        stroke_subtype: undefined,
        detection_source: 'manual',
      });
      setValidationError(null);
    } catch (error) {
      // Error is shown to user via alert
      alert('Failed to add contact. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTimestampChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTimestamp = parseFloat(e.target.value) || 0;
    setFormData({
      ...formData,
      video_timestamp: newTimestamp,
    });
  };

  if (!isVisible) return null;

  return (
    <div className="add-contact-container">
      {!isOpen ? (
        <button
          className="add-contact-btn"
          onClick={(e) => {
            e.stopPropagation();
            setIsOpen(true);
          }}
          title={`Add ball contact at ${formatTime(currentTime)}`}
        >
          <span className="add-icon">+</span>
          <span className="add-text">Add Contact</span>
        </button>
      ) : (
        <div className="add-contact-form" onClick={(e) => e.stopPropagation()}>
          <div className="form-header">
            <span className="timestamp-display">{formatTime(currentTime)}</span>
            <button
              className="close-form-btn"
              onClick={(e) => {
                e.stopPropagation();
                setIsOpen(false);
                setValidationError(null);
              }}
            >
              ×
            </button>
          </div>

          <div className="form-fields">
            <div className="form-group">
              <label>Timestamp (seconds):</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max={videoDuration > 0 ? videoDuration : undefined}
                value={formData.video_timestamp}
                onChange={handleTimestampChange}
                className={validationError ? 'error' : ''}
              />
              {validationError && (
                <div className="validation-error">{validationError}</div>
              )}
              {videoDuration > 0 && (
                <div className="timestamp-info">
                  Video duration: {formatTime(videoDuration)}
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
                setIsOpen(false);
                setValidationError(null);
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
