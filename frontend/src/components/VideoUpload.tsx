import React, { useCallback, useState } from 'react';
import { videoApi } from '../services/api';
import { VideoMetadata } from '../types/video';
import './VideoUpload.css';

interface VideoUploadProps {
  onUploadSuccess: (video: VideoMetadata) => void;
}

const VideoUpload: React.FC<VideoUploadProps> = ({ onUploadSuccess }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileSelect = useCallback(async (file: File) => {
    // Validate file type
    const allowedTypes = ['video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/flv'];
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
      const response = await videoApi.uploadVideo(file);
      onUploadSuccess(response.video);
      setUploadProgress(100);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  }, [onUploadSuccess]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  return (
    <div className="video-upload">
      <h2>Upload Tennis Video</h2>
      
      <div
        className={`upload-area ${isDragOver ? 'drag-over' : ''} ${isUploading ? 'uploading' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
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
            <div className="upload-icon">📁</div>
            <p>Drag and drop your tennis video here</p>
            <p>or</p>
            <label className="file-input-label">
              Choose File
              <input
                type="file"
                accept="video/*"
                onChange={handleFileInput}
                disabled={isUploading}
                style={{ display: 'none' }}
              />
            </label>
            <p className="file-info">
              Supported formats: MP4, AVI, MOV, WMV, FLV<br />
              Maximum size: 100MB
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
    </div>
  );
};

export default VideoUpload;
