import type {
  AnalysisRequest,
  AnalysisResponse,
  CancellationResponse,
  VideoJob,
} from '../types/analysis';
import api from './api';

export type {
  AnalysisRequest,
  AnalysisResponse,
  CancellationResponse,
  VideoJob,
} from '../types/analysis';

export const unifiedAnalysisApi = {
  /** Start a background analysis task for a video */
  startAnalysis: async (
    videoId: number,
    request: AnalysisRequest
  ): Promise<AnalysisResponse> => {
    const response = await api.post<AnalysisResponse>(
      `/analysis/videos/${videoId}`,
      request
    );
    return response.data;
  },

  /** List video jobs (DB-backed) */
  getVideoJobs: async (status?: string): Promise<VideoJob[]> => {
    const response = await api.get<VideoJob[]>('/videos/jobs', {
      params: status ? { status } : undefined,
    });
    return response.data;
  },

  /** Get a single VideoJob by ID (DB-backed) */
  getVideoJob: async (jobId: string): Promise<VideoJob | null> => {
    try {
      const response = await api.get<VideoJob>(`/videos/jobs/${jobId}`);
      return response.data;
    } catch (error: unknown) {
      const axiosError = error as { response?: { status?: number } };
      if (axiosError?.response?.status === 404) {
        return null;
      }
      throw error;
    }
  },

  /** Cancel a running background job */
  cancelTask: async (jobId: string): Promise<CancellationResponse> => {
    const response = await api.delete<CancellationResponse>(
      `/analysis/tasks/${jobId}`
    );
    return response.data;
  },
};

export default unifiedAnalysisApi;
