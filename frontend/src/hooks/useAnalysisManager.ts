import { useCallback, useState } from 'react';
import unifiedAnalysisApi, {
  AnalysisRequest,
} from '../services/unifiedAnalysisApi';
import {
  useAnalysisProgress,
  AnalysisProgress,
} from './useAnalysisProgress';
import { AnalysisData } from '../services/api';

interface AnalysisState {
  videoId: number;
  jobId: string | null;
  status:
    | 'idle'
    | 'starting'
    | 'processing'
    | 'completed'
    | 'failed'
    | 'cancelled';
  progress: number;
  error: string | null;
}

interface UseAnalysisManagerOptions {
  videoId: number;
  autoRefresh?: boolean;
  onAnalysisComplete?: (result: AnalysisData | null) => void;
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
    jobId: null,
    status: 'idle',
    progress: 0,
    error: null,
  });
  const [isLoading] = useState(false);

  // Memoize callbacks to prevent infinite re-renders
  const handleComplete = useCallback(
    (progress: AnalysisProgress) => {
      setAnalysisState((prev) => ({
        ...prev,
        status: 'completed',
        progress: 100,
        jobId: null,
        error: null,
      }));
      onAnalysisComplete?.(progress.result ?? null);
    },
    [onAnalysisComplete]
  );

  const handleError = useCallback(
    (error: string) => {
      setAnalysisState((prev) => ({
        ...prev,
        status: 'failed',
        error,
        progress: 0,
        jobId: null,
      }));
      onAnalysisError?.(error);
    },
    [onAnalysisError]
  );

  const handleProgress = useCallback(
    (progress: AnalysisProgress) => {
      setAnalysisState((prev) => ({
        ...prev,
        status: progress.status as AnalysisState['status'],
        progress: progress.progress,
        error: null,
      }));
    },
    []
  );

  // Use the new unified analysis progress hook
  const { startPolling, stopPolling, isPolling } = useAnalysisProgress({
    onComplete: handleComplete,
    onError: handleError,
    onProgress: handleProgress,
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
          jobId: response.job_id,
        }));

        // Start polling for progress
        startPolling(response.job_id);
      } catch (err: unknown) {

        const axiosError = err as { response?: { data?: { detail?: string } }; message?: string; code?: string };
        const errorMessage =
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          (axiosError?.code === 'ECONNABORTED'
            ? 'Request timed out. The server may be busy or Redis may be unavailable.'
            : 'Failed to start analysis');
        setAnalysisState((prev) => ({
          ...prev,
          status: 'failed',
          error: errorMessage,
          progress: 0,
          jobId: null,
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
    if (!analysisState.jobId) return;

    try {
      await unifiedAnalysisApi.cancelTask(analysisState.jobId);
      stopPolling();
      setAnalysisState((prev) => ({
        ...prev,
        status: 'cancelled',
        progress: 0,
        jobId: null,
      }));
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: string } }; message?: string };
      const errorMessage =
        axiosError?.response?.data?.detail ||
        axiosError?.message ||
        'Failed to cancel analysis';
      setAnalysisState((prev) => ({
        ...prev,
        error: errorMessage,
      }));
    }
  }, [analysisState.jobId, stopPolling]);

  // Function to refresh analysis data (placeholder for now)
  const refreshAnalysis = useCallback(async () => {
    // For now, just reset to idle state
    // In the future, we could check for existing analysis results
    setAnalysisState((prev) => ({
      ...prev,
      status: 'idle',
      progress: 0,
      error: null,
      jobId: null,
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
