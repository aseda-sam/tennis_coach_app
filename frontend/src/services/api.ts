import axios from 'axios';
import { AppConfig } from '../types/config';
import {
  DemoVideoListItem,
  OverlayData,
  VideoListResponse,
  VideoMetadata,
  VideoUploadResponse,
} from '../types/video';
import { supabase } from './supabaseClient';

// API configuration
const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'http://localhost:8000/v0';

// Create main API instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

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
    clientRecordedAt?: string,
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
    if (clientRecordedAt) {
      params.append('client_recorded_at', clientRecordedAt);
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

  // Get public app configuration (upload limits, etc.)
  getAppConfig: async (): Promise<AppConfig> => {
    const response = await api.get<AppConfig>('/config');
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

  // Get ball contact timestamps for a video (backend: ball-contact-timestamps; UI keeps "contact")
  getContactTimestamps: async (
    videoId: number
  ): Promise<{ contact_timestamps: number[] }> => {
    const response = await api.get<{ ball_contact_timestamps: number[] }>(
      `/videos/${videoId}/ball-contact-timestamps`
    );
    return { contact_timestamps: response.data.ball_contact_timestamps };
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

  // Check if user is admin
  checkAdminStatus: async (): Promise<{ is_admin: boolean }> => {
    const response = await api.get<{ is_admin: boolean }>('/admin/status');
    return response.data;
  },

  // List all demo videos (admin only)
  listDemoVideos: async (): Promise<DemoVideoListItem[]> => {
    const response = await api.get('/admin/demos');
    return response.data;
  },

  // Set active demo (admin only)
  setActiveDemo: async (videoId: number): Promise<VideoMetadata> => {
    const response = await api.post<VideoMetadata>(
      `/admin/demos/${videoId}/set-active`
    );
    return response.data;
  },

  // Trigger pose analysis for demo video (admin only)
  analyzeDemoPose: async (
    videoId: number,
    confidenceThreshold: number = 0.7
  ): Promise<AnalysisStartResponse> => {
    const response = await api.post<AnalysisStartResponse>(
      `/admin/demos/${videoId}/analyze-pose?confidence_threshold=${confidenceThreshold}`
    );
    return response.data;
  },

  // Update video metadata (session_type and camera_angle)
  updateVideoMetadata: async (
    videoId: number,
    metadata: {
      session_type?: string;
      camera_angle?: string;
      player_tag?: 'you' | 'someone_else';
      apply_to_existing_serves?: boolean;
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

export default api;
