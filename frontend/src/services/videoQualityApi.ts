import api from './api';

export interface VideoQualityMetrics {
  quality_score: number;
  blur_score: number;
  lighting_score: number;
  resolution_score: number;
  quality_level: string;
  recommended_confidence_threshold: number;
  frame_count_analyzed: number;
}

export interface VideoQualityInfo {
  id: number;
  video_id: number;
  metrics: VideoQualityMetrics;
  created_at: string;
  completed_at?: string;
  status: string;
  error_message?: string;
}

export interface VideoQualityRequest {
  max_frames?: number;
  sample_rate?: number;
}

export interface VideoQualityStartResponse {
  quality_assessment_id?: number;
  video_filename: string;
  status: string;
  message: string;
  estimated_duration: number;
  task_id?: number;
}

export interface VideoQualityResponse {
  quality_assessment: VideoQualityInfo;
  message: string;
}

class VideoQualityApi {
  /**
   * Start video quality assessment for a video
   */
  async startAssessment(
    videoId: number,
    request: VideoQualityRequest = {}
  ): Promise<VideoQualityStartResponse> {
    const response = await api.post(
      `/v0/video-quality/analyze/${videoId}`,
      request
    );
    return response.data;
  }

  /**
   * Get video quality results for a video
   */
  async getResults(videoId: number): Promise<VideoQualityResponse> {
    const response = await api.get(`/v0/video-quality/${videoId}`);
    return response.data;
  }

  /**
   * Check if video quality assessment exists for a video
   */
  async hasAssessment(videoId: number): Promise<boolean> {
    try {
      await this.getResults(videoId);
      return true;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return false;
      }
      throw error;
    }
  }

  /**
   * Get video quality status for a video
   */
  async getStatus(videoId: number): Promise<string | null> {
    try {
      const result = await this.getResults(videoId);
      return result.quality_assessment.status;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  }
}

const videoQualityApi = new VideoQualityApi();
export default videoQualityApi;
