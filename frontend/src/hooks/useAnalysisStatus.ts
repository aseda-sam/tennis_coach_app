import { useCallback, useEffect, useRef, useState } from 'react';
import unifiedAnalysisApi, { VideoJob } from '../services/unifiedAnalysisApi';
import { AnalysisData } from '../services/api';

/**
 * Discriminated union for analysis status state.
 * Following react-frontend.mdc patterns for type safety.
 */
export type AnalysisState =
  | { status: 'idle' }
  | { status: 'queued'; jobId: string; startedAt: string }
  | { status: 'processing'; jobId: string; startedAt: string }
  | {
      status: 'completed';
      jobId: string;
      result: AnalysisData | null;
      completedAt: string;
    }
  | { status: 'failed'; jobId: string; error: string; startedAt: string };

export interface UseAnalysisStatusOptions {
  pollInterval?: number; // milliseconds, default 12000 (12s)
  onComplete?: (state: Extract<AnalysisState, { status: 'completed' }>) => void;
  onError?: (state: Extract<AnalysisState, { status: 'failed' }>) => void;
  onStateChange?: (state: AnalysisState) => void;
}

export interface UseAnalysisStatusReturn {
  state: AnalysisState;
  isLoading: boolean;
  error: string | null;
  startPolling: (jobId: string) => void;
  stopPolling: () => void;
  refetch: () => Promise<void>;
  isPolling: boolean;
}

/**
 * Unified hook for analysis status polling with visibility awareness.
 * Replaces useTaskStatus and useAnalysisProgress hooks.
 *
 * Features:
 * - Visibility-aware: pauses when tab hidden, resumes on focus
 * - Slower polling: defaults to 12s interval (was 2s)
 * - Immediate fetch on tab focus
 * - Stops automatically on terminal states
 * - Proper cleanup with AbortController
 */
export function useAnalysisStatus(
  options: UseAnalysisStatusOptions = {}
): UseAnalysisStatusReturn {
  const {
    pollInterval = 12000, // 12 seconds default (was 2s)
    onComplete,
    onError,
    onStateChange,
  } = options;

  const [state, setState] = useState<AnalysisState>({ status: 'idle' });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const currentJobIdRef = useRef<string | null>(null);
  const isVisibleRef = useRef(true);

  const jobToState = useCallback((job: VideoJob): AnalysisState => {
    switch (job.status) {
      case 'queued':
        return {
          status: 'queued',
          jobId: job.id,
          startedAt: job.started_at || new Date().toISOString(),
        };
      case 'processing':
        return {
          status: 'processing',
          jobId: job.id,
          startedAt: job.started_at || new Date().toISOString(),
        };
      case 'completed':
        return {
          status: 'completed',
          jobId: job.id,
          result: null,
          completedAt: job.finished_at || new Date().toISOString(),
        };
      case 'failed':
        return {
          status: 'failed',
          jobId: job.id,
          error: job.error || 'Job failed',
          startedAt: job.started_at || new Date().toISOString(),
        };
      default:
        return { status: 'idle' };
    }
  }, []);

  // Fetch job status (DB-backed)
  const fetchJobStatus = useCallback(
    async (jobId: string) => {
      if (!jobId) return;

      try {
        setIsLoading(true);
        setError(null);

        // Abort previous request if still pending
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        const job = await unifiedAnalysisApi.getVideoJob(jobId);
        if (!job) {
          const failedState: AnalysisState = {
            status: 'failed',
            jobId,
            error: 'Job not found',
            startedAt: new Date().toISOString(),
          };
          setState(failedState);
          onStateChange?.(failedState);
          setIsPolling(false);
          setIsLoading(false);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          onError?.(failedState);
          return;
        }

        const newState = jobToState(job);

        setState(newState);
        onStateChange?.(newState);

        // Handle terminal states
        if (newState.status === 'completed') {
          setIsPolling(false);
          setIsLoading(false);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          onComplete?.(newState);
          return;
        }

        if (newState.status === 'failed') {
          setIsPolling(false);
          setIsLoading(false);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          onError?.(newState);
          return;
        }
      } catch (err: unknown) {
        const axiosError = err as {
          response?: { status?: number; data?: { detail?: string } };
          message?: string;
        };

        const errorMessage =
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to fetch job status';
        setError(errorMessage);
        setIsLoading(false);
        // Don't stop polling on transient errors - let it retry
      } finally {
        setIsLoading(false);
      }
    },
    [jobToState, onComplete, onError, onStateChange]
  );

  // Poll function that respects visibility
  const poll = useCallback(() => {
    const jobId = currentJobIdRef.current;
    if (!jobId || !isVisibleRef.current) return;
    fetchJobStatus(jobId);
  }, [fetchJobStatus]);

  // Start polling
  const startPolling = useCallback(
    (jobId: string) => {
      // Clear any existing interval
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }

      currentJobIdRef.current = jobId;
      setIsPolling(true);
      setError(null);

      // Fetch immediately
      fetchJobStatus(jobId);

      // Set up interval for continued polling (only when visible)
      intervalRef.current = setInterval(() => {
        if (currentJobIdRef.current === jobId && isVisibleRef.current) {
          poll();
        }
      }, pollInterval);
    },
    [fetchJobStatus, pollInterval, poll]
  );

  // Stop polling
  const stopPolling = useCallback(() => {
    setIsPolling(false);
    currentJobIdRef.current = null;

    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Abort any ongoing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  // Manual refetch
  const refetch = useCallback(async () => {
    const jobId = currentJobIdRef.current;
    if (jobId) {
      await fetchJobStatus(jobId);
    }
  }, [fetchJobStatus]);

  // Visibility API: pause polling when tab hidden, resume on focus
  useEffect(() => {
    const handleVisibilityChange = () => {
      isVisibleRef.current = !document.hidden;

      if (!document.hidden && currentJobIdRef.current && isPolling) {
        // Tab became visible - fetch immediately
        fetchJobStatus(currentJobIdRef.current);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isPolling, fetchJobStatus]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    state,
    isLoading,
    error,
    startPolling,
    stopPolling,
    refetch,
    isPolling,
  };
}

export default useAnalysisStatus;
