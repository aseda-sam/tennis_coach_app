export interface VideoMetadata {
  filename: string;
  file_size: number;
  duration?: number;
  width?: number;
  height?: number;
  fps?: number;
  frame_count?: number;
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
