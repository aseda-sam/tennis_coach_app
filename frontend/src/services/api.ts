import axios from 'axios';
import {
  OverlayData,
  VideoListResponse,
  VideoMetadata,
  VideoUploadResponse,
} from '../types/video';
import { createAuthInterceptor } from '../utils/authInterceptor';
import { supabase } from './supabaseClient';

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

// Normalize errors for analysisApiInstance too
analysisApiInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    // Normalize FastAPI error responses to always have string detail
    if (
      error.response?.data?.detail &&
      Array.isArray(error.response.data.detail)
    ) {
      const messages = error.response.data.detail
        .map((err: { type?: string; loc?: unknown[]; msg?: string }) => {
          if (typeof err === 'object' && err !== null && 'msg' in err) {
            const loc = Array.isArray(err.loc)
              ? err.loc.slice(1).join('.')
              : '';
            return loc ? `${loc}: ${err.msg}` : err.msg;
          }
          return String(err);
        })
        .filter(Boolean);
      error.response.data.detail =
        messages.length > 0 ? messages.join('; ') : 'Validation error';
    }
    return Promise.reject(error);
  }
);

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
    // Normalize FastAPI error responses to always have string detail
    // FastAPI validation errors return detail as array: [{type, loc, msg, input}]
    if (
      error.response?.data?.detail &&
      Array.isArray(error.response.data.detail)
    ) {
      const messages = error.response.data.detail
        .map((err: { type?: string; loc?: unknown[]; msg?: string }) => {
          if (typeof err === 'object' && err !== null && 'msg' in err) {
            const loc = Array.isArray(err.loc)
              ? err.loc.slice(1).join('.')
              : '';
            return loc ? `${loc}: ${err.msg}` : err.msg;
          }
          return String(err);
        })
        .filter(Boolean);
      error.response.data.detail =
        messages.length > 0 ? messages.join('; ') : 'Validation error';
    }
    return Promise.reject(error);
  }
);

export const videoApi = {
  // Upload a video file
  uploadVideo: async (
    file: File,
    isDemo: boolean = false,
    metadata?: {
      session_type?: string;
      camera_angle?: string;
    }
  ): Promise<VideoUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams();
    if (isDemo) {
      params.append('is_demo', 'true');
    }
    if (metadata?.session_type) {
      params.append('session_type', metadata.session_type);
    }
    if (metadata?.camera_angle) {
      params.append('camera_angle', metadata.camera_angle);
    }

    const queryString = params.toString();
    const response = await api.post<VideoUploadResponse>(
      `/videos/upload${queryString ? `?${queryString}` : ''}`,
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
  getVideoUrl: async (
    videoId: number,
    expiresIn: number = 3600
  ): Promise<string> => {
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
  ): Promise<
    {
      video_id: number;
      has_analysis: boolean;
      analysis_types: string[];
    }[]
  > => {
    const response = await api.post<{
      statuses: {
        video_id: number;
        has_analysis: boolean;
        analysis_types: string[];
      }[];
    }>('/videos/analysis-status/bulk', { video_ids: videoIds });
    return response.data.statuses;
  },

  // Get overlay data for client-side rendering
  getOverlayData: async (videoId: number): Promise<OverlayData> => {
    try {
      const response = await api.get<OverlayData>(
        `/videos/${videoId}/overlay-data`
      );
      return response.data;
    } catch (error: unknown) {
      const axiosError = error as {
        response?: { status?: number; data?: { detail?: string } };
      };
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

  // Update video metadata (session_type and camera_angle)
  updateVideoMetadata: async (
    videoId: number,
    metadata: {
      session_type?: string;
      camera_angle?: string;
    }
  ): Promise<VideoMetadata> => {
    try {
      const response = await api.patch<VideoMetadata>(
        `/videos/${videoId}/metadata`,
        metadata
      );
      return response.data;
    } catch (error: unknown) {
      const axiosError = error as {
        response?: { status?: number; data?: { detail?: string } };
      };
      if (axiosError.response?.status === 404) {
        throw new Error('Video not found. Please check and try again.');
      }
      if (axiosError.response?.status === 400) {
        throw new Error(
          axiosError.response?.data?.detail || 'Invalid request.'
        );
      }
      if (axiosError.response?.status === 500) {
        throw new Error('Server error. Please try again later.');
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
  processing_time: number;
  model_used?: string;
  confidence_threshold?: number;
  include_pose_detection?: boolean;
  frames_with_pose?: number;
  pose_detection_rate?: number;
  pose_detections: unknown[];
  created_at: string;
  updated_at?: string;
  // New timing information
  timing?: {
    frame_extraction?: number;
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

  // Task status tracking methods
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
    const response = await api.get<TaskStatsResponse>('/analysis/stats');
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
