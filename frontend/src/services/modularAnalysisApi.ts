import videoQualityApi from './videoQualityApi';
import ballDetectionApi from './ballDetectionApi';
import poseDetectionApi from './poseDetectionApi';

export interface ModularAnalysisRequest {
  include_video_quality?: boolean;
  include_ball_detection?: boolean;
  include_pose_detection?: boolean;
  confidence_threshold?: number;
  detection_threshold?: number;
  max_frames?: number;
}

export interface ModularAnalysisProgress {
  video_quality?: {
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress?: number;
    error?: string;
  };
  ball_detection?: {
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress?: number;
    error?: string;
  };
  pose_detection?: {
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress?: number;
    error?: string;
  };
}

export interface ModularAnalysisResult {
  video_quality?: any;
  ball_detection?: any;
  pose_detection?: any;
  overall_status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  error?: string;
}

class ModularAnalysisApi {
  /**
   * Start comprehensive analysis using modular services
   */
  async startComprehensiveAnalysis(
    videoId: number,
    request: ModularAnalysisRequest = {}
  ): Promise<{
    status: string;
    message: string;
    analysis_id: string;
    progress: ModularAnalysisProgress;
  }> {
    const {
      include_video_quality = true,
      include_ball_detection = true,
      include_pose_detection = true,
      confidence_threshold = 0.5,
      detection_threshold = 0.5,
      max_frames,
    } = request;

    const analysisId = `modular_${videoId}_${Date.now()}`;
    const progress: ModularAnalysisProgress = {};

    try {
      // Start video quality assessment if requested
      if (include_video_quality) {
        try {
          progress.video_quality = { status: 'processing' };
          await videoQualityApi.startAssessment(videoId, { max_frames });
        } catch (error: any) {
          progress.video_quality = {
            status: 'failed',
            error: error.message,
          };
        }
      }

      // Start ball detection if requested
      if (include_ball_detection) {
        try {
          progress.ball_detection = { status: 'processing' };
          await ballDetectionApi.startAnalysis(videoId, {
            confidence_threshold,
            detection_threshold,
            max_frames,
          });
        } catch (error: any) {
          progress.ball_detection = {
            status: 'failed',
            error: error.message,
          };
        }
      }

      // Start pose detection if requested
      if (include_pose_detection) {
        try {
          progress.pose_detection = { status: 'processing' };
          await poseDetectionApi.startAnalysis(videoId, {
            confidence_threshold,
            detection_threshold,
            max_frames,
          });
        } catch (error: any) {
          progress.pose_detection = {
            status: 'failed',
            error: error.message,
          };
        }
      }

      return {
        status: 'processing',
        message: 'Modular analysis started successfully',
        analysis_id: analysisId,
        progress,
      };
    } catch (error: any) {
      return {
        status: 'failed',
        message: error.message || 'Failed to start modular analysis',
        analysis_id: analysisId,
        progress,
      };
    }
  }

  /**
   * Start pose-only analysis (fastest option)
   */
  async startPoseOnlyAnalysis(
    videoId: number,
    request: Omit<ModularAnalysisRequest, 'include_video_quality' | 'include_ball_detection'> = {}
  ) {
    return this.startComprehensiveAnalysis(videoId, {
      ...request,
      include_video_quality: false,
      include_ball_detection: false,
      include_pose_detection: true,
    });
  }

  /**
   * Get comprehensive analysis results
   */
  async getComprehensiveResults(videoId: number): Promise<ModularAnalysisResult> {
    const result: ModularAnalysisResult = {
      overall_status: 'completed',
      progress: 0,
    };

    let completedServices = 0;
    let totalServices = 0;

    try {
      // Get video quality results
      try {
        const qualityResult = await videoQualityApi.getResults(videoId);
        result.video_quality = qualityResult.quality_assessment;
        completedServices++;
      } catch (error) {
        // Service not available or failed
      }
      totalServices++;

      // Get ball detection results
      try {
        const ballResult = await ballDetectionApi.getResults(videoId);
        result.ball_detection = ballResult.ball_detection;
        completedServices++;
      } catch (error) {
        // Service not available or failed
      }
      totalServices++;

      // Get pose detection results
      try {
        const poseResult = await poseDetectionApi.getResults(videoId);
        result.pose_detection = poseResult.pose_detection;
        completedServices++;
      } catch (error) {
        // Service not available or failed
      }
      totalServices++;

      result.progress = totalServices > 0 ? (completedServices / totalServices) * 100 : 0;
      result.overall_status = completedServices > 0 ? 'completed' : 'failed';

      return result;
    } catch (error: any) {
      return {
        overall_status: 'failed',
        progress: 0,
        error: error.message,
      };
    }
  }

  /**
   * Check if any analysis exists for a video
   */
  async hasAnyAnalysis(videoId: number): Promise<boolean> {
    const hasQuality = await videoQualityApi.hasAssessment(videoId);
    const hasBall = await ballDetectionApi.hasAnalysis(videoId);
    const hasPose = await poseDetectionApi.hasAnalysis(videoId);
    
    return hasQuality || hasBall || hasPose;
  }
}

const modularAnalysisApi = new ModularAnalysisApi();
export default modularAnalysisApi;
