export interface VideoMetadata {
  id: number;                    // NEW: video ID
  filename: string;
  file_path: string;             // NEW: file path
  file_size: number;
  content_type?: string;
  duration?: number;
  width?: number;
  height?: number;
  fps?: number;
  frame_count?: number;
  created_at: string;            // NEW: creation timestamp
  updated_at?: string;           // NEW: update timestamp
  status: string;                // NEW: processing status
  error_message?: string;        // NEW: error message if processing failed
}

export interface VideoUploadResponse {
  video_id: number;              // CHANGED: from video object to video_id
  filename: string;
  file_size: number;
  status: string;
  message: string;
  metadata?: {                   // NEW: metadata object
    duration?: number;
    fps?: number;
    width?: number;
    height?: number;
    frame_count?: number;
  };
}

export interface VideoListResponse {
  videos: VideoMetadata[];
  total: number;
}

export interface ApiError {
  error: {                       // CHANGED: new error structure
    code: string;
    message: string;
    details?: any;
  };
}
