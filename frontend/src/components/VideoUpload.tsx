import React, { useCallback, useRef, useState } from 'react';
import { useDemoEditor } from '../hooks/useDemoEditor';
import { videoApi } from '../services/api';
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

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

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
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isDemo, setIsDemo] = useState(defaultIsDemo);
  const [sessionType, setSessionType] = useState<string>('');
  const [cameraAngle, setCameraAngle] = useState<string>('');
  const [isUpdatingMetadata, setIsUpdatingMetadata] = useState(false);
  const { isDemoEditor: canUploadDemo } = useDemoEditor();
  const resolvedIsDemo = forceDemo ? true : isDemo;

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

      // Validate file size (100MB limit)
      const maxSize = 100 * 1024 * 1024; // 100MB
      if (file.size > maxSize) {
        setError('File size must be less than 100MB');
        return;
      }

      setSelectedFile(file);
      setError(null);
      setUploadStatus('uploading');
      setUploadProgress(0);

      try {
        // Upload file immediately without metadata
        const response = await videoApi.uploadVideo(file, resolvedIsDemo, {});

        setUploadedVideoId(response.video_id);
        setUploadProgress(100);
        setUploadStatus('success');
        setStep(2); // Move to Step 2: Details
      } catch (err: unknown) {
        const axiosError = err as {
          response?: {
            data?: { detail?: string; error?: { message?: string } };
          };
        };
        const detail =
          axiosError.response?.data?.detail ||
          axiosError.response?.data?.error?.message;

        const errorMessage = detail || 'Upload failed. Please try again.';
        setError(errorMessage);
        setUploadStatus('error');
      }
    },
    [resolvedIsDemo]
  );

  const handleFinishUpload = useCallback(async () => {
    if (!uploadedVideoId || !sessionType) {
      return;
    }

    setIsUpdatingMetadata(true);
    setError(null);

    try {
      // Update video metadata
      await videoApi.updateVideoMetadata(uploadedVideoId, {
        session_type: sessionType,
        camera_angle: cameraAngle || undefined,
      });

      // Get updated video info
      const updatedVideo = await videoApi.getVideo(uploadedVideoId);

      // Create VideoMetadata object
      const video: VideoMetadata = {
        id: updatedVideo.id,
        filename: updatedVideo.filename,
        file_path: updatedVideo.file_path || '',
        file_size: updatedVideo.file_size,
        status: updatedVideo.status,
        created_at: updatedVideo.created_at,
        session_type: updatedVideo.session_type,
        camera_angle: updatedVideo.camera_angle,
        ...(updatedVideo.duration && { duration: updatedVideo.duration }),
        ...(updatedVideo.fps && { fps: updatedVideo.fps }),
        ...(updatedVideo.width && { width: updatedVideo.width }),
        ...(updatedVideo.height && { height: updatedVideo.height }),
        ...(updatedVideo.frame_count && {
          frame_count: updatedVideo.frame_count,
        }),
      };

      onUploadSuccess(video);
    } catch (err: unknown) {
      const axiosError = err as {
        response?: {
          data?: { detail?: string; error?: { message?: string } };
        };
      };
      const detail =
        axiosError.response?.data?.detail ||
        axiosError.response?.data?.error?.message;

      const errorMessage =
        detail || 'Failed to update video details. Please try again.';
      setError(errorMessage);
    } finally {
      setIsUpdatingMetadata(false);
    }
  }, [uploadedVideoId, sessionType, cameraAngle, onUploadSuccess]);

  const handleReplaceFile = useCallback(async () => {
    // If a video was already uploaded, delete it from the server to avoid orphaned videos
    if (uploadedVideoId) {
      try {
        await videoApi.deleteVideo(uploadedVideoId);
      } catch (err) {
        // Log error but don't block the replace action
        // User can manually delete orphaned videos later if needed
        console.warn('Failed to delete replaced video:', err);
      }
    }

    // Reset client state
    setSelectedFile(null);
    setUploadedVideoId(null);
    setUploadStatus('idle');
    setUploadProgress(0);
    setStep(1);
    setSessionType('');
    setCameraAngle('');
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [uploadedVideoId]);

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
    if (uploadStatus !== 'uploading' && fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, [step, uploadStatus]);

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
            className={`upload-area ${isDragOver ? 'drag-over' : ''} ${uploadStatus === 'uploading' ? 'uploading' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={handleAreaClick}
          >
            {uploadStatus === 'uploading' ? (
              <div className="upload-progress">
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
                <p>Uploading... {uploadProgress}%</p>
              </div>
            ) : uploadStatus === 'success' ? (
              <div className="upload-success">
                <div className="upload-icon" aria-hidden="true">
                  <UploadIcon size={48} color="#22c55e" />
                </div>
                <p className="upload-main-text">
                  Uploaded: {selectedFile?.name}
                </p>
                <button
                  type="button"
                  onClick={handleReplaceFile}
                  className="replace-file-btn"
                >
                  Replace file
                </button>
              </div>
            ) : (
              <>
                <div className="upload-icon" aria-hidden="true">
                  <UploadIcon size={48} color="#64748b" />
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
                  disabled={uploadStatus === 'uploading'}
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
              <UploadIcon size={32} color="#22c55e" />
            </div>
            <div className="uploaded-file-details">
              <p className="uploaded-filename">{selectedFile?.name}</p>
              <p className="uploaded-status">Uploaded successfully</p>
            </div>
          </div>

          <div className="details-form">
            <div className={`form-field ${sessionType ? 'selected' : ''}`}>
              <label>
                Session Type <span className="required">(required)</span>
              </label>
              <select
                value={sessionType}
                onChange={(e) => setSessionType(e.target.value)}
                disabled={isUpdatingMetadata}
              >
                <option value="">Select session type</option>
                <option value="serve_practice">Serve Practice</option>
                <option value="match">Match</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className={`form-field ${cameraAngle ? 'selected' : ''}`}>
              <label>
                Camera Angle <span className="optional">(optional)</span>
              </label>
              <select
                value={cameraAngle}
                onChange={(e) => setCameraAngle(e.target.value)}
                disabled={isUpdatingMetadata}
              >
                <option value="">Select camera angle</option>
                <option value="behind">Behind</option>
                <option value="profile">Profile</option>
                <option value="diagonal">Diagonal</option>
                <option value="unknown">Unknown</option>
              </select>
            </div>

            <div className="finish-upload-actions">
              <button
                type="button"
                onClick={handleReplaceFile}
                className="replace-file-btn-secondary"
                disabled={isUpdatingMetadata}
              >
                Replace file
              </button>
              <button
                type="button"
                onClick={handleFinishUpload}
                className="finish-upload-btn"
                disabled={!sessionType || isUpdatingMetadata}
              >
                {isUpdatingMetadata ? 'Finishing...' : 'Finish upload'}
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
