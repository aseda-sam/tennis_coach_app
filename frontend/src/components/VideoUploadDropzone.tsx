import React, { useCallback, useRef } from 'react';
import { UploadIcon } from './Icons';

interface VideoUploadDropzoneProps {
  selectedFile: File | null;
  isDragOver: boolean;
  uploadProgress: number;
  isUploading: boolean;
  isUploadSuccess: boolean;
  isDemo: boolean;
  canUploadDemo: boolean;
  hideDemoToggle: boolean;
  forceDemo: boolean;
  demoNoticeText?: string;
  onFileSelect: (file: File) => void;
  onDemoChange: (checked: boolean) => void;
  onReplaceFile: () => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
}

const VideoUploadDropzone: React.FC<VideoUploadDropzoneProps> = ({
  selectedFile,
  isDragOver,
  uploadProgress,
  isUploading,
  isUploadSuccess,
  isDemo,
  canUploadDemo,
  hideDemoToggle,
  forceDemo,
  demoNoticeText,
  onFileSelect,
  onDemoChange,
  onReplaceFile,
  onDragOver,
  onDragLeave,
  onDrop,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const handleAreaClick = useCallback(() => {
    if (!isUploading && fileInputRef.current) {
      fileInputRef.current.click();
    }
  }, [isUploading]);

  return (
    <>
      <div
        className={`upload-area ${isDragOver ? 'drag-over' : ''} ${isUploading ? 'uploading' : ''}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
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
        ) : isUploadSuccess ? (
          <div className="upload-success">
            <div className="upload-icon" aria-hidden="true">
              <UploadIcon size={48} color="var(--color-success)" />
            </div>
            <p className="upload-main-text">Uploaded: {selectedFile?.name}</p>
            <button
              type="button"
              onClick={onReplaceFile}
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
              onChange={(e) => onDemoChange(e.target.checked)}
              disabled={isUploading}
            />
            <span>Upload as demo video (public, accessible to all users)</span>
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
  );
};

export default VideoUploadDropzone;
