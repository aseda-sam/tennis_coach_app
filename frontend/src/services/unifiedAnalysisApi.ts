import axios from 'axios';
import { createAuthInterceptor } from '../utils/authInterceptor';

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
    console.error('Analysis API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Types for the new unified analysis API
export interface AnalysisRequest {
  analysis_type:
    | 'pose_only'
    | 'ball_only'
    | 'video_annotation_only'
    | 'pose_with_annotation';
  confidence_threshold?: number;
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
    | 'ball_only'
    | 'video_annotation_only'
    | 'pose_with_annotation';
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  error?: string;
  result?: any;
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
    const response = await analysisApi.get<TaskStatsResponse>(
      '/analysis/tasks/stats'
    );
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
   * Start ball-only analysis
   */
  async startBallAnalysis(
    videoId: number,
    confidenceThreshold: number = 0.5
  ): Promise<AnalysisResponse> {
    return this.startAnalysis(videoId, {
      analysis_type: 'ball_only',
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
