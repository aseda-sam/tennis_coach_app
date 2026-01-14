import React, { useState } from 'react';
import {
  useAnalysisStatus,
  AnalysisState,
} from '../hooks/useAnalysisStatus';
import unifiedAnalysisApi, {
  AnalysisRequest,
} from '../services/unifiedAnalysisApi';
import { clsx } from 'clsx';

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

  const { state, error, startPolling, stopPolling, isPolling, refetch } =
    useAnalysisStatus({
      onComplete: (completedState) => {
        console.log('Analysis completed:', completedState);
        onAnalysisComplete?.(completedState.result);
      },
      onError: (failedState) => {
        console.error('Analysis error:', failedState.error);
        onAnalysisError?.(failedState.error);
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
      startPolling(response.job_id);
    } catch (err: any) {
      console.error('Failed to start analysis:', err);
      onAnalysisError?.(err.message || 'Failed to start analysis');
    } finally {
      setIsStarting(false);
    }
  };

  const handleCancelAnalysis = async () => {
    if (state.status !== 'idle' && 'jobId' in state) {
      try {
        await unifiedAnalysisApi.cancelTask(state.jobId);
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

  const getStatusBadge = (status: AnalysisState['status']) => {
    const baseClasses =
      'px-2 py-1 text-xs font-medium rounded-full transition-colors duration-200';
    switch (status) {
      case 'completed':
        return clsx(baseClasses, 'bg-green-100 text-green-700');
      case 'failed':
        return clsx(baseClasses, 'bg-red-100 text-red-700');
      case 'processing':
        return clsx(baseClasses, 'bg-blue-100 text-blue-700');
      case 'queued':
        return clsx(baseClasses, 'bg-yellow-100 text-yellow-700');
      default:
        return clsx(baseClasses, 'bg-gray-100 text-gray-700');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 transition-shadow duration-200">
      <h3 className="text-lg font-semibold mb-4 text-gray-900">Video Analysis</h3>

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
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors duration-200"
          >
            Cancel Analysis
          </button>
        )}
      </div>

      {/* Status Display - Status-first UX */}
      {state.status !== 'idle' && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">
              {getAnalysisTypeLabel(
                state.status === 'queued' || state.status === 'processing'
                  ? selectedAnalysisType
                  : 'pose_only'
              )}
            </span>
            <span className={getStatusBadge(state.status)}>
              {state.status.toUpperCase()}
            </span>
          </div>

          {/* Status Messages */}
          {state.status === 'queued' && (
            <div className="text-sm text-gray-600">
              Analysis started. You can leave this page.
            </div>
          )}

          {state.status === 'processing' && (
            <div className="text-sm text-gray-600">
              Processing... This may take a few minutes.
            </div>
          )}

          {state.status === 'completed' && (
            <div className="text-sm text-green-600">
              Analysis completed successfully!
            </div>
          )}

          {state.status === 'failed' && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-600">{state.error}</p>
            </div>
          )}

          {/* Error Display (from hook) */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-md p-3">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Manual Refresh Button */}
          {state.status !== 'completed' && state.status !== 'failed' && (
            <button
              onClick={refetch}
              className="text-sm text-blue-600 hover:text-blue-700 underline transition-colors duration-200"
            >
              Refresh status
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalysisPanel;
