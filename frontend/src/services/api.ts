import axios from 'axios';
import {
  VideoListResponse,
  VideoMetadata,
  VideoUploadResponse,
} from '../types/video';
import { supabase } from './supabaseClient';
import { createAuthInterceptor } from '../utils/authInterceptor';

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

// Add auth interceptor to analysisApiInstance (used by analysisApi.startAnalysis)
createAuthInterceptor(analysisApiInstance, 'Analysis API Instance');

// Add request/response interceptors
api.interceptors.request.use(async (config) => {
  const profile = process.env.REACT_APP_PROFILE || 'local';

  // Only add auth headers if profile is not 'local' and supabase is available
  if (profile !== 'local' && supabase) {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
      console.log(
        `[API] ${config.method?.toUpperCase()} ${config.url} - Auth token added (profile: ${profile})`
      );
    } else {
      console.warn(
        `[API] ${config.method?.toUpperCase()} ${config.url} - No session token available (profile: ${profile})`
      );
    }
  } else {
    console.log(
      `[API] ${config.method?.toUpperCase()} ${config.url} - No auth required (profile: ${profile})`
    );
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const statusText = error.response?.statusText;
    const data = error.response?.data;

    if (status === 401) {
      console.error(
        `[API] 401 Unauthorized on ${error.config?.method?.toUpperCase()} ${error.config?.url}`,
        {
          profile: process.env.REACT_APP_PROFILE || 'local',
          detail: data?.detail || 'Not authenticated',
          hasAuthHeader: !!error.config?.headers?.Authorization,
        }
      );
    } else if (status === 429) {
      console.warn(
        `[API] 429 Rate Limit Exceeded on ${error.config?.method?.toUpperCase()} ${error.config?.url}:`,
        data?.detail || 'Rate limit exceeded'
      );
    } else {
      console.error(
        `[API] Error ${status} ${statusText} on ${error.config?.method?.toUpperCase()} ${error.config?.url}:`,
        data || error.message
      );
    }
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

  // Check video analysis status
  getVideoAnalysisStatus: async (
    videoId: number
  ): Promise<{
    video_id: number;
    has_analysis: boolean;
    analysis_types: string[];
  }> => {
    const response = await api.get(`/videos/${videoId}/analysis-status`);
    return response.data;
  },

  // Get overlay data for client-side rendering
  getOverlayData: async (videoId: number): Promise<any> => {
    const response = await api.get(`/videos/${videoId}/overlay-data`);
    return response.data;
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

// New interfaces for task status tracking (RQ-compatible)
export interface TaskStatus {
  job_id: string;
  video_id: number;
  analysis_type: string;
  status: string;
  progress: number;
  error: string | null;
  result: any | null;
  started_at: string | null;
  completed_at: string | null;
  estimated_duration: number | null;
}

export interface TaskListResponse {
  tasks: Record<string, TaskStatus>;
  total_tasks: number;
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
  // Get job status by job ID (RQ)
  getTaskStatus: async (jobId: string): Promise<TaskStatus> => {
    const response = await api.get<TaskStatus>(`/analysis/status/${jobId}`);
    return response.data;
  },

  // Get all active tasks
  getAllTasks: async (): Promise<TaskListResponse> => {
    const response = await api.get<TaskListResponse>('/analysis/tasks');
    return response.data;
  },

  // Get task statistics
  getTaskStats: async (): Promise<TaskStatsResponse> => {
    const response = await api.get<TaskStatsResponse>('/analysis/tasks/stats');
    return response.data;
  },

  // Cancel a job (RQ)
  cancelTask: async (
    jobId: string
  ): Promise<{ message: string; job_id: string }> => {
    const response = await api.delete<{ message: string; job_id: string }>(
      `/analysis/tasks/${jobId}`
    );
    return response.data;
  },
};

export default api;
