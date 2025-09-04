import React, { useState } from 'react';
import useAnalysisProgress from '../hooks/useAnalysisProgress';
import unifiedAnalysisApi, {
  AnalysisRequest,
} from '../services/unifiedAnalysisApi';

interface AnalysisPanelProps {
  videoId: number;
  onAnalysisComplete?: (result: any) => void;
  onAnalysisError?: (error: string) => void;
}

const AnalysisPanel: React.FC<AnalysisPanelProps> = ({
  videoId,
  onAnalysisComplete,
  onAnalysisError,
}) => {
  const [selectedAnalysisType, setSelectedAnalysisType] =
    useState<AnalysisRequest['analysis_type']>('pose_only');
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.5);
  const [isStarting, setIsStarting] = useState(false);

  const { progress, error, startPolling, stopPolling, isPolling } =
    useAnalysisProgress({
      onComplete: (progress) => {
        console.log('Analysis completed:', progress);
        onAnalysisComplete?.(progress.result);
      },
      onError: (error) => {
        console.error('Analysis error:', error);
        onAnalysisError?.(error);
      },
    });

  const handleStartAnalysis = async () => {
    try {
      setIsStarting(true);

      const request: AnalysisRequest = {
        analysis_type: selectedAnalysisType,
        confidence_threshold: confidenceThreshold,
      };

      const response = await unifiedAnalysisApi.startAnalysis(videoId, request);
      console.log('Analysis started:', response);

      // Start polling for progress
      startPolling(response.task_id);
    } catch (err: any) {
      console.error('Failed to start analysis:', err);
      onAnalysisError?.(err.message || 'Failed to start analysis');
    } finally {
      setIsStarting(false);
    }
  };

  const handleCancelAnalysis = async () => {
    if (progress?.taskId) {
      try {
        await unifiedAnalysisApi.cancelTask(progress.taskId);
        stopPolling();
      } catch (err: any) {
        console.error('Failed to cancel analysis:', err);
      }
    }
  };

  const getAnalysisTypeLabel = (type: AnalysisRequest['analysis_type']) => {
    switch (type) {
      case 'pose_only':
        return 'Pose Detection Only';
      case 'ball_only':
        return 'Ball Detection Only';
      case 'video_annotation_only':
        return 'Video Annotation';
      default:
        return type;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600';
      case 'failed':
      case 'cancelled':
        return 'text-red-600';
      case 'processing':
        return 'text-blue-600';
      case 'queued':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-4">Video Analysis</h3>

      {/* Analysis Configuration */}
      <div className="space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Analysis Type
          </label>
          <select
            value={selectedAnalysisType}
            onChange={(e) =>
              setSelectedAnalysisType(
                e.target.value as AnalysisRequest['analysis_type']
              )
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isPolling || isStarting}
          >
            <option value="pose_only">Pose Detection Only (Fastest)</option>
            <option value="ball_only">Ball Detection Only</option>
            <option value="video_annotation_only">Video Annotation</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Confidence Threshold: {confidenceThreshold}
          </label>
          <input
            type="range"
            min="0.1"
            max="1.0"
            step="0.1"
            value={confidenceThreshold}
            onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
            className="w-full"
            disabled={isPolling || isStarting}
          />
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 mb-6">
        {!isPolling ? (
          <button
            onClick={handleStartAnalysis}
            disabled={isStarting}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStarting
              ? 'Starting...'
              : `Start ${getAnalysisTypeLabel(selectedAnalysisType)}`}
          </button>
        ) : (
          <button
            onClick={handleCancelAnalysis}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
          >
            Cancel Analysis
          </button>
        )}
      </div>

      {/* Progress Display */}
      {progress && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-700">
              {getAnalysisTypeLabel(progress.analysisType)}
            </span>
            <span
              className={`text-sm font-medium ${getStatusColor(progress.status)}`}
            >
              {progress.status.toUpperCase()}
            </span>
          </div>

          {/* Overall Progress */}
          <div>
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>Overall Progress</span>
              <span>{progress.progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress.progress}%` }}
              />
            </div>
          </div>

          {/* Stage Progress */}
          {progress.currentStage && (
            <div>
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>{progress.currentStage}</span>
                {progress.stageProgress !== undefined && (
                  <span>{progress.stageProgress}%</span>
                )}
              </div>
              {progress.stageProgress !== undefined && (
                <div className="w-full bg-gray-200 rounded-full h-1">
                  <div
                    className="bg-green-600 h-1 rounded-full transition-all duration-300"
                    style={{ width: `${progress.stageProgress}%` }}
                  />
                </div>
              )}
            </div>
          )}

          {/* Stage Message */}
          {progress.stageMessage && (
            <p className="text-sm text-gray-600">{progress.stageMessage}</p>
          )}

          {/* Frame Progress */}
          {progress.framesProcessed !== undefined &&
            progress.totalFrames !== undefined && (
              <div className="text-sm text-gray-600">
                Frames: {progress.framesProcessed} / {progress.totalFrames}
              </div>
            )}

          {/* Time Remaining */}
          {progress.estimatedTimeRemaining && (
            <div className="text-sm text-gray-600">
              Estimated time remaining:{' '}
              {Math.round(progress.estimatedTimeRemaining / 1000)}s
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalysisPanel;
