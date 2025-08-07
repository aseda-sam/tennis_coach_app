import axios from 'axios';
import { VideoListResponse, VideoMetadata, VideoUploadResponse } from '../types/video';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for video uploads
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`Making ${config.method?.toUpperCase()} request to ${config.url}`);
    return config;
  },
  (error) => {
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
    const response = await api.get<VideoListResponse>('/videos');
    return response.data;
  },

  // Get video details by ID
  getVideo: async (id: string): Promise<VideoMetadata> => {
    const response = await api.get<VideoMetadata>(`/videos/${id}`);
    return response.data;
  },

  // Delete a video
  deleteVideo: async (id: string): Promise<void> => {
    await api.delete(`/videos/${id}`);
  },
};

export default api;
