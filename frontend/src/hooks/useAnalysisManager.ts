import { useCallback, useEffect, useState } from 'react';
import { AnalysisData } from '../services/api';
import unifiedAnalysisApi, {
  AnalysisRequest,
} from '../services/unifiedAnalysisApi';
import { AnalysisProgress, useAnalysisProgress } from './useAnalysisProgress';

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

  const handleProgress = useCallback((progress: AnalysisProgress) => {
    setAnalysisState((prev) => ({
      ...prev,
      status: progress.status as AnalysisState['status'],
      progress: progress.progress,
      error: null,
    }));
  }, []);

  // Use the new unified analysis progress hook
  const { startPolling, stopPolling, isPolling } = useAnalysisProgress({
    onComplete: handleComplete,
    onError: handleError,
    onProgress: handleProgress,
  });

  // Check for active jobs on mount and resume polling if found
  useEffect(() => {
    let isMounted = true;

    const checkForActiveJobs = async () => {
      try {
        // Get all active tasks
        const tasksResponse = await unifiedAnalysisApi.listTasks();

        // Find active job for this video
        const activeJob = Object.values(tasksResponse.tasks).find(
          (task) =>
            task.video_id === videoId &&
            (task.status === 'queued' || task.status === 'processing')
        );

        if (activeJob && isMounted) {
          // Found an active job, resume polling
          // Use functional update to check current state atomically
          setAnalysisState((prev) => {
            // Only resume if still in idle state (avoid race conditions)
            if (prev.status === 'idle' && !prev.jobId) {
              // Update state and start polling
              startPolling(activeJob.job_id);
              return {
                ...prev,
                status: 'processing',
                jobId: activeJob.job_id,
                progress: activeJob.progress || 0,
                error: null,
              };
            }
            return prev;
          });
        }
      } catch (err) {
        // Silently fail - user can still manually start analysis
        // This prevents blocking the UI if the API call fails
        console.debug('Failed to check for active jobs:', err);
      }
    };

    // Check on mount or when videoId changes
    // On mount, state will be 'idle', so we'll check for active jobs
    checkForActiveJobs();

    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [videoId]); // Only run when videoId changes (on mount or when switching videos)

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
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
          code?: string;
        };
        let errorMessage: string;

        if (axiosError?.code === 'ECONNABORTED') {
          errorMessage =
            'Request timed out. The server may be busy or Redis may be unavailable.';
        } else {
          // Error detail is already normalized to string by axios interceptor
          errorMessage =
            axiosError?.response?.data?.detail ||
            axiosError?.message ||
            'Failed to start analysis';
        }

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
      const axiosError = err as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
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
