import api from './api';

export interface PoseDetectionMetrics {
  total_frames: number;
  frames_with_poses: number;
  total_pose_detections: number;
  detection_rate: number;
  average_pose_confidence?: number;
  min_pose_confidence?: number;
  max_pose_confidence?: number;
  pose_stability_score?: number;
  confidence_threshold: number;
  detection_threshold: number;
  processing_time_seconds: number;
  frame_processing_rate?: number;
}

export interface PoseDetectionInfo {
  id: number;
  video_id: number;
  metrics: PoseDetectionMetrics;
  frame_data?: any; // Frame-by-frame pose data (optional)
  created_at: string;
  completed_at?: string;
  status: string;
  error_message?: string;
}

export interface PoseDetectionRequest {
  confidence_threshold?: number;
  detection_threshold?: number;
  max_frames?: number;
}

export interface PoseDetectionStartResponse {
  pose_detection_id?: number;
  video_filename: string;
  status: string;
  message: string;
  estimated_duration: number;
  task_id?: number;
}

export interface PoseDetectionResponse {
  pose_detection: PoseDetectionInfo;
  message: string;
}

class PoseDetectionApi {
  /**
   * Start pose detection analysis for a video
   */
  async startAnalysis(
    videoId: number,
    request: PoseDetectionRequest = {}
  ): Promise<PoseDetectionStartResponse> {
    const response = await api.post(
      `/pose-detection/analyze/${videoId}`,
      request
    );
    return response.data;
  }

  /**
   * Get pose detection results for a video
   */
  async getResults(videoId: number): Promise<PoseDetectionResponse> {
    const response = await api.get(`/pose-detection/${videoId}`);
    return response.data;
  }

  /**
   * Check if pose detection exists for a video
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
   * Get pose detection status for a video
   */
  async getStatus(videoId: number): Promise<string | null> {
    try {
      const result = await this.getResults(videoId);
      return result.pose_detection.status;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  }
}

const poseDetectionApi = new PoseDetectionApi();
export default poseDetectionApi;
