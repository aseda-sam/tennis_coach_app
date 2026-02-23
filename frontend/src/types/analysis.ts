/** Analysis API types (start response, analysis data, unified analysis). */

export interface AnalysisStartResponse {
  analysis_id: number | null;
  video_filename: string;
  status: string;
  message: string;
  estimated_duration: number | null;
  task_id: number | null;
}

export interface AnalysisData {
  id: number;
  video_id: number;
  video_filename: string;
  analysis_type: string;
  total_frames: number;
  processing_time: number;
  model_used?: string;
  confidence_threshold?: number;
  include_pose_detection?: boolean;
  frames_with_pose?: number;
  pose_detection_rate?: number;
  pose_detections: unknown[];
  created_at: string;
  updated_at?: string;
  timing?: {
    frame_extraction?: number;
    pose_detection?: number;
    frame_annotation?: number;
    video_creation?: number;
    total_analysis?: number;
  };
  confidence_threshold_used?: number;
}

export interface AnalysisRequest {
  analysis_type: 'pose_only';
  confidence_threshold?: number;
  force_reanalysis?: boolean;
}

export interface AnalysisResponse {
  job_id: string;
  video_id: number;
  analysis_type: string;
  status: string;
  message: string;
  estimated_duration?: number;
}

export interface VideoJob {
  id: string;
  video_id: number;
  job_type: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  error?: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
}

export interface CancellationResponse {
  message: string;
  job_id: string;
}
