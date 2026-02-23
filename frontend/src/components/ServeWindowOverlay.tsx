import React from 'react';
import { CourtSide, InOut, ServeSubtype } from '../types/serveWindow';
import { formatTime } from '../utils/validation';
import './BallContactModal.css'; // Reuse styles
import TimelineMarkers from './TimelineMarkers';
import { ServeWindowChildProps } from './ServeWindowPanel';

const ServeWindowOverlay: React.FC<ServeWindowChildProps> = ({
  serveWindow,
  isEditing,
  isLoading,
  validationError,
  formData,
  setFormData,
  videoDuration,
  currentTime,
  isDemo,
  onClose,
  onSeek,
  onEdit,
  onSave,
  onDelete,
  onCancelEdit,
}) => {
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
                      court_side: (e.target.value as CourtSide) || null,
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
                      serve_subtype: (e.target.value as ServeSubtype) || null,
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
                      in_out: (e.target.value as InOut) || null,
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
                  {formatTime(serveWindow.start_timestamp)} -{' '}
                  {formatTime(serveWindow.end_timestamp)}
                </span>
              </div>

              {serveWindow.contact_timestamp !== null && (
                <div className="detail-row">
                  <span className="detail-label">Contact:</span>
                  <span className="detail-value">
                    {formatTime(serveWindow.contact_timestamp)}
                  </span>
                </div>
              )}

              {serveWindow.court_side && (
                <div className="detail-row">
                  <span className="detail-label">Court Side:</span>
                  <span className="detail-value capitalize">
                    {serveWindow.court_side}
                  </span>
                </div>
              )}

              {serveWindow.serve_number && (
                <div className="detail-row">
                  <span className="detail-label">Serve Number:</span>
                  <span className="detail-value">
                    {serveWindow.serve_number}
                  </span>
                </div>
              )}

              {serveWindow.serve_subtype && (
                <div className="detail-row">
                  <span className="detail-label">Serve Type:</span>
                  <span className="detail-value capitalize">
                    {serveWindow.serve_subtype}
                  </span>
                </div>
              )}

              {serveWindow.in_out && (
                <div className="detail-row">
                  <span className="detail-label">In/Out:</span>
                  <span className="detail-value capitalize">
                    {serveWindow.in_out.replace('_', ' ')}
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
                  onClick={onCancelEdit}
                  disabled={isLoading}
                >
                  Cancel
                </button>
                <button
                  className="btn btn-primary"
                  onClick={onSave}
                  disabled={isLoading || !!validationError}
                >
                  {isLoading ? 'Saving...' : 'Save Changes'}
                </button>
              </>
            ) : (
              <>
                <button
                  className="btn btn-danger"
                  onClick={onDelete}
                  disabled={isLoading}
                >
                  {isLoading ? 'Deleting...' : 'Delete'}
                </button>
                <button
                  className="btn btn-primary"
                  onClick={onEdit}
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

export default ServeWindowOverlay;
