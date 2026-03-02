import React, { useCallback, useState } from 'react';
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
import VideoUploadDropzone from './VideoUploadDropzone';
import VideoUploadMetadataForm from './VideoUploadMetadataForm';
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
    // Demo uploads: camera angle is optional, session type is fixed
    // Regular uploads: session type is required
    if (!uploadedVideoId || (!forceDemo && !sessionType)) {
      return;
    }

    setError(null);

    try {
      const metadata: Record<string, string | undefined> = {
        session_type: forceDemo ? 'serve_practice' : sessionType,
        camera_angle: cameraAngle || undefined,
      };
      if (!forceDemo) {
        metadata.player_tag = playerTag;
      }
      const updatedVideo = await updateMetadataMutation.mutateAsync({
        videoId: uploadedVideoId,
        metadata,
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
    forceDemo,
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

  return (
    <div className="video-upload">
      {/* Step Indicator — hidden for demo uploads (single-step) */}
      {!forceDemo && (
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
      )}

      {step === 1 && (
        <VideoUploadDropzone
          selectedFile={selectedFile}
          isDragOver={isDragOver}
          uploadProgress={uploadProgress}
          isUploading={uploadMutation.isPending}
          isUploadSuccess={uploadMutation.isSuccess}
          isDemo={isDemo}
          canUploadDemo={canUploadDemo}
          hideDemoToggle={hideDemoToggle}
          forceDemo={forceDemo}
          demoNoticeText={demoNoticeText}
          onFileSelect={handleFileSelect}
          onDemoChange={setIsDemo}
          onReplaceFile={handleReplaceFile}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        />
      )}

      {step === 2 && (
        <VideoUploadMetadataForm
          selectedFile={selectedFile}
          sessionType={sessionType}
          cameraAngle={cameraAngle}
          playerTag={playerTag}
          playerLabel={playerLabel}
          isDemo={forceDemo}
          isSubmitting={updateMetadataMutation.isPending}
          onSessionTypeChange={setSessionType}
          onCameraAngleChange={setCameraAngle}
          onPlayerTagChange={setPlayerTag}
          onFinish={handleFinishUpload}
          onReplaceFile={handleReplaceFile}
        />
      )}

      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default VideoUpload;
