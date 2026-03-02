import React from 'react';
import { Upload } from 'lucide-react';

interface VideoUploadMetadataFormProps {
  selectedFile: File | null;
  sessionType: string;
  cameraAngle: string;
  playerTag: 'you' | 'someone_else';
  playerLabel: string;
  isDemo?: boolean;
  isSubmitting: boolean;
  onSessionTypeChange: (value: string) => void;
  onCameraAngleChange: (value: string) => void;
  onPlayerTagChange: (value: 'you' | 'someone_else') => void;
  onFinish: () => void;
  onReplaceFile: () => void;
}

const VideoUploadMetadataForm: React.FC<VideoUploadMetadataFormProps> = ({
  selectedFile,
  sessionType,
  cameraAngle,
  playerTag,
  playerLabel,
  isDemo = false,
  isSubmitting,
  onSessionTypeChange,
  onCameraAngleChange,
  onPlayerTagChange,
  onFinish,
  onReplaceFile,
}) => {
  return (
    <div className="upload-details-step">
      <div className="uploaded-file-info">
        <div className="upload-icon" aria-hidden="true">
          <Upload size={32} color="var(--color-success)" strokeWidth={1.5} />
        </div>
        <div className="uploaded-file-details">
          <p className="uploaded-filename">{selectedFile?.name}</p>
          <p className="uploaded-status">Uploaded successfully</p>
        </div>
      </div>

      <div className="details-form">
        {!isDemo && (
          <div className={`form-field ${sessionType ? 'selected' : ''}`}>
            <label>
              Session Type{' '}
              <span className="required-asterisk" aria-label="required">
                *
              </span>
            </label>
            <select
              value={sessionType}
              onChange={(e) => onSessionTypeChange(e.target.value)}
              disabled={isSubmitting}
            >
              <option value="">Select session type</option>
              <option value="serve_practice">Serve Practice</option>
              <option value="match">Match</option>
              <option value="other">Other</option>
            </select>
          </div>
        )}

        <div className={`form-field ${cameraAngle ? 'selected' : ''}`}>
          <label>Camera Angle</label>
          <select
            value={cameraAngle}
            onChange={(e) => onCameraAngleChange(e.target.value)}
            disabled={isSubmitting}
          >
            <option value="">Select camera angle</option>
            <option value="behind">Behind</option>
            <option value="profile">Profile</option>
            <option value="unknown">Unknown</option>
          </select>
        </div>

        {!isDemo && (
          <div className="player-tag-section">
            <div className="player-tag-title">Who Is Serving?</div>
            <div className="player-tag-options">
              <label
                className={`player-tag-option ${
                  playerTag === 'you' ? 'selected' : ''
                }`}
              >
                <input
                  type="radio"
                  name="playerTag"
                  value="you"
                  checked={playerTag === 'you'}
                  onChange={() => onPlayerTagChange('you')}
                  disabled={isSubmitting}
                />
                <span>
                  <strong>{playerLabel}</strong>
                </span>
              </label>
              <label
                className={`player-tag-option ${
                  playerTag === 'someone_else' ? 'selected' : ''
                }`}
              >
                <input
                  type="radio"
                  name="playerTag"
                  value="someone_else"
                  checked={playerTag === 'someone_else'}
                  onChange={() => onPlayerTagChange('someone_else')}
                  disabled={isSubmitting}
                />
                <span>
                  <strong>Someone Else</strong>
                </span>
              </label>
            </div>
            <p className="player-tag-note">
              New serves detected in this video will be saved under this player.
            </p>
          </div>
        )}

        <div className="finish-upload-actions">
          <button
            type="button"
            onClick={onReplaceFile}
            className="replace-file-btn-secondary"
            disabled={isSubmitting}
          >
            Replace File
          </button>
          <button
            type="button"
            onClick={onFinish}
            className="finish-upload-btn"
            disabled={(!isDemo && !sessionType) || isSubmitting}
          >
            {isSubmitting ? 'Finishing...' : 'Finish Upload'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default VideoUploadMetadataForm;
