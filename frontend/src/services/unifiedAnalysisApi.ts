import axios from 'axios';
import { createAuthInterceptor } from '../utils/authInterceptor';
import { AnalysisData } from './api';

// API configuration
const API_BASE_URL =
  process.env.REACT_APP_API_URL || 'http://localhost:8000/v0';

// Create axios instance for unified analysis API
const analysisApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Add request/response interceptors
createAuthInterceptor(analysisApi, 'Analysis API');

analysisApi.interceptors.response.use(
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

// Types for the new unified analysis API
export interface AnalysisRequest {
  analysis_type:
    | 'pose_only'
    | 'video_annotation_only'
    | 'pose_with_annotation'
    | 'contact_metrics';
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

export interface TaskStatus {
  job_id: string;
  video_id: number;
  analysis_type:
    | 'pose_only'
    | 'video_annotation_only'
    | 'pose_with_annotation'
    | 'contact_metrics';
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  error?: string;
  result?: AnalysisData | null;
  started_at?: string;
  completed_at?: string;
  estimated_duration?: number;
}

export interface TaskListResponse {
  tasks: Record<string, TaskStatus>;
  total_tasks: number;
}

export interface TaskStatsResponse {
  total_tasks: number;
  status_counts: Record<string, number>;
  active_workers?: number;
  max_workers?: number;
}

export interface CancellationResponse {
  message: string;
  job_id: string;
}

class UnifiedAnalysisApi {
  /**
   * Start a background analysis task for a video
   */
  async startAnalysis(
    videoId: number,
    request: AnalysisRequest
  ): Promise<AnalysisResponse> {
    const response = await analysisApi.post<AnalysisResponse>(
      `/analysis/videos/${videoId}`,
      request
    );
    return response.data;
  }

  /**
   * Get the status of a background analysis job
   */
  async getTaskStatus(jobId: string): Promise<TaskStatus> {
    const response = await analysisApi.get<TaskStatus>(
      `/analysis/status/${jobId}`
    );
    return response.data;
  }

  /**
   * List all active background tasks
   */
  async listTasks(): Promise<TaskListResponse> {
    const response = await analysisApi.get<TaskListResponse>('/analysis/tasks');
    return response.data;
  }

  /**
   * Get background task system statistics
   */
  async getTaskStats(): Promise<TaskStatsResponse> {
    const response =
      await analysisApi.get<TaskStatsResponse>('/analysis/stats');
    return response.data;
  }

  /**
   * Cancel a running background job
   */
  async cancelTask(jobId: string): Promise<CancellationResponse> {
    const response = await analysisApi.delete<CancellationResponse>(
      `/analysis/tasks/${jobId}`
    );
    return response.data;
  }

  /**
   * Start pose-only analysis (fastest option)
   */
  async startPoseAnalysis(
    videoId: number,
    confidenceThreshold: number = 0.5
  ): Promise<AnalysisResponse> {
    return this.startAnalysis(videoId, {
      analysis_type: 'pose_only',
      confidence_threshold: confidenceThreshold,
    });
  }

  /**
   * Start video annotation analysis
   */
  async startVideoAnnotation(
    videoId: number,
    confidenceThreshold: number = 0.5
  ): Promise<AnalysisResponse> {
    return this.startAnalysis(videoId, {
      analysis_type: 'video_annotation_only',
      confidence_threshold: confidenceThreshold,
    });
  }

  /**
   * Start pose detection with video annotation (recommended for pose analysis)
   */
  async startPoseWithAnnotation(
    videoId: number,
    confidenceThreshold: number = 0.5
  ): Promise<AnalysisResponse> {
    return this.startAnalysis(videoId, {
      analysis_type: 'pose_with_annotation',
      confidence_threshold: confidenceThreshold,
    });
  }

  /**
   * Recompute contact metrics (elbow angles, etc.) using existing pose data
   */
  async startContactMetricsAnalysis(
    videoId: number,
    forceReanalysis: boolean = false
  ): Promise<AnalysisResponse> {
    return this.startAnalysis(videoId, {
      analysis_type: 'contact_metrics',
      force_reanalysis: forceReanalysis,
    });
  }

  /**
   * Poll job status until completion or failure
   */
  async waitForTaskCompletion(
    jobId: string,
    pollInterval: number = 2000,
    maxWaitTime: number = 300000 // 5 minutes
  ): Promise<TaskStatus> {
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitTime) {
      const status = await this.getTaskStatus(jobId);

      if (
        status.status === 'completed' ||
        status.status === 'failed' ||
        status.status === 'cancelled'
      ) {
        return status;
      }

      // Wait before next poll
      await new Promise((resolve) => setTimeout(resolve, pollInterval));
    }

    throw new Error(`Job ${jobId} did not complete within ${maxWaitTime}ms`);
  }

  /**
   * Get job progress with real-time updates
   */
  async *getTaskProgress(
    jobId: string
  ): AsyncGenerator<TaskStatus, void, unknown> {
    while (true) {
      const status = await this.getTaskStatus(jobId);
      yield status;

      if (
        status.status === 'completed' ||
        status.status === 'failed' ||
        status.status === 'cancelled'
      ) {
        break;
      }

      // Wait before next update
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
}

const unifiedAnalysisApi = new UnifiedAnalysisApi();
export default unifiedAnalysisApi;
