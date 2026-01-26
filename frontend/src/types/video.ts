export interface VideoMetadata {
  id: number; // NEW: video ID
  filename: string;
  file_path: string; // NEW: file path
  file_size: number;
  content_type?: string;
  duration?: number;
  width?: number;
  height?: number;
  fps?: number;
  frame_count?: number;
  created_at: string; // NEW: creation timestamp
  updated_at?: string; // NEW: update timestamp
  status: string; // NEW: processing status
  error_message?: string; // NEW: error message if processing failed
  session_type?: string; // Session type: 'serve_practice', 'match', 'other'
  camera_angle?: string; // Camera angle: 'behind', 'profile', 'diagonal', 'unknown'
}

export interface VideoUploadResponse {
  video_id: number; // CHANGED: from video object to video_id
  filename: string;
  file_size: number;
  status: string;
  message: string;
  metadata?: {
    // NEW: metadata object
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
  error: {
    // CHANGED: new error structure
    code: string;
    message: string;
    details?: unknown;
  };
}

export interface PoseFrame {
  frame_index: number;
  timestamp: number;
  keypoints: { [key: string]: number[] }; // {"left_shoulder": [x, y], ...}
  confidence: number;
}

export interface OverlayData {
  video_id: number;
  fps: number;
  total_frames: number;
  width: number;
  height: number;
  frames: PoseFrame[];
}

