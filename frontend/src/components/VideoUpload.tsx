import React, { useCallback, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getApiErrorMessage } from '../utils/apiError';
import { useAppConfig } from '../hooks/useAppConfig';
import { useAdmin } from '../hooks/useAdmin';
import { usePlayerProfile } from '../hooks/usePlayerProfile';
import {
  useDeleteVideo,
  useUpdateVideoMetadata,
  useUploadVideo,
} from '../hooks/useVideos';
import { VideoMetadata } from '../types/video';
import { UploadIcon } from './Icons';
import './VideoUpload.css';

interface VideoUploadProps {
  onUploadSuccess: (video: VideoMetadata) => void;
  defaultIsDemo?: boolean;
  forceDemo?: boolean;
  hideDemoToggle?: boolean;
  demoNoticeText?: string;
}

function formatFileSizeMb(bytes: number) {
  const mb = bytes / (1024 * 1024);
  return Number.isInteger(mb) ? `${mb}` : mb.toFixed(1);
}

const VideoUpload: React.FC<VideoUploadProps> = ({
  onUploadSuccess,
  defaultIsDemo = false,
  forceDemo = false,
  hideDemoToggle = false,
  demoNoticeText,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<1 | 2>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadedVideoId, setUploadedVideoId] = useState<number | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isDemo, setIsDemo] = useState(defaultIsDemo);
  const [sessionType, setSessionType] = useState<string>('');
  const [cameraAngle, setCameraAngle] = useState<string>('');
  const [playerTag, setPlayerTag] = useState<'you' | 'someone_else'>('you');
  const { config } = useAppConfig();
  const { isAdmin: canUploadDemo } = useAdmin();
  const { data: playerProfile, isLoading: isPlayerProfileLoading } =
    usePlayerProfile();
  const queryClient = useQueryClient();
  const deleteVideoMutation = useDeleteVideo();
  const uploadMutation = useUploadVideo();
  const updateMetadataMutation = useUpdateVideoMetadata();
  const resolvedIsDemo = forceDemo ? true : isDemo;
  const maxSizeBytes = config.upload_limits.max_file_size_bytes;
  const maxSizeLabel = formatFileSizeMb(maxSizeBytes);
  const playerLabel = isPlayerProfileLoading
    ? 'Your profile'
    : playerProfile?.name || 'Your profile';

  const handleFileSelect = useCallback(
    async (file: File) => {
      // Validate file type
      const allowedTypes = [
        'video/mp4',
        'video/avi',
        'video/mov',
        'video/wmv',
        'video/flv',
      ];
      if (!allowedTypes.includes(file.type)) {
        setError('Please select a valid video file (MP4, AVI, MOV, WMV, FLV)');
        return;
      }

      // Validate file size (backend-configured limit)
      if (file.size > maxSizeBytes) {
        setError(`File size must be less than ${maxSizeLabel}MB`);
        return;
      }

      setSelectedFile(file);
      setError(null);
      setUploadProgress(0);

      try {
        const clientRecordedAt = file.lastModified
          ? new Date(file.lastModified).toISOString()
          : undefined;

        // Upload file immediately without metadata
        const response = await uploadMutation.mutateAsync({
          file,
          isDemo: resolvedIsDemo,
          clientRecordedAt,
          metadata: {},
        });

        setUploadedVideoId(response.video_id);
        setUploadProgress(100);
        setStep(2); // Move to Step 2: Details
      } catch (err: unknown) {
        const errorMessage = getApiErrorMessage(
          err,
          'Upload failed. Please try again.'
        );
        setError(errorMessage);
      }
    },
    [maxSizeBytes, maxSizeLabel, resolvedIsDemo, uploadMutation]
  );

  const handleFinishUpload = useCallback(async () => {
    if (!uploadedVideoId || !sessionType) {
      return;
    }

    setError(null);

    try {
      // Update video metadata
      const updatedVideo = await updateMetadataMutation.mutateAsync({
        videoId: uploadedVideoId,
        metadata: {
          session_type: sessionType,
          camera_angle: cameraAngle || undefined,
          player_tag: playerTag,
        },
      });

      queryClient.setQueryData(['video', uploadedVideoId], updatedVideo);
      onUploadSuccess(updatedVideo as VideoMetadata);
    } catch (err: unknown) {
      const errorMessage = getApiErrorMessage(
        err,
        'Failed to update video details. Please try again.'
      );
      setError(errorMessage);
    }
  }, [
    uploadedVideoId,
    sessionType,
    cameraAngle,
    playerTag,
    onUploadSuccess,
    updateMetadataMutation,
    queryClient,
  ]);

  const handleReplaceFile = useCallback(async () => {
    // If a video was already uploaded, delete it from the server to avoid orphaned videos
    if (uploadedVideoId) {
      try {
        await deleteVideoMutation.mutateAsync(uploadedVideoId);
      } catch (err) {
        // Log error but don't block the replace action
        // User can manually delete orphaned videos later if needed
        console.warn('Failed to delete replaced video:', err);
      }
    }

    // Reset client state
    setSelectedFile(null);
    setUploadedVideoId(null);
    setUploadProgress(0);
    setStep(1);
    setSessionType('');
    setCameraAngle('');
    setPlayerTag('you');
    setError(null);
    uploadMutation.reset();
    updateMetadataMutation.reset();
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [
    uploadedVideoId,
    deleteVideoMutation,
    uploadMutation,
    updateMetadataMutation,
  ]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);

      if (step === 2) {
        return; // Don't allow dropping new files in Step 2
      }

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        handleFileSelect(files[0]);
      }
    },
    [handleFileSelect, step]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFileSelect(file);
      }
    },
    [handleFileSelect]
  );

  const handleAreaClick = useCallback(() => {
    if (step === 2) {
      return; // Don't allow clicking upload area in Step 2
    }
    if (!uploadMutation.isPending && fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, [step, uploadMutation.isPending]);

  return (
    <div className="video-upload">
      {/* Step Indicator */}
      <div className="upload-steps">
        <div
          className={`step-indicator ${step >= 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}`}
        >
          <span className="step-number">1</span>
          <span className="step-label">Upload</span>
        </div>
        <div className={`step-indicator ${step >= 2 ? 'active' : ''}`}>
          <span className="step-number">2</span>
          <span className="step-label">Details</span>
        </div>
      </div>

      {step === 1 && (
        <>
          <div
            className={`upload-area ${isDragOver ? 'drag-over' : ''} ${uploadMutation.isPending ? 'uploading' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleAreaClick}
          >
            {uploadMutation.isPending ? (
              <div className="upload-progress">
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
                <p>Uploading... {uploadProgress}%</p>
              </div>
            ) : uploadMutation.isSuccess ? (
              <div className="upload-success">
                <div className="upload-icon" aria-hidden="true">
                  <UploadIcon size={48} color="var(--color-success)" />
                </div>
                <p className="upload-main-text">
                  Uploaded: {selectedFile?.name}
                </p>
                <button
                  type="button"
                  onClick={handleReplaceFile}
                  className="replace-file-btn"
                >
                  Replace File
                </button>
              </div>
            ) : (
              <>
                <div className="upload-icon" aria-hidden="true">
                  <UploadIcon size={48} color="var(--color-text-muted)" />
                </div>
                <p className="upload-main-text">
                  Drag and drop your tennis video here
                </p>
                <p className="upload-or-text">or</p>
                <label
                  className="file-input-label"
                  onClick={(e) => e.stopPropagation()}
                >
                  Choose File
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    onChange={handleFileInput}
                    style={{ display: 'none' }}
                  />
                </label>
              </>
            )}
          </div>

          {canUploadDemo && !hideDemoToggle && !forceDemo && (
            <div className="demo-upload-option">
              <label>
                <input
                  type="checkbox"
                  checked={isDemo}
                  onChange={(e) => setIsDemo(e.target.checked)}
                  disabled={uploadMutation.isPending}
                />
                <span>
                  Upload as demo video (public, accessible to all users)
                </span>
              </label>
            </div>
          )}
          {canUploadDemo && forceDemo && (
            <div className="demo-upload-option demo-upload-option--locked">
              <span>
                {demoNoticeText ||
                  'This upload will be saved as a public demo video.'}
              </span>
            </div>
          )}
        </>
      )}

      {step === 2 && (
        <div className="upload-details-step">
          <div className="uploaded-file-info">
            <div className="upload-icon" aria-hidden="true">
              <UploadIcon size={32} color="var(--color-success)" />
            </div>
            <div className="uploaded-file-details">
              <p className="uploaded-filename">{selectedFile?.name}</p>
              <p className="uploaded-status">Uploaded successfully</p>
            </div>
          </div>

          <div className="details-form">
            <div className={`form-field ${sessionType ? 'selected' : ''}`}>
              <label>
                Session Type{' '}
                <span className="required-asterisk" aria-label="required">
                  *
                </span>
              </label>
              <select
                value={sessionType}
                onChange={(e) => setSessionType(e.target.value)}
                disabled={updateMetadataMutation.isPending}
              >
                <option value="">Select session type</option>
                <option value="serve_practice">Serve Practice</option>
                <option value="match">Match</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className={`form-field ${cameraAngle ? 'selected' : ''}`}>
              <label>Camera Angle</label>
              <select
                value={cameraAngle}
                onChange={(e) => setCameraAngle(e.target.value)}
                disabled={updateMetadataMutation.isPending}
              >
                <option value="">Select camera angle</option>
                <option value="behind">Behind</option>
                <option value="profile">Profile</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>

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
                    onChange={() => setPlayerTag('you')}
                    disabled={updateMetadataMutation.isPending}
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
                    onChange={() => setPlayerTag('someone_else')}
                    disabled={updateMetadataMutation.isPending}
                  />
                  <span>
                    <strong>Someone Else</strong>
                  </span>
                </label>
              </div>
              <p className="player-tag-note">
                New serves detected in this video will be saved under this
                player.
              </p>
            </div>

            <div className="finish-upload-actions">
              <button
                type="button"
                onClick={handleReplaceFile}
                className="replace-file-btn-secondary"
                disabled={updateMetadataMutation.isPending}
              >
                Replace File
              </button>
              <button
                type="button"
                onClick={handleFinishUpload}
                className="finish-upload-btn"
                disabled={!sessionType || updateMetadataMutation.isPending}
              >
                {updateMetadataMutation.isPending
                  ? 'Finishing...'
                  : 'Finish Upload'}
              </button>
            </div>
          </div>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default VideoUpload;
