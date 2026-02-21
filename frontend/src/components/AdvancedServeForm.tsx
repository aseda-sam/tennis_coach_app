import React from 'react';
import {
  CourtSide,
  InOut,
  ServeSubtype,
  ServeWindowCreate,
} from '../types/serveWindow';
import { formatTime } from '../utils/validation';
import TimelineMarkers from './TimelineMarkers';

interface AdvancedServeFormProps {
  formData: ServeWindowCreate;
  setFormData: React.Dispatch<React.SetStateAction<ServeWindowCreate>>;
  validationError: string | null;
  isLoading: boolean;
  videoDuration: number;
  currentTime: number;
  lockedFrameNumber: number | null;
  supportsCompact: boolean;
  onClose: () => void;
  onSubmit: () => void;
  onShowCompact: () => void;
  onSeek?: (time: number) => void;
}

const AdvancedServeForm: React.FC<AdvancedServeFormProps> = ({
  formData,
  setFormData,
  validationError,
  isLoading,
  videoDuration,
  currentTime,
  lockedFrameNumber,
  supportsCompact,
  onClose,
  onSubmit,
  onShowCompact,
  onSeek,
}) => {
  return (
    <>
      <div className="form-header">
        <div className="timestamp-header">
          <div className="timestamp-label">Serve</div>
          <div className="timestamp-display">
            {formatTime(formData.start_timestamp)} –{' '}
            {formatTime(formData.end_timestamp)}
            {lockedFrameNumber !== null && (
              <span className="frame-number"> (frame {lockedFrameNumber})</span>
            )}
          </div>
        </div>
        <div className="form-header-actions">
          {supportsCompact && (
            <button
              className="compact-toggle-btn"
              onClick={(e) => {
                e.stopPropagation();
                onShowCompact();
              }}
            >
              Range only
            </button>
          )}
          <button
            className="close-form-btn"
            onClick={(e) => {
              e.stopPropagation();
              onClose();
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
                  court_side: (e.target.value as CourtSide) || null,
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

          <div className="form-group form-group--compact">
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
            onClose();
          }}
          disabled={isLoading}
        >
          Cancel
        </button>
        <button
          className="btn btn-primary"
          onClick={(e) => {
            e.stopPropagation();
            onSubmit();
          }}
          disabled={isLoading || !!validationError}
        >
          {isLoading ? 'Creating...' : 'Create Serve'}
        </button>
      </div>
    </>
  );
};

export default AdvancedServeForm;
