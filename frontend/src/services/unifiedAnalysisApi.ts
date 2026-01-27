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

export interface VideoJob {
  id: string;
  video_id: number;
  job_type: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  error?: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
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
   * List video jobs (DB-backed)
   */
  async getVideoJobs(status?: string): Promise<VideoJob[]> {
    const response = await analysisApi.get<VideoJob[]>('/videos/jobs', {
      params: status ? { status } : undefined,
    });
    return response.data;
  }

  /**
   * Get a single VideoJob by ID (DB-backed)
   */
  async getVideoJob(jobId: string): Promise<VideoJob | null> {
    const jobs = await this.getVideoJobs();
    return jobs.find((job) => job.id === jobId) ?? null;
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

}

const unifiedAnalysisApi = new UnifiedAnalysisApi();
export default unifiedAnalysisApi;
