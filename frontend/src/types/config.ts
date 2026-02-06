export interface UploadLimits {
  max_file_size_bytes: number;
  max_video_duration_seconds: number;
  supported_formats: string[];
}

export interface ServeDetectionConfig {
  low_confidence_threshold: number;
}

export interface AppConfig {
  upload_limits: UploadLimits;
  serve_detection: ServeDetectionConfig;
}
