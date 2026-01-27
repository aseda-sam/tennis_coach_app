import { useCallback, useEffect, useRef, useState } from 'react';
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
    error: null,
  });
  const [isLoading] = useState(false);
  const shouldStartPollingRef = useRef<string | null>(null);

  // Memoize callbacks to prevent infinite re-renders
  const handleComplete = useCallback(
    (progress: AnalysisProgress) => {
      setAnalysisState((prev) => ({
        ...prev,
        status: 'completed',
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
        const jobs = await unifiedAnalysisApi.getVideoJobs('queued,processing');

        // Find active job for this video
        const activeJob = jobs.find(
          (job) =>
            job.video_id === videoId &&
            (job.status === 'queued' || job.status === 'processing')
        );

        if (activeJob && isMounted) {
          // Found an active job, resume polling
          // Check current state and update atomically, but keep side effect outside
          setAnalysisState((prev) => {
            // Only resume if still in idle state (avoid race conditions)
            if (prev.status === 'idle' && !prev.jobId) {
              // Store job_id in ref to start polling outside setState callback
              shouldStartPollingRef.current = activeJob.id;
              return {
                ...prev,
                status: 'processing',
                jobId: activeJob.id,
                error: null,
              };
            }
            return prev;
          });
          // Start polling outside setState callback (side effect)
          // This ensures React best practices - side effects not in state updaters
          if (shouldStartPollingRef.current) {
            startPolling(shouldStartPollingRef.current);
            shouldStartPollingRef.current = null;
          }
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
      shouldStartPollingRef.current = null;
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
          error: null,
        }));

        const response = await unifiedAnalysisApi.startAnalysis(
          videoId,
          analysisRequest
        );

        setAnalysisState((prev) => ({
          ...prev,
          status: 'processing',
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
