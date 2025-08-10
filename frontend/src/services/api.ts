import axios from 'axios';
import { VideoListResponse, VideoMetadata, VideoUploadResponse } from '../types/video';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for video uploads
});

// Create a separate instance for analysis requests with longer timeout
const analysisApiInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for analysis requests
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    // If it's a network error (no backend available), show a user-friendly message
    if (error.code === 'ERR_NETWORK' || error.code === 'ECONNREFUSED') {
      console.warn('Backend API not available. Running in demo mode.');
    }
    return Promise.reject(error);
  }
);

export const videoApi = {
  // Upload a video file
  uploadVideo: async (file: File): Promise<VideoUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post<VideoUploadResponse>('/videos/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get list of uploaded videos
  getVideos: async (): Promise<VideoListResponse> => {
    const response = await api.get<VideoMetadata[]>('/videos');
    return {
      videos: response.data,
      total: response.data.length
    };
  },

  // Get video details by ID
  getVideo: async (id: string): Promise<VideoMetadata> => {
    const response = await api.get<VideoMetadata>(`/videos/${id}`);
    return response.data;
  },

  // Delete a video
  deleteVideo: async (filename: string): Promise<void> => {
    await api.delete(`/videos/${filename}`);
  },
};

export interface AnalysisSummary {
  message: string;
  analysis_id?: number;
  processing_time?: number;
  analysis_summary?: {
    total_frames: number;
    frames_with_balls: number;
    total_ball_detections: number;
    average_detections_per_frame: number;
    detection_rate: number;
    frames_with_pose?: number;
    pose_detection_rate?: number;
  };
  frames_processed?: number;
  error?: string;
}

export interface AnalysisData {
  id: number;
  video_filename: string;
  analysis_type: string;
  total_frames: number;
  frames_with_balls: number;
  total_ball_detections: number;
  average_detections_per_frame: number;
  detection_rate: number;
  processing_time: number;
  model_used: string;
  confidence_threshold: number;
  frames_with_pose?: number;
  pose_detection_rate?: number;
  pose_detections?: string;
  annotated_video_path?: string;
}

export const analysisApi = {
  // Start analysis for a video
  startAnalysis: async (videoFilename: string): Promise<AnalysisSummary> => {
    const response = await analysisApiInstance.post<AnalysisSummary>(`/analysis/${videoFilename}`);
    return response.data;
  },

  // Get analysis results for a video
  getAnalysis: async (videoFilename: string): Promise<AnalysisData> => {
    const response = await api.get<AnalysisData>(`/analysis/${videoFilename}`);
    return response.data;
  },

  // Get all analyses
  getAllAnalyses: async (): Promise<AnalysisData[]> => {
    const response = await api.get<AnalysisData[]>('/analysis/');
    return response.data;
  },

  // Delete analysis for a video
  deleteAnalysis: async (videoFilename: string): Promise<void> => {
    await api.delete(`/analysis/${videoFilename}`);
  },

  // Re-analyze video (future endpoint)
  reanalyzeVideo: async (videoFilename: string): Promise<AnalysisSummary> => {
    const response = await analysisApiInstance.post<AnalysisSummary>(`/analysis/${videoFilename}/reanalyze`);
    return response.data;
  },
};

export default api;
