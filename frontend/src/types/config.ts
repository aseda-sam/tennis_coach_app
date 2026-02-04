export interface UploadLimits {
  max_file_size_bytes: number;
  max_video_duration_seconds: number;
  supported_formats: string[];
}

export interface AppConfig {
  upload_limits: UploadLimits;
}
