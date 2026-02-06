import React, { useEffect, useState } from 'react';
import { ServeAttempt, ServeAttemptUpdate } from '../services/serveAttemptApi';
import {
  formatTime,
  validateContactTimestamp,
  validateTimestamp,
} from '../utils/validation';
import './BallContactModal.css'; // Reuse styles
import TimelineMarkers from './TimelineMarkers';

interface ServeAttemptModalProps {
  serveAttempt: ServeAttempt | null;
  isOpen: boolean;
  videoDuration: number;
  currentTime?: number;
  onClose: () => void;
  onUpdate: (
    serveAttemptId: number,
    updates: ServeAttemptUpdate
  ) => Promise<void>;
  onDelete: (serveAttemptId: number) => Promise<void>;
  onSeek?: (time: number) => void;
  isDemo?: boolean;
  /** Use panel mode to show as side panel instead of blocking overlay */
  mode?: 'overlay' | 'panel';
}

const ServeAttemptModal: React.FC<ServeAttemptModalProps> = ({
  serveAttempt,
  isOpen,
  videoDuration,
  currentTime = 0,
  onClose,
  onUpdate,
  onDelete,
  onSeek,
  isDemo = false,
  mode = 'overlay',
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [formData, setFormData] = useState<
    ServeAttemptUpdate & {
      start_timestamp: number;
      end_timestamp: number;
      contact_timestamp: number | null;
    }
  >({
    start_timestamp: serveAttempt?.start_timestamp ?? 0,
    end_timestamp: serveAttempt?.end_timestamp ?? 0,
    contact_timestamp: serveAttempt?.contact_timestamp ?? null,
    court_side: serveAttempt?.court_side ?? null,
    serve_number: serveAttempt?.serve_number ?? null,
    serve_subtype: serveAttempt?.serve_subtype ?? null,
    in_out: serveAttempt?.in_out ?? null,
  });

  useEffect(() => {
    if (serveAttempt) {
      setFormData({
        start_timestamp: serveAttempt.start_timestamp,
        end_timestamp: serveAttempt.end_timestamp,
        contact_timestamp: serveAttempt.contact_timestamp,
        court_side: serveAttempt.court_side,
        serve_number: serveAttempt.serve_number,
        serve_subtype: serveAttempt.serve_subtype,
        in_out: serveAttempt.in_out,
      });
    }
    setValidationError(null);
  }, [serveAttempt]);

  useEffect(() => {
    if (
      isEditing &&
      videoDuration > 0 &&
      formData.start_timestamp !== undefined &&
      formData.start_timestamp !== null &&
      formData.end_timestamp !== undefined &&
      formData.end_timestamp !== null
    ) {
      const startVal = formData.start_timestamp;
      const endVal = formData.end_timestamp;
      const startValidation = validateTimestamp(startVal, videoDuration);
      const endValidation = validateTimestamp(endVal, videoDuration);
      if (!startValidation.isValid) {
        setValidationError(startValidation.error || null);
      } else if (!endValidation.isValid) {
        setValidationError(endValidation.error || null);
      } else if (startVal >= endVal) {
        setValidationError('Start time must be before end time');
      } else {
        const contactValidation = validateContactTimestamp(
          formData.contact_timestamp ?? null,
          startVal,
          endVal,
          videoDuration
        );
        if (!contactValidation.isValid) {
          setValidationError(contactValidation.error || null);
        } else {
          setValidationError(null);
        }
      }
    }
  }, [formData, videoDuration, isEditing]);

  if (!isOpen || !serveAttempt) return null;

  const handleEdit = () => {
    setIsEditing(true);
    setFormData({
      start_timestamp: serveAttempt.start_timestamp,
      end_timestamp: serveAttempt.end_timestamp,
      contact_timestamp: serveAttempt.contact_timestamp,
      court_side: serveAttempt.court_side,
      serve_number: serveAttempt.serve_number,
      serve_subtype: serveAttempt.serve_subtype,
      in_out: serveAttempt.in_out,
    });
    setValidationError(null);
  };

  const handleSave = async () => {
    if (
      videoDuration > 0 &&
      formData.start_timestamp !== undefined &&
      formData.start_timestamp !== null &&
      formData.end_timestamp !== undefined &&
      formData.end_timestamp !== null
    ) {
      const startVal = formData.start_timestamp;
      const endVal = formData.end_timestamp;
      const startValidation = validateTimestamp(startVal, videoDuration);
      const endValidation = validateTimestamp(endVal, videoDuration);
      if (!startValidation.isValid || !endValidation.isValid) {
        setValidationError(
          startValidation.error || endValidation.error || 'Invalid timestamp'
        );
        return;
      }

      if (startVal >= endVal) {
        setValidationError('Start time must be before end time');
        return;
      }

      const contactValidation = validateContactTimestamp(
        formData.contact_timestamp ?? null,
        startVal,
        endVal,
        videoDuration
      );
      if (!contactValidation.isValid) {
        setValidationError(contactValidation.error || 'Invalid timestamp');
        return;
      }
    }

    setIsLoading(true);
    try {
      await onUpdate(serveAttempt.id, formData);
      setIsEditing(false);
      setValidationError(null);
    } catch (error) {
      alert('Failed to update serve. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this serve?')) {
      return;
    }

    setIsLoading(true);
    try {
      await onDelete(serveAttempt.id);
      onClose();
    } catch (error) {
      alert('Failed to delete serve attempt. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Panel mode renders without the blocking overlay
  if (mode === 'panel') {
    return (
      <div className="serve-detail-panel">
        <div className="serve-detail-panel__header">
          <h3>Serve Details</h3>
          <button className="serve-detail-panel__close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="serve-detail-panel__content">
          {isEditing ? (
            <div className="serve-detail-panel__form">
              <div className="serve-detail-panel__form-group">
                <label>Serve Window & Contact:</label>
                <TimelineMarkers
                  startTime={formData.start_timestamp}
                  endTime={formData.end_timestamp}
                  contactTime={formData.contact_timestamp}
                  videoDuration={videoDuration}
                  currentTime={currentTime}
                  onStartChange={(time) =>
                    setFormData({ ...formData, start_timestamp: time })
                  }
                  onEndChange={(time) =>
                    setFormData({ ...formData, end_timestamp: time })
                  }
                  onContactChange={(time) =>
                    setFormData({ ...formData, contact_timestamp: time })
                  }
                  onSeek={onSeek}
                  zoomToWindow={true}
                />
                {formData.contact_timestamp !== null && (
                  <div className="serve-detail-panel__contact-row">
                    <span>
                      Contact: {formatTime(formData.contact_timestamp)}
                    </span>
                    <button
                      type="button"
                      className="serve-detail-panel__clear-btn"
                      onClick={() =>
                        setFormData({ ...formData, contact_timestamp: null })
                      }
                    >
                      Clear
                    </button>
                  </div>
                )}
              </div>

              <div className="serve-detail-panel__form-row">
                <div className="serve-detail-panel__form-group serve-detail-panel__form-group--half">
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

                <div className="serve-detail-panel__form-group serve-detail-panel__form-group--half">
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
              </div>

              <div className="serve-detail-panel__form-row">
                <div className="serve-detail-panel__form-group serve-detail-panel__form-group--half">
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

                <div className="serve-detail-panel__form-group serve-detail-panel__form-group--half">
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

              {validationError && (
                <div className="serve-detail-panel__error">
                  {validationError}
                </div>
              )}
            </div>
          ) : (
            <div className="serve-detail-panel__details">
              <div className="serve-detail-panel__detail-row">
                <span className="serve-detail-panel__detail-label">Range:</span>
                <span className="serve-detail-panel__detail-value">
                  {formatTime(serveAttempt.start_timestamp)} -{' '}
                  {formatTime(serveAttempt.end_timestamp)}
                </span>
              </div>

              {serveAttempt.contact_timestamp !== null && (
                <div className="serve-detail-panel__detail-row">
                  <span className="serve-detail-panel__detail-label">
                    Contact:
                  </span>
                  <span className="serve-detail-panel__detail-value">
                    {formatTime(serveAttempt.contact_timestamp)}
                  </span>
                </div>
              )}

              {serveAttempt.elbow_angle_at_contact !== null && (
                <div className="serve-detail-panel__detail-row">
                  <span className="serve-detail-panel__detail-label">
                    Elbow Angle:
                  </span>
                  <span className="serve-detail-panel__detail-value">
                    {Math.round(serveAttempt.elbow_angle_at_contact)}°
                  </span>
                </div>
              )}

              {serveAttempt.court_side && (
                <div className="serve-detail-panel__detail-row">
                  <span className="serve-detail-panel__detail-label">
                    Court:
                  </span>
                  <span className="serve-detail-panel__detail-value">
                    {serveAttempt.court_side.charAt(0).toUpperCase() +
                      serveAttempt.court_side.slice(1)}
                  </span>
                </div>
              )}

              {serveAttempt.serve_subtype && (
                <div className="serve-detail-panel__detail-row">
                  <span className="serve-detail-panel__detail-label">
                    Type:
                  </span>
                  <span className="serve-detail-panel__detail-value">
                    {serveAttempt.serve_subtype.charAt(0).toUpperCase() +
                      serveAttempt.serve_subtype.slice(1)}
                  </span>
                </div>
              )}

              {serveAttempt.in_out && (
                <div className="serve-detail-panel__detail-row">
                  <span className="serve-detail-panel__detail-label">
                    Result:
                  </span>
                  <span className="serve-detail-panel__detail-value">
                    {serveAttempt.in_out.replace('_', ' ')}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {!isDemo && (
          <div className="serve-detail-panel__actions">
            {isEditing ? (
              <>
                <button
                  className="serve-detail-panel__btn serve-detail-panel__btn--secondary"
                  onClick={() => {
                    setIsEditing(false);
                    setValidationError(null);
                  }}
                  disabled={isLoading}
                >
                  Cancel
                </button>
                <button
                  className="serve-detail-panel__btn serve-detail-panel__btn--primary"
                  onClick={handleSave}
                  disabled={isLoading || !!validationError}
                >
                  {isLoading ? 'Saving...' : 'Save'}
                </button>
              </>
            ) : (
              <>
                <button
                  className="serve-detail-panel__btn serve-detail-panel__btn--danger"
                  onClick={handleDelete}
                  disabled={isLoading}
                >
                  Delete
                </button>
                <button
                  className="serve-detail-panel__btn serve-detail-panel__btn--primary"
                  onClick={handleEdit}
                  disabled={isLoading}
                >
                  Edit
                </button>
              </>
            )}
          </div>
        )}
        {isDemo && (
          <div className="serve-detail-panel__actions">
            <div className="serve-detail-panel__demo-notice">
              Demo mode: Editing disabled
            </div>
          </div>
        )}
      </div>
    );
  }

  // Overlay mode (original behavior)
  return (
    <div className="ball-contact-modal-overlay" onClick={onClose}>
      <div className="ball-contact-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Serve Details</h3>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="modal-content">
          {isEditing ? (
            <div className="edit-form">
              <div className="form-group">
                <label>Serve Window & Contact:</label>
                <TimelineMarkers
                  startTime={formData.start_timestamp}
                  endTime={formData.end_timestamp}
                  contactTime={formData.contact_timestamp}
                  videoDuration={videoDuration}
                  currentTime={currentTime}
                  onStartChange={(time) =>
                    setFormData({ ...formData, start_timestamp: time })
                  }
                  onEndChange={(time) =>
                    setFormData({ ...formData, end_timestamp: time })
                  }
                  onContactChange={(time) =>
                    setFormData({ ...formData, contact_timestamp: time })
                  }
                  onSeek={onSeek}
                  zoomToWindow={true}
                />
                {formData.contact_timestamp !== null && (
                  <div className="contact-clear-row">
                    <span className="contact-value">
                      Contact: {formatTime(formData.contact_timestamp)}
                    </span>
                    <button
                      type="button"
                      className="btn btn-small btn-secondary"
                      onClick={() =>
                        setFormData({ ...formData, contact_timestamp: null })
                      }
                    >
                      Clear Contact
                    </button>
                  </div>
                )}
              </div>

              <div className="form-group">
                <label>Court Side:</label>
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

              <div className="form-group">
                <label>Serve Number:</label>
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

              <div className="form-group">
                <label>Serve Type:</label>
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

              <div className="form-group">
                <label>In/Out:</label>
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

              {validationError && (
                <div className="validation-error">{validationError}</div>
              )}
            </div>
          ) : (
            <div className="contact-details">
              <div className="detail-row">
                <span className="detail-label">Range:</span>
                <span className="detail-value">
                  {formatTime(serveAttempt.start_timestamp)} -{' '}
                  {formatTime(serveAttempt.end_timestamp)}
                </span>
              </div>

              {serveAttempt.contact_timestamp !== null && (
                <div className="detail-row">
                  <span className="detail-label">Contact:</span>
                  <span className="detail-value">
                    {formatTime(serveAttempt.contact_timestamp)}
                  </span>
                </div>
              )}

              {serveAttempt.elbow_angle_at_contact !== null && (
                <div className="detail-row">
                  <span className="detail-label">Elbow Angle:</span>
                  <span className="detail-value">
                    {Math.round(serveAttempt.elbow_angle_at_contact)}°
                  </span>
                </div>
              )}

              {serveAttempt.court_side && (
                <div className="detail-row">
                  <span className="detail-label">Court Side:</span>
                  <span className="detail-value capitalize">
                    {serveAttempt.court_side}
                  </span>
                </div>
              )}

              {serveAttempt.serve_number && (
                <div className="detail-row">
                  <span className="detail-label">Serve Number:</span>
                  <span className="detail-value">
                    {serveAttempt.serve_number}
                  </span>
                </div>
              )}

              {serveAttempt.serve_subtype && (
                <div className="detail-row">
                  <span className="detail-label">Serve Type:</span>
                  <span className="detail-value capitalize">
                    {serveAttempt.serve_subtype}
                  </span>
                </div>
              )}

              {serveAttempt.in_out && (
                <div className="detail-row">
                  <span className="detail-label">In/Out:</span>
                  <span className="detail-value capitalize">
                    {serveAttempt.in_out.replace('_', ' ')}
                  </span>
                </div>
              )}
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
                  {isLoading ? 'Deleting...' : 'Delete'}
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleEdit}
                  disabled={isLoading}
                >
                  Edit
                </button>
              </>
            )}
          </div>
        )}
        {isDemo && (
          <div className="modal-actions">
            <div className="demo-readonly-notice">
              <p>Demo mode: Serve editing is disabled</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ServeAttemptModal;
