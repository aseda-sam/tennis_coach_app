import { useCallback, useState } from 'react';
import unifiedAnalysisApi, {
  AnalysisRequest,
} from '../services/unifiedAnalysisApi';
import { useAnalysisProgress } from './useAnalysisProgress';

interface AnalysisState {
  videoId: number;
  taskId: number | null;
  status:
    | 'idle'
    | 'starting'
    | 'processing'
    | 'completed'
    | 'failed'
    | 'cancelled';
  progress: number;
  currentStage?: string;
  stageProgress?: number;
  stageMessage?: string;
  error: string | null;
}

interface UseAnalysisManagerOptions {
  videoId: number;
  autoRefresh?: boolean;
  onAnalysisComplete?: (result: any) => void;
  onAnalysisError?: (error: string) => void;
}

interface UseAnalysisManagerResult {
  analysisState: AnalysisState;
  startAnalysis: (analysisRequest: AnalysisRequest) => Promise<void>;
  refreshAnalysis: () => Promise<void>;
  cancelAnalysis: () => Promise<void>;
  isLoading: boolean;
}

export const useAnalysisManager = ({
  videoId,
  autoRefresh = true,
  onAnalysisComplete,
  onAnalysisError,
}: UseAnalysisManagerOptions): UseAnalysisManagerResult => {
  const [analysisState, setAnalysisState] = useState<AnalysisState>({
    videoId,
    taskId: null,
    status: 'idle',
    progress: 0,
    error: null,
  });
  const [isLoading] = useState(false);

  // Use the new unified analysis progress hook
  const { startPolling, stopPolling, isPolling } = useAnalysisProgress({
    onComplete: (progress) => {
      setAnalysisState((prev) => ({
        ...prev,
        status: 'completed',
        progress: 100,
        taskId: null,
        error: null,
      }));
      onAnalysisComplete?.(progress.result);
    },
    onError: (error) => {
      setAnalysisState((prev) => ({
        ...prev,
        status: 'failed',
        error,
        progress: 0,
        taskId: null,
      }));
      onAnalysisError?.(error);
    },
    onProgress: (progress) => {
      setAnalysisState((prev) => ({
        ...prev,
        status: progress.status as AnalysisState['status'],
        progress: progress.progress,
        currentStage: progress.currentStage,
        stageProgress: progress.stageProgress,
        stageMessage: progress.stageMessage,
        error: null,
      }));
    },
  });

  // Function to start analysis using the new unified API
  const startAnalysis = useCallback(
    async (analysisRequest: AnalysisRequest) => {
      try {
        setAnalysisState((prev) => ({
          ...prev,
          status: 'starting',
          progress: 0,
          error: null,
        }));

        const response = await unifiedAnalysisApi.startAnalysis(
          videoId,
          analysisRequest
        );

        setAnalysisState((prev) => ({
          ...prev,
          status: 'processing',
          progress: 0,
          taskId: response.task_id,
        }));

        // Start polling for progress
        startPolling(response.task_id);
      } catch (err: any) {
        const errorMessage =
          err?.response?.data?.detail ||
          err?.message ||
          'Failed to start analysis';
        setAnalysisState((prev) => ({
          ...prev,
          status: 'failed',
          error: errorMessage,
          progress: 0,
          taskId: null,
        }));

        if (onAnalysisError) {
          onAnalysisError(errorMessage);
        }
      }
    },
    [videoId, startPolling, onAnalysisError]
  );

  // Function to cancel analysis
  const cancelAnalysis = useCallback(async () => {
    if (!analysisState.taskId) return;

    try {
      await unifiedAnalysisApi.cancelTask(analysisState.taskId);
      stopPolling();
      setAnalysisState((prev) => ({
        ...prev,
        status: 'cancelled',
        progress: 0,
        taskId: null,
      }));
    } catch (err: any) {
      const errorMessage =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to cancel analysis';
      setAnalysisState((prev) => ({
        ...prev,
        error: errorMessage,
      }));
    }
  }, [analysisState.taskId, stopPolling]);

  // Function to refresh analysis data (placeholder for now)
  const refreshAnalysis = useCallback(async () => {
    // For now, just reset to idle state
    // In the future, we could check for existing analysis results
    setAnalysisState((prev) => ({
      ...prev,
      status: 'idle',
      progress: 0,
      error: null,
      taskId: null,
    }));
  }, []);

  return {
    analysisState,
    startAnalysis,
    refreshAnalysis,
    cancelAnalysis,
    isLoading: isLoading || isPolling,
  };
};
