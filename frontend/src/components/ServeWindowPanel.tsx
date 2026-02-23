import React from 'react';
import {
  CourtSide,
  InOut,
  ServeSubtype,
  ServeWindow,
  ServeWindowUpdate,
} from '../types/serveWindow';
import { formatTime } from '../utils/validation';
import TimelineMarkers from './TimelineMarkers';

export interface ServeWindowFormData extends ServeWindowUpdate {
  start_timestamp: number;
  end_timestamp: number;
  contact_timestamp: number | null;
}

export interface ServeWindowChildProps {
  serveWindow: ServeWindow;
  isEditing: boolean;
  isLoading: boolean;
  validationError: string | null;
  formData: ServeWindowFormData;
  setFormData: React.Dispatch<React.SetStateAction<ServeWindowFormData>>;
  videoDuration: number;
  currentTime: number;
  isDemo: boolean;
  onClose: () => void;
  onSeek?: (time: number) => void;
  onEdit: () => void;
  onSave: () => void;
  onDelete: () => void;
  onCancelEdit: () => void;
}

const ServeWindowPanel: React.FC<ServeWindowChildProps> = ({
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
                  <span>Contact: {formatTime(formData.contact_timestamp)}</span>
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
                      court_side: (e.target.value as CourtSide) || null,
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

              <div className="serve-detail-panel__form-group serve-detail-panel__form-group--half">
                <label>In/Out</label>
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
            </div>

            {validationError && (
              <div className="serve-detail-panel__error">{validationError}</div>
            )}
          </div>
        ) : (
          <div className="serve-detail-panel__details">
            <div className="serve-detail-panel__detail-row">
              <span className="serve-detail-panel__detail-label">Range:</span>
              <span className="serve-detail-panel__detail-value">
                {formatTime(serveWindow.start_timestamp)} -{' '}
                {formatTime(serveWindow.end_timestamp)}
              </span>
            </div>

            {serveWindow.contact_timestamp !== null && (
              <div className="serve-detail-panel__detail-row">
                <span className="serve-detail-panel__detail-label">
                  Contact:
                </span>
                <span className="serve-detail-panel__detail-value">
                  {formatTime(serveWindow.contact_timestamp)}
                </span>
              </div>
            )}

            {serveWindow.court_side && (
              <div className="serve-detail-panel__detail-row">
                <span className="serve-detail-panel__detail-label">Court:</span>
                <span className="serve-detail-panel__detail-value">
                  {serveWindow.court_side.charAt(0).toUpperCase() +
                    serveWindow.court_side.slice(1)}
                </span>
              </div>
            )}

            {serveWindow.serve_subtype && (
              <div className="serve-detail-panel__detail-row">
                <span className="serve-detail-panel__detail-label">Type:</span>
                <span className="serve-detail-panel__detail-value">
                  {serveWindow.serve_subtype.charAt(0).toUpperCase() +
                    serveWindow.serve_subtype.slice(1)}
                </span>
              </div>
            )}

            {serveWindow.in_out && (
              <div className="serve-detail-panel__detail-row">
                <span className="serve-detail-panel__detail-label">
                  Result:
                </span>
                <span className="serve-detail-panel__detail-value">
                  {serveWindow.in_out.replace('_', ' ')}
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
                onClick={onCancelEdit}
                disabled={isLoading}
              >
                Cancel
              </button>
              <button
                className="serve-detail-panel__btn serve-detail-panel__btn--primary"
                onClick={onSave}
                disabled={isLoading || !!validationError}
              >
                {isLoading ? 'Saving...' : 'Save'}
              </button>
            </>
          ) : (
            <>
              <button
                className="serve-detail-panel__btn serve-detail-panel__btn--danger"
                onClick={onDelete}
                disabled={isLoading}
              >
                Delete
              </button>
              <button
                className="serve-detail-panel__btn serve-detail-panel__btn--primary"
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
        <div className="serve-detail-panel__actions">
          <div className="serve-detail-panel__demo-notice">
            Demo mode: Editing disabled
          </div>
        </div>
      )}
    </div>
  );
};

export default ServeWindowPanel;
