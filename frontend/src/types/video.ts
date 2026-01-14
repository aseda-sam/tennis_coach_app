export interface VideoQualityMetrics {
  quality_score: number;
  blur_score: number;
  lighting_score: number;
  resolution_score: number;
  quality_level: string;
  recommended_confidence_threshold: number;
  frame_count_analyzed: number;
}

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
  // Quality metrics (assessed once on upload)
  quality_score?: number;
  blur_score?: number;
  lighting_score?: number;
  resolution_score?: number;
  quality_level?: string;
  quality_assessed_at?: string;
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
  quality_metrics?: VideoQualityMetrics; // NEW: quality assessment results
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
    details?: any;
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

export interface VideoMetrics {
  video_id: number;
  serve_count: number;
  avg_elbow_angle: number | null;
  total_contacts: number;
  toss_height: number | null;
  contact_height: number | null;
}

export type VideoMetricsByVideo = Record<number, VideoMetrics>;
