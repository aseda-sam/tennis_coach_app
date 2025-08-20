import {
  AlertCircle,
  ArrowLeft,
  CheckCircle,
  FileVideo,
  Upload,
} from 'lucide-react';
import React, { useCallback, useState } from 'react';
import { videoApi } from '../services/api';
import { VideoMetadata } from '../types/video';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Progress } from './ui/progress';

interface ModernVideoUploadProps {
  onUploadSuccess: (video: VideoMetadata) => void;
  onBack?: () => void;
}

interface UploadState {
  isUploading: boolean;
  progress: number;
  error: string | null;
  isDragOver: boolean;
  uploadedFile: File | null;
}

const ALLOWED_TYPES = [
  'video/mp4',
  'video/avi',
  'video/mov',
  'video/wmv',
  'video/flv',
];
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

const ModernVideoUpload: React.FC<ModernVideoUploadProps> = ({
  onUploadSuccess,
  onBack,
}) => {
  const [uploadState, setUploadState] = useState<UploadState>({
    isUploading: false,
    progress: 0,
    error: null,
    isDragOver: false,
    uploadedFile: null,
  });

  const validateFile = useCallback((file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return 'Please select a valid video file (MP4, AVI, MOV, WMV, FLV)';
    }

    if (file.size > MAX_FILE_SIZE) {
      return 'File size must be less than 100MB';
    }

    return null;
  }, []);

  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }, []);

  const handleFileUpload = useCallback(
    async (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setUploadState((prev) => ({ ...prev, error: validationError }));
        return;
      }

      setUploadState((prev) => ({
        ...prev,
        isUploading: true,
        error: null,
        progress: 0,
        uploadedFile: file,
      }));

      try {
        const response = await videoApi.uploadVideo(file);

        // Create VideoMetadata from response
        const video: VideoMetadata = {
          id: response.video_id,
          filename: response.filename,
          file_path: '',
          file_size: response.file_size,
          status: response.status,
          created_at: new Date().toISOString(),
          ...(response.metadata && {
            duration: response.metadata.duration,
            fps: response.metadata.fps,
            width: response.metadata.width,
            height: response.metadata.height,
            frame_count: response.metadata.frame_count,
          }),
        };

        setUploadState((prev) => ({ ...prev, progress: 100 }));

        // Brief delay to show completion state
        setTimeout(() => {
          onUploadSuccess(video);
        }, 1000);
      } catch (err: any) {
        const errorMessage =
          err.response?.data?.error?.message ||
          err.response?.data?.detail ||
          'Upload failed. Please try again.';
        setUploadState((prev) => ({
          ...prev,
          error: errorMessage,
          isUploading: false,
          progress: 0,
        }));
      }
    },
    [validateFile, onUploadSuccess]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (!uploadState.isUploading) {
        setUploadState((prev) => ({ ...prev, isDragOver: true }));
      }
    },
    [uploadState.isUploading]
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setUploadState((prev) => ({ ...prev, isDragOver: false }));
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setUploadState((prev) => ({ ...prev, isDragOver: false }));

      if (uploadState.isUploading) return;

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        handleFileUpload(files[0]);
      }
    },
    [uploadState.isUploading, handleFileUpload]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file && !uploadState.isUploading) {
        handleFileUpload(file);
      }
      // Reset input
      e.target.value = '';
    },
    [uploadState.isUploading, handleFileUpload]
  );

  const resetUpload = useCallback(() => {
    setUploadState({
      isUploading: false,
      progress: 0,
      error: null,
      isDragOver: false,
      uploadedFile: null,
    });
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50">
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          {onBack && (
            <Button
              variant="ghost"
              onClick={onBack}
              className="text-slate-600 hover:text-slate-900"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Home
            </Button>
          )}
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">
              Upload Tennis Video
            </h1>
            <p className="text-slate-600">
              Upload your tennis videos for AI-powered analysis and technique
              insights
            </p>
          </div>
        </div>

        {/* Upload Card */}
        <Card className="p-8 glass border-0 shadow-lg">
          {uploadState.progress === 100 && !uploadState.error ? (
            // Success State
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-6 bg-green-100 rounded-full flex items-center justify-center">
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-2">
                Upload Complete!
              </h3>
              <p className="text-slate-600 mb-6">
                Your video has been successfully uploaded and is ready for
                analysis.
              </p>
              <Button onClick={resetUpload} variant="outline">
                Upload Another Video
              </Button>
            </div>
          ) : uploadState.isUploading ? (
            // Uploading State
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-6 bg-blue-100 rounded-full flex items-center justify-center">
                <FileVideo className="h-8 w-8 text-blue-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-2">
                Uploading Video...
              </h3>
              {uploadState.uploadedFile && (
                <div className="mb-6 space-y-2">
                  <p className="text-slate-600">
                    {uploadState.uploadedFile.name}
                  </p>
                  <p className="text-sm text-slate-500">
                    {formatFileSize(uploadState.uploadedFile.size)}
                  </p>
                </div>
              )}
              <div className="max-w-md mx-auto mb-4">
                <Progress value={uploadState.progress} className="h-3" />
              </div>
              <p className="text-slate-600">{uploadState.progress}% complete</p>
            </div>
          ) : (
            // Upload State
            <div
              className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 ${
                uploadState.isDragOver
                  ? 'border-blue-400 bg-blue-50'
                  : uploadState.error
                    ? 'border-red-300 bg-red-50'
                    : 'border-slate-300 hover:border-blue-400 hover:bg-blue-50/50'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="space-y-6">
                <div
                  className={`w-20 h-20 mx-auto rounded-full flex items-center justify-center ${
                    uploadState.error ? 'bg-red-100' : 'bg-blue-100'
                  }`}
                >
                  {uploadState.error ? (
                    <AlertCircle className="h-10 w-10 text-red-600" />
                  ) : (
                    <Upload className="h-10 w-10 text-blue-600" />
                  )}
                </div>

                <div className="space-y-2">
                  <h3 className="text-xl font-semibold text-slate-900">
                    {uploadState.isDragOver
                      ? 'Drop your video here'
                      : 'Drag and drop your tennis video'}
                  </h3>
                  <p className="text-slate-600">or click to browse files</p>
                </div>

                <div className="space-y-4">
                  <label className="inline-block">
                    <Button className="brand-gradient hover:shadow-lg text-white">
                      <Upload className="h-4 w-4 mr-2" />
                      Choose Video File
                    </Button>
                    <input
                      type="file"
                      accept="video/*"
                      onChange={handleFileInput}
                      className="hidden"
                      aria-label="Choose video file"
                    />
                  </label>

                  <div className="flex flex-wrap justify-center gap-2">
                    {ALLOWED_TYPES.map((type) => (
                      <Badge
                        key={type}
                        variant="outline"
                        className="text-xs bg-white"
                      >
                        {type.split('/')[1].toUpperCase()}
                      </Badge>
                    ))}
                  </div>

                  <p className="text-sm text-slate-500">
                    Maximum file size: {formatFileSize(MAX_FILE_SIZE)}
                  </p>
                </div>

                {uploadState.error && (
                  <div className="p-4 bg-red-100 border border-red-200 rounded-lg">
                    <div className="flex items-center gap-3">
                      <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
                      <p className="text-red-700 text-sm">
                        {uploadState.error}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </Card>

        {/* Tips Card */}
        <Card className="mt-8 p-6 bg-blue-50/50 border-blue-200">
          <h4 className="font-semibold text-slate-900 mb-3">
            Tips for Best Results
          </h4>
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 bg-blue-600 rounded-full mt-2 flex-shrink-0"></span>
              <span>Record at 30+ FPS for better ball detection accuracy</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 bg-blue-600 rounded-full mt-2 flex-shrink-0"></span>
              <span>Ensure good lighting and clear view of the court</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 bg-blue-600 rounded-full mt-2 flex-shrink-0"></span>
              <span>Keep the camera steady for best pose detection</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 bg-blue-600 rounded-full mt-2 flex-shrink-0"></span>
              <span>MP4 format recommended for fastest processing</span>
            </li>
          </ul>
        </Card>
      </div>
    </div>
  );
};

export default ModernVideoUpload;
