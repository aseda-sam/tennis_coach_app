import React from 'react';
import { ServeWindowCreate } from '../types/serveWindow';
import { formatTime } from '../utils/validation';
import TimelineMarkers from './TimelineMarkers';

interface CompactServeFormProps {
  formData: ServeWindowCreate;
  setFormData: React.Dispatch<React.SetStateAction<ServeWindowCreate>>;
  validationError: string | null;
  isLoading: boolean;
  videoDuration: number;
  currentTime: number;
  onClose: () => void;
  onSubmit: () => void;
  onShowAdvanced: () => void;
  onSeek?: (time: number) => void;
}

const CompactServeForm: React.FC<CompactServeFormProps> = ({
  formData,
  setFormData,
  validationError,
  isLoading,
  videoDuration,
  currentTime,
  onClose,
  onSubmit,
  onShowAdvanced,
  onSeek,
}) => {
  return (
    <>
      <div className="compact-form-header">
        <div className="compact-form-title">Create Serve</div>
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
              onClose();
            }}
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            className="compact-btn compact-btn--primary"
            onClick={(e) => {
              e.stopPropagation();
              onSubmit();
            }}
            disabled={isLoading || !!validationError}
          >
            {isLoading ? 'Creating...' : 'Create'}
          </button>
          <button
            className="compact-btn compact-btn--details"
            onClick={(e) => {
              e.stopPropagation();
              onShowAdvanced();
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
  );
};

export default CompactServeForm;
