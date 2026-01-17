import React, { useEffect, useState } from 'react';
import {
  STROKE_SUBTYPE_LABELS,
  STROKE_TYPE_LABELS,
  getSubtypesForType,
  type StrokeType,
} from '../constants/shotTypes';
import { BallContact, BallContactUpdate } from '../services/ballContactApi';
import { formatTime, validateTimestamp } from '../utils/validation';
import './BallContactModal.css';

interface BallContactModalProps {
  contact: BallContact | null;
  isOpen: boolean;
  videoDuration: number; // Add video duration prop
  onClose: () => void;
  onUpdate: (contactId: number, updates: BallContactUpdate) => Promise<void>;
  onDelete: (contactId: number) => Promise<void>;
  isDemo?: boolean; // If true, hide edit/delete buttons
}

const BallContactModal: React.FC<BallContactModalProps> = ({
  contact,
  isOpen,
  videoDuration,
  onClose,
  onUpdate,
  onDelete,
  isDemo = false,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [formData, setFormData] = useState<BallContactUpdate>({
    video_timestamp: contact?.video_timestamp || 0,
    contact_hand: contact?.contact_hand || 'right',
    stroke_type: contact?.stroke_type || undefined,
    stroke_subtype: contact?.stroke_subtype || undefined,
  });

  // Update form data when contact changes
  useEffect(() => {
    if (contact) {
      setFormData({
        video_timestamp: contact.video_timestamp,
        contact_hand: contact.contact_hand,
        stroke_type: contact.stroke_type || undefined,
        stroke_subtype: contact.stroke_subtype || undefined,
      });
    }
    setValidationError(null);
  }, [contact]);

  // Validate timestamp whenever form data changes
  useEffect(() => {
    if (
      isEditing &&
      videoDuration > 0 &&
      formData.video_timestamp !== undefined
    ) {
      const validation = validateTimestamp(
        formData.video_timestamp,
        videoDuration
      );
      setValidationError(validation.isValid ? null : validation.error || null);
    }
  }, [formData.video_timestamp, videoDuration, isEditing]);

  if (!isOpen || !contact) return null;

  const handleEdit = () => {
    setIsEditing(true);
    setFormData({
      video_timestamp: contact.video_timestamp,
      contact_hand: contact.contact_hand,
      stroke_type: contact.stroke_type || undefined,
      stroke_subtype: contact.stroke_subtype || undefined,
    });
    setValidationError(null);
  };

  const handleSave = async () => {
    // Validate before submitting
    if (videoDuration > 0 && formData.video_timestamp !== undefined) {
      const validation = validateTimestamp(
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
      await onUpdate(contact.id, formData);
      setIsEditing(false);
      setValidationError(null);
    } catch (error) {
      // Error is shown to user via alert
      alert('Failed to update contact. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this ball contact?')) {
      return;
    }

    setIsLoading(true);
    try {
      await onDelete(contact.id);
      onClose();
    } catch (error) {
      // Error is shown to user via alert
      alert('Failed to delete contact. Please try again.');
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

  return (
    <div className="ball-contact-modal-overlay" onClick={onClose}>
      <div className="ball-contact-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Ball Contact Details</h3>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-content">
          {isEditing ? (
            <div className="edit-form">
              <div className="form-group">
                <label>Timestamp (seconds):</label>
                <input
                  type="number"
                  step="0.001"
                  min="0"
                  max={videoDuration > 0 ? videoDuration : undefined}
                  value={formData.video_timestamp || 0}
                  onChange={handleTimestampChange}
                  className={validationError ? 'error' : ''}
                />
                {validationError && (
                  <div className="validation-error">{validationError}</div>
                )}
                {videoDuration > 0 && (
                  <div className="timestamp-info">
                    Video duration: {formatTime(videoDuration)}
                    <br />
                    <small>
                      Enter timestamp with up to 3 decimal places for
                      frame-accurate positioning
                    </small>
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
          ) : (
            <div className="contact-details">
              <div className="detail-row">
                <span className="detail-label">Timestamp:</span>
                <span className="detail-value">
                  {contact.video_timestamp.toFixed(3)}s
                  {contact.frame_number && ` (Frame ${contact.frame_number})`}
                </span>
              </div>

              <div className="detail-row">
                <span className="detail-label">Contact Hand:</span>
                <span className="detail-value capitalize">
                  {contact.contact_hand}
                </span>
              </div>

              <div className="detail-row">
                <span className="detail-label">Stroke Type:</span>
                <span className="detail-value">
                  {contact.stroke_type
                    ? STROKE_TYPE_LABELS[contact.stroke_type] ||
                      contact.stroke_type
                    : 'Unknown'}
                </span>
              </div>

              {contact.stroke_subtype && (
                <div className="detail-row">
                  <span className="detail-label">Stroke Subtype:</span>
                  <span className="detail-value">
                    {STROKE_SUBTYPE_LABELS[contact.stroke_subtype] ||
                      contact.stroke_subtype}
                  </span>
                </div>
              )}

              <div className="detail-row">
                <span className="detail-label">Detection Source:</span>
                <span
                  className={`detail-value badge ${contact.detection_source}`}
                >
                  {contact.detection_source}
                </span>
              </div>

              <div className="detail-row">
                <span className="detail-label">Created:</span>
                <span className="detail-value">
                  {new Date(contact.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          )}
        </div>

        {!isDemo && (
          <div className="modal-actions">
            {isEditing ? (
              <>
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setIsEditing(false);
                    setValidationError(null);
                  }}
                  disabled={isLoading}
                >
                  Cancel
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleSave}
                  disabled={isLoading || !!validationError}
                >
                  {isLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </>
            ) : (
              <>
                <button
                  className="btn btn-danger"
                  onClick={handleDelete}
                  disabled={isLoading}
                >
                  {isLoading ? 'Deleting...' : 'Delete Contact'}
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleEdit}
                  disabled={isLoading}
                >
                  Edit Contact
                </button>
              </>
            )}
          </div>
        )}
        {isDemo && (
          <div className="modal-actions">
            <div className="demo-readonly-notice">
              <p>Demo mode: Contact editing is disabled</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BallContactModal;
