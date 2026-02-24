import { AnalysisStartResponse } from '../types/analysis';
import { AppConfig } from '../types/config';
import {
  DemoVideoListItem,
  OverlayData,
  VideoListResponse,
  VideoMetadata,
  VideoUploadResponse,
} from '../types/video';
import { getAuthHeaders } from '../utils/authInterceptor';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/v0';
const DEFAULT_TIMEOUT_MS = 30000;

type ApiRequestConfig = {
  params?: Record<string, string | number | boolean | undefined | null>;
  headers?: Record<string, string>;
  timeoutMs?: number;
};

type ApiResponse<T = any> = {
  data: T;
  status: number;
};

type ApiErrorResponseData = {
  detail?: string;
  [key: string]: unknown;
};

type ApiErrorLike = Error & {
  response?: {
    status?: number;
    data?: ApiErrorResponseData;
  };
  code?: string;
};

class ApiHttpError extends Error {
  response: {
    status: number;
    data: ApiErrorResponseData;
  };

  constructor(status: number, data: ApiErrorResponseData, message?: string) {
    super(message || data?.detail || `Request failed with status ${status}`);
    this.name = 'ApiHttpError';
    this.response = { status, data };
  }
}

function normalizeFastApiDetail(data: unknown): ApiErrorResponseData {
  if (!data || typeof data !== 'object') {
    return { detail: 'Request failed' };
  }

  const payload = data as ApiErrorResponseData;
  const detail = payload.detail;

  if (!Array.isArray(detail)) {
    return payload;
  }

  const messages = detail
    .map((err: { loc?: unknown[]; msg?: string }) => {
      if (typeof err !== 'object' || err === null || !('msg' in err)) {
        return String(err);
      }
      const loc = Array.isArray(err.loc) ? err.loc.slice(1).join('.') : '';
      return loc ? `${loc}: ${err.msg}` : err.msg;
    })
    .filter(Boolean);

  return {
    ...payload,
    detail: messages.length > 0 ? messages.join('; ') : 'Validation error',
  };
}

function buildUrl(path: string, params?: ApiRequestConfig['params']): string {
  const url = new URL(`${API_BASE_URL}${path}`);

  if (!params) {
    return url.toString();
  }

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  });

  return url.toString();
}

async function request<T>(
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  path: string,
  body?: unknown,
  config?: ApiRequestConfig
): Promise<ApiResponse<T>> {
  const controller = new AbortController();
  const timeoutMs = config?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const authHeaders = await getAuthHeaders();
    const headers: Record<string, string> = {
      ...authHeaders,
      ...(config?.headers || {}),
    };

    const isFormData =
      typeof FormData !== 'undefined' && body instanceof FormData;
    if (!isFormData && body !== undefined && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(buildUrl(path, config?.params), {
      method,
      headers,
      body:
        body === undefined
          ? undefined
          : isFormData
            ? (body as FormData)
            : JSON.stringify(body),
      signal: controller.signal,
    });

    const contentType = response.headers.get('content-type') || '';
    const isJson = contentType.includes('application/json');
    const rawData = isJson ? await response.json() : await response.text();

    if (!response.ok) {
      throw new ApiHttpError(
        response.status,
        normalizeFastApiDetail(rawData),
        `Request failed with status ${response.status}`
      );
    }

    return {
      data: rawData as T,
      status: response.status,
    };
  } catch (error) {
    if (error instanceof ApiHttpError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      const timeoutError = new Error('Request timeout') as ApiErrorLike;
      timeoutError.code = 'ECONNABORTED';
      throw timeoutError;
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

const api = {
  get: <T = any>(path: string, config?: ApiRequestConfig) =>
    request<T>('GET', path, undefined, config),
  post: <T = any>(path: string, body?: unknown, config?: ApiRequestConfig) =>
    request<T>('POST', path, body, config),
  patch: <T = any>(path: string, body?: unknown, config?: ApiRequestConfig) =>
    request<T>('PATCH', path, body, config),
  put: <T = any>(path: string, body?: unknown, config?: ApiRequestConfig) =>
    request<T>('PUT', path, body, config),
  delete: <T = any>(path: string, config?: ApiRequestConfig) =>
    request<T>('DELETE', path, undefined, config),
};

export interface VideoFilters {
  camera_angle?: string;
  player_id?: number;
  exclude_player_id?: number;
}

export const videoApi = {
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
    if (isDemo) params.append('is_demo', 'true');
    if (clientRecordedAt) params.append('client_recorded_at', clientRecordedAt);
    if (metadata?.session_type)
      params.append('session_type', metadata.session_type);
    if (metadata?.camera_angle)
      params.append('camera_angle', metadata.camera_angle);

    const queryString = params.toString();
    const response = await api.post<VideoUploadResponse>(
      `/videos/upload${queryString ? `?${queryString}` : ''}`,
      formData
    );
    return response.data;
  },

  getAppConfig: async (): Promise<AppConfig> => {
    const response = await api.get<AppConfig>('/config');
    return response.data;
  },

  getVideos: async (filters?: VideoFilters): Promise<VideoListResponse> => {
    const params = new URLSearchParams();
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value));
        }
      });
    }
    const query = params.toString();
    const url = query ? `/videos/?${query}` : '/videos/';
    const response = await api.get<VideoMetadata[]>(url);
    return {
      videos: response.data,
      total: response.data.length,
    };
  },

  getVideo: async (videoId: number): Promise<VideoMetadata> => {
    const response = await api.get<VideoMetadata>(`/videos/${videoId}`);
    return response.data;
  },

  getDemoVideo: async (): Promise<VideoMetadata> => {
    const response = await api.get<VideoMetadata>('/videos/demo');
    return response.data;
  },

  deleteVideo: async (videoId: number): Promise<void> => {
    await api.delete(`/videos/${videoId}`);
  },

  getVideoUrl: async (
    videoId: number,
    expiresIn: number = 3600
  ): Promise<string> => {
    const response = await api.get<{ url: string; expires_in: number }>(
      `/videos/${videoId}/url?expires_in=${expiresIn}`
    );
    return response.data.url;
  },

  getVideoAnalysisStatus: async (
    videoId: number
  ): Promise<{
    video_id: number;
    has_analysis: boolean;
    analysis_types: string[];
    has_ball_detection: boolean;
    ball_detection_rate: number | null;
    ball_detection_status: string | null;
  }> => {
    const response = await api.get(`/videos/${videoId}/analysis-status`);
    return response.data;
  },

  getContactTimestamps: async (
    videoId: number
  ): Promise<{ contact_timestamps: number[] }> => {
    const response = await api.get<{ ball_contact_timestamps: number[] }>(
      `/videos/${videoId}/ball-contact-timestamps`
    );
    return { contact_timestamps: response.data.ball_contact_timestamps };
  },

  getBulkVideoAnalysisStatus: async (
    videoIds: number[]
  ): Promise<
    {
      video_id: number;
      has_analysis: boolean;
      analysis_types: string[];
      has_ball_detection: boolean;
      ball_detection_rate: number | null;
      ball_detection_status: string | null;
    }[]
  > => {
    const response = await api.post<{
      statuses: {
        video_id: number;
        has_analysis: boolean;
        analysis_types: string[];
        has_ball_detection: boolean;
        ball_detection_rate: number | null;
        ball_detection_status: string | null;
      }[];
    }>('/videos/analysis-status/bulk', { video_ids: videoIds });
    return response.data.statuses;
  },

  getOverlayData: async (videoId: number): Promise<OverlayData> => {
    try {
      const response = await api.get<OverlayData>(
        `/videos/${videoId}/overlay-data`
      );
      return response.data;
    } catch (error: unknown) {
      const apiError = error as ApiErrorLike;
      if (apiError.response?.status === 404) {
        throw new Error(
          'Pose data not found for this video. Please run pose detection analysis first.'
        );
      }
      if (apiError.response?.status === 400) {
        throw new Error(
          apiError.response?.data?.detail ||
            'Invalid request. Please check the video and try again.'
        );
      }
      if (apiError.response?.status === 500) {
        throw new Error(
          'Server error while fetching overlay data. Please try again later.'
        );
      }
      throw error;
    }
  },

  checkAdminStatus: async (): Promise<{ is_admin: boolean }> => {
    const response = await api.get<{ is_admin: boolean }>('/admin/status');
    return response.data;
  },

  listDemoVideos: async (): Promise<DemoVideoListItem[]> => {
    const response = await api.get('/admin/demos');
    return response.data;
  },

  setActiveDemo: async (videoId: number): Promise<VideoMetadata> => {
    const response = await api.post<VideoMetadata>(
      `/admin/demos/${videoId}/set-active`
    );
    return response.data;
  },

  analyzeDemoPose: async (
    videoId: number,
    confidenceThreshold: number = 0.7
  ): Promise<AnalysisStartResponse> => {
    const response = await api.post<AnalysisStartResponse>(
      `/admin/demos/${videoId}/analyze-pose?confidence_threshold=${confidenceThreshold}`
    );
    return response.data;
  },

  updateVideoMetadata: async (
    videoId: number,
    metadata: {
      session_type?: string;
      camera_angle?: string;
      player_tag?: 'you' | 'someone_else';
      title?: string;
      notes?: string;
      recorded_at?: string;
    }
  ): Promise<VideoMetadata> => {
    try {
      const response = await api.patch<VideoMetadata>(
        `/videos/${videoId}/metadata`,
        metadata
      );
      return response.data;
    } catch (error: unknown) {
      const apiError = error as ApiErrorLike;
      if (apiError.response?.status === 404) {
        throw new Error('Video not found. Please check and try again.');
      }
      if (apiError.response?.status === 400) {
        throw new Error(apiError.response?.data?.detail || 'Invalid request.');
      }
      if (apiError.response?.status === 500) {
        throw new Error('Server error. Please try again later.');
      }
      throw error;
    }
  },
};

export default api;
