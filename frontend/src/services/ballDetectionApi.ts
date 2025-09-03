import api from './api';

export interface BallDetectionMetrics {
  total_frames: number;
  frames_with_balls: number;
  total_ball_detections: number;
  detection_rate: number;
  average_ball_confidence?: number;
  min_ball_confidence?: number;
  max_ball_confidence?: number;
  ball_tracking_quality?: number;
  confidence_threshold: number;
  detection_threshold: number;
  processing_time_seconds: number;
  frame_processing_rate?: number;
}

export interface BallDetectionInfo {
  id: number;
  video_id: number;
  metrics: BallDetectionMetrics;
  created_at: string;
  completed_at?: string;
  status: string;
  error_message?: string;
}

export interface BallDetectionRequest {
  confidence_threshold?: number;
  detection_threshold?: number;
  max_frames?: number;
  model_size?: 'nano' | 'small' | 'medium' | 'large';
}

export interface BallDetectionStartResponse {
  ball_detection_id?: number;
  video_filename: string;
  status: string;
  message: string;
  estimated_duration: number;
  task_id?: number;
}

export interface BallDetectionResponse {
  ball_detection: BallDetectionInfo;
  message: string;
}

class BallDetectionApi {
  /**
   * Start ball detection analysis for a video
   */
  async startAnalysis(
    videoId: number,
    request: BallDetectionRequest = {}
  ): Promise<BallDetectionStartResponse> {
    const response = await api.post(
      `/ball-detection/analyze/${videoId}`,
      request
    );
    return response.data;
  }

  /**
   * Get ball detection results for a video
   */
  async getResults(videoId: number): Promise<BallDetectionResponse> {
    const response = await api.get(`/ball-detection/${videoId}`);
    return response.data;
  }

  /**
   * Check if ball detection exists for a video
   */
  async hasAnalysis(videoId: number): Promise<boolean> {
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
   * Get ball detection status for a video
   */
  async getStatus(videoId: number): Promise<string | null> {
    try {
      const result = await this.getResults(videoId);
      return result.ball_detection.status;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  }
}

const ballDetectionApi = new BallDetectionApi();
export default ballDetectionApi;
