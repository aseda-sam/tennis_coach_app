import axios from 'axios';
import {
  VideoListResponse,
  VideoMetadata,
  VideoUploadResponse,
} from '../types/video';

// API configuration
const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'http://localhost:8000/v0';

// Create axios instance for analysis API
const analysisApiInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Create main API instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Add request/response interceptors
api.interceptors.request.use((config) => {
  console.log(
    `Making ${config.method?.toUpperCase()} request to ${config.url}`
  );
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Normalize analysis data to ensure arrays are always returned
const normalizeAnalysis = (data: any): AnalysisData => ({
  ...data,
  ball_detections:
    typeof data.ball_detections === 'string'
      ? JSON.parse(data.ball_detections || '[]')
      : (data.ball_detections ?? []),
  pose_detections:
    typeof data.pose_detections === 'string'
      ? JSON.parse(data.pose_detections || '[]')
      : (data.pose_detections ?? []),
  contact_timestamps:
    typeof data.contact_timestamps === 'string'
      ? JSON.parse(data.contact_timestamps || '[]')
      : (data.contact_timestamps ?? []),
  contact_detections:
    typeof data.contact_detections === 'string'
      ? JSON.parse(data.contact_detections || '[]')
      : (data.contact_detections ?? []),
});

export const videoApi = {
  // Upload a video file
  uploadVideo: async (file: File): Promise<VideoUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<VideoUploadResponse>(
      '/videos/upload',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  // Get list of uploaded videos
  getVideos: async (): Promise<VideoListResponse> => {
    const response = await api.get<VideoMetadata[]>('/videos/');
    return {
      videos: response.data,
      total: response.data.length,
    };
  },

  // Get video details by ID
  getVideo: async (videoId: number): Promise<VideoMetadata> => {
    const response = await api.get<VideoMetadata>(`/videos/${videoId}`);
    return response.data;
  },

  // Delete a video
  deleteVideo: async (videoId: number): Promise<void> => {
    await api.delete(`/videos/${videoId}`);
  },

  // Stream original video
  streamVideo: async (videoId: number): Promise<string> => {
    return `${API_BASE_URL}/videos/${videoId}/stream`;
  },

  // Stream annotated video
  streamAnnotatedVideo: async (videoId: number): Promise<string> => {
    return `${API_BASE_URL}/videos/${videoId}/annotated/stream`;
  },
};

// Updated to match backend AnalysisStartResponse
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
  video_id: number; // Required since all records now have video_id
  video_filename: string;
  analysis_type: string;
  total_frames: number;
  frames_with_balls: number;
  total_ball_detections: number;
  average_detections_per_frame: number;
  detection_rate: number;
  processing_time: number;
  model_used?: string;
  confidence_threshold?: number;
  include_pose_detection?: boolean;
  frames_with_pose?: number;
  pose_detection_rate?: number;
  contact_frames?: number;
  contact_timestamps?: number[];
  contact_detections?: any[];
  ball_detections: any[];
  pose_detections: any[];
  created_at: string;
  updated_at?: string;
  // New timing information
  timing?: {
    frame_extraction?: number;
    ball_detection?: number;
    pose_detection?: number;
    frame_annotation?: number;
    video_creation?: number;
    total_analysis?: number;
  };
  confidence_threshold_used?: number;
}

// New interfaces for task status tracking
export interface TaskStatus {
  task_id: number;
  video_id: number;
  analysis_type: string;
  status: string;
  progress: number;
  current_stage: string | null;
  stage_progress: number | null;
  stage_message: string | null;
  estimated_time_remaining: number | null;
  frames_processed: number | null;
  total_frames: number | null;
  error: string | null;
  result: any | null;
  started_at: string;
  completed_at: string | null;
}

export interface TaskListResponse {
  tasks: Record<number, TaskStatus>;
  total: number;
}

export interface TaskStatsResponse {
  total_tasks: number;
  status_counts: Record<string, number>;
  active_workers: number;
  max_workers: number;
}

export const analysisApi = {
  // Start analysis for a video - now returns AnalysisStartResponse with task_id
  startAnalysis: async (
    videoId: number,
    analysisRequest: {
      analysis_type: string;
      confidence_threshold?: number;
      include_pose_detection?: boolean;
    }
  ): Promise<AnalysisStartResponse> => {
    const response = await analysisApiInstance.post<AnalysisStartResponse>(
      `/analysis/videos/${videoId}`,
      analysisRequest
    );
    return response.data;
  },

  // Get analysis results by analysis ID
  getAnalysis: async (analysisId: number): Promise<AnalysisData> => {
    const response = await api.get<AnalysisData>(`/analysis/${analysisId}`);
    return normalizeAnalysis(response.data);
  },

  // Get analysis results by video ID
  getAnalysisByVideo: async (videoId: number): Promise<AnalysisData> => {
    const response = await api.get<AnalysisData>(`/analysis/videos/${videoId}`);
    return normalizeAnalysis(response.data);
  },

  // Get all analyses
  getAllAnalyses: async (): Promise<AnalysisData[]> => {
    const response = await api.get<AnalysisData[]>('/analysis/');
    return response.data.map(normalizeAnalysis);
  },

  // Delete analysis by analysis ID
  deleteAnalysis: async (analysisId: number): Promise<void> => {
    await api.delete(`/analysis/${analysisId}`);
  },

  // New methods for task status tracking
  // Get task status by task ID
  getTaskStatus: async (taskId: number): Promise<TaskStatus> => {
    const response = await api.get<TaskStatus>(
      `/analysis/tasks/${taskId}/status`
    );
    return response.data;
  },

  // Get all active tasks
  getAllTasks: async (): Promise<TaskListResponse> => {
    const response = await api.get<TaskListResponse>('/analysis/tasks/');
    return response.data;
  },

  // Get task statistics
  getTaskStats: async (): Promise<TaskStatsResponse> => {
    const response = await api.get<TaskStatsResponse>('/analysis/tasks/stats');
    return response.data;
  },

  // Cancel a task
  cancelTask: async (
    taskId: number
  ): Promise<{ message: string; task_id: number }> => {
    const response = await api.delete<{ message: string; task_id: number }>(
      `/analysis/tasks/${taskId}`
    );
    return response.data;
  },
};

export default api;
