import React, { useCallback, useRef, useState } from 'react';
import { videoApi } from '../services/api';
import { VideoMetadata } from '../types/video';
import { UploadIcon } from './Icons';
import { useAuth } from '../hooks/useAuth';
import './VideoUpload.css';

interface VideoUploadProps {
  onUploadSuccess: (video: VideoMetadata) => void;
}

const VideoUpload: React.FC<VideoUploadProps> = ({ onUploadSuccess }) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isDemo, setIsDemo] = useState(false);
  const [sessionType, setSessionType] = useState<string>('');
  const [cameraAngle, setCameraAngle] = useState<string>('');
  const { user } = useAuth();

  // Check if user can upload demo videos
  const profile = process.env.REACT_APP_PROFILE || 'local';
  const DEMO_UPLOAD_USER_ID = 'ca4a6fcc-4cdf-435c-a22f-1c8c02ce4c5f';
  const canUploadDemo = profile === 'local' || user?.id === DEMO_UPLOAD_USER_ID;

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

      setIsUploading(true);
      setError(null);
      setUploadProgress(0);

      try {
        // Build query params for session metadata
        const params = new URLSearchParams();
        if (isDemo) {
          params.append('is_demo', 'true');
        }
        if (sessionType) {
          params.append('session_type', sessionType);
        }
        if (cameraAngle) {
          params.append('camera_angle', cameraAngle);
        }

        const response = await videoApi.uploadVideo(file, isDemo, {
          session_type: sessionType || undefined,
          camera_angle: cameraAngle || undefined,
        });

        // Create a video object from the response data
        const video: VideoMetadata = {
          id: response.video_id,
          filename: response.filename,
          file_path: '', // This will be filled by the backend
          file_size: response.file_size,
          status: response.status,
          created_at: new Date().toISOString(),
          // Add metadata if available
          ...(response.metadata && {
            duration: response.metadata.duration,
            fps: response.metadata.fps,
            width: response.metadata.width,
            height: response.metadata.height,
            frame_count: response.metadata.frame_count,
          }),
        };

        onUploadSuccess(video);
        setUploadProgress(100);
      } catch (err: unknown) {
        const axiosError = err as {
          response?: {
            data?: { detail?: string; error?: { message?: string } };
          };
        };
        // Handle error responses
        const detail =
          axiosError.response?.data?.detail ||
          axiosError.response?.data?.error?.message;

        // Handle errors
        const errorMessage = detail || 'Upload failed. Please try again.';
        setError(errorMessage);
      } finally {
        setIsUploading(false);
      }
    },
    [onUploadSuccess, isDemo, sessionType, cameraAngle]
  );

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

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        handleFileSelect(files[0]);
      }
    },
    [handleFileSelect]
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
    if (!isUploading && fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, [isUploading]);

  return (
    <div className="video-upload">
      <div
        className={`upload-area ${isDragOver ? 'drag-over' : ''} ${isUploading ? 'uploading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleAreaClick}
      >
        {isUploading ? (
          <div className="upload-progress">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
            <p>Uploading... {uploadProgress}%</p>
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
                disabled={isUploading}
                style={{ display: 'none' }}
              />
            </label>
          </>
        )}
      </div>

      <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {canUploadDemo && (
          <div className="demo-upload-option" style={{ padding: '0.75rem', border: '1px solid #e2e8f0', borderRadius: '0.5rem', backgroundColor: '#f8fafc' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={isDemo}
                onChange={(e) => setIsDemo(e.target.checked)}
                disabled={isUploading}
              />
              <span style={{ fontSize: '0.875rem', color: '#475569' }}>
                Upload as demo video (public, accessible to all users)
              </span>
            </label>
          </div>
        )}

        <div style={{ padding: '0.75rem', border: '1px solid #e2e8f0', borderRadius: '0.5rem', backgroundColor: '#f8fafc' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500', color: '#475569' }}>
            Session Type (optional)
          </label>
          <select
            value={sessionType}
            onChange={(e) => setSessionType(e.target.value)}
            disabled={isUploading}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #cbd5e1' }}
          >
            <option value="">Select session type</option>
            <option value="serve_drill">Serve Drill</option>
            <option value="match">Match</option>
            <option value="practice">Practice</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div style={{ padding: '0.75rem', border: '1px solid #e2e8f0', borderRadius: '0.5rem', backgroundColor: '#f8fafc' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: '500', color: '#475569' }}>
            Camera Angle (optional)
          </label>
          <select
            value={cameraAngle}
            onChange={(e) => setCameraAngle(e.target.value)}
            disabled={isUploading}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #cbd5e1' }}
          >
            <option value="">Select camera angle</option>
            <option value="behind">Behind</option>
            <option value="profile">Profile</option>
            <option value="diagonal">Diagonal</option>
            <option value="unknown">Unknown</option>
          </select>
        </div>
      </div>

      <div className="upload-guidance">
        <h3 className="guidance-title">What videos work best?</h3>
        <ul className="guidance-list">
          <li>Record from the side or slightly behind for serves</li>
          <li>Capture your full body in frame</li>
          <li>Good lighting helps us see your form clearly</li>
          <li>Videos should be at least a few seconds long</li>
        </ul>
        <p className="file-info">
          Supported formats: MP4, AVI, MOV, WMV, FLV • Maximum size: 100MB
        </p>
      </div>

      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default VideoUpload;
