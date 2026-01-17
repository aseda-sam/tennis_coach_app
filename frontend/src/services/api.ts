import axios from 'axios';
import {
  OverlayData,
  VideoListResponse,
  VideoMetadata,
  VideoMetrics,
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
    }
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Errors are handled by calling code through error callbacks
    // No need to log here - let the application handle errors appropriately
    return Promise.reject(error);
  }
);

// Normalize analysis data to ensure arrays are always returned
const normalizeAnalysis = (data: unknown): AnalysisData => {
  const analysisData = data as Record<string, unknown>;
  return {
    ...analysisData,
    ball_detections:
      typeof analysisData.ball_detections === 'string'
        ? JSON.parse(analysisData.ball_detections || '[]')
        : (analysisData.ball_detections ?? []),
    pose_detections:
      typeof analysisData.pose_detections === 'string'
        ? JSON.parse(analysisData.pose_detections || '[]')
        : (analysisData.pose_detections ?? []),
    contact_timestamps:
      typeof analysisData.contact_timestamps === 'string'
        ? JSON.parse(analysisData.contact_timestamps as string || '[]')
        : (analysisData.contact_timestamps ?? []),
    contact_detections:
      typeof analysisData.contact_detections === 'string'
        ? JSON.parse(analysisData.contact_detections as string || '[]')
        : (analysisData.contact_detections ?? []),
  } as AnalysisData;
};

export const videoApi = {
  // Upload a video file
  uploadVideo: async (file: File, isDemo: boolean = false): Promise<VideoUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<VideoUploadResponse>(
      `/videos/upload?is_demo=${isDemo}`,
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

  // Get demo video
  getDemoVideo: async (): Promise<VideoMetadata> => {
    const response = await api.get<VideoMetadata>('/videos/demo');
    return response.data;
  },

  // Delete a video
  deleteVideo: async (videoId: number): Promise<void> => {
    await api.delete(`/videos/${videoId}`);
  },

  // Stream original video (legacy - returns stream endpoint URL)
  streamVideo: async (videoId: number): Promise<string> => {
    return `${API_BASE_URL}/videos/${videoId}/stream`;
  },

  // Get signed URL for video (preferred - avoids redirect race conditions)
  getVideoUrl: async (videoId: number, expiresIn: number = 3600): Promise<string> => {
    const response = await api.get<{ url: string; expires_in: number }>(
      `/videos/${videoId}/url?expires_in=${expiresIn}`
    );
    return response.data.url;
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

  // Bulk check video analysis statuses (optimized)
  getBulkVideoAnalysisStatus: async (
    videoIds: number[]
  ): Promise<{
    video_id: number;
    has_analysis: boolean;
    analysis_types: string[];
  }[]> => {
    const response = await api.post<{
      statuses: {
        video_id: number;
        has_analysis: boolean;
        analysis_types: string[];
      }[];
    }>('/videos/analysis-status/bulk', { video_ids: videoIds });
    return response.data.statuses;
  },

  // Get video performance metrics
  getVideoMetrics: async (videoId: number): Promise<VideoMetrics> => {
    const response = await api.get<VideoMetrics>(`/videos/${videoId}/metrics`);
    return response.data;
  },

  // Get overlay data for client-side rendering
  getOverlayData: async (videoId: number): Promise<OverlayData> => {
    try {
      const response = await api.get<OverlayData>(
        `/videos/${videoId}/overlay-data`
      );
      return response.data;
    } catch (error: unknown) {
      const axiosError = error as { response?: { status?: number; data?: { detail?: string } } };
      if (axiosError.response?.status === 404) {
        throw new Error(
          'Pose data not found for this video. Please run pose detection analysis first.'
        );
      }
      if (axiosError.response?.status === 400) {
        throw new Error(
          axiosError.response?.data?.detail ||
            'Invalid request. Please check the video and try again.'
        );
      }
      if (axiosError.response?.status === 500) {
        throw new Error(
          'Server error while fetching overlay data. Please try again later.'
        );
      }
      throw error;
    }
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
  contact_detections?: unknown[];
  ball_detections: unknown[];
  pose_detections: unknown[];
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
  result: AnalysisData | null;
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
