export interface VideoMetadata {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  duration: number;
  width: number;
  height: number;
  fps: number;
  format: string;
  created_at: string;
  updated_at: string;
}

export interface VideoUploadResponse {
  message: string;
  video: VideoMetadata;
}

export interface VideoListResponse {
  videos: VideoMetadata[];
  total: number;
}

export interface ApiError {
  detail: string;
}
