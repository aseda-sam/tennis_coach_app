import { useCallback, useEffect, useRef, useState } from 'react';
import unifiedAnalysisApi, { TaskStatus } from '../services/unifiedAnalysisApi';

/**
 * Discriminated union for analysis status state.
 * Following react-frontend.mdc patterns for type safety.
 */
export type AnalysisState =
  | { status: 'idle' }
  | { status: 'queued'; jobId: string; startedAt: string }
  | { status: 'processing'; jobId: string; startedAt: string }
  | { status: 'completed'; jobId: string; result: any; completedAt: string }
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

  // Convert TaskStatus to AnalysisState discriminated union
  const taskStatusToState = useCallback(
    (taskStatus: TaskStatus): AnalysisState => {
      switch (taskStatus.status) {
        case 'queued':
          return {
            status: 'queued',
            jobId: taskStatus.job_id,
            startedAt: taskStatus.started_at || new Date().toISOString(),
          };
        case 'processing':
          return {
            status: 'processing',
            jobId: taskStatus.job_id,
            startedAt: taskStatus.started_at || new Date().toISOString(),
          };
        case 'completed':
          return {
            status: 'completed',
            jobId: taskStatus.job_id,
            result: taskStatus.result,
            completedAt: taskStatus.completed_at || new Date().toISOString(),
          };
        case 'failed':
        case 'cancelled':
          return {
            status: 'failed',
            jobId: taskStatus.job_id,
            error: taskStatus.error || `Task ${taskStatus.status}`,
            startedAt: taskStatus.started_at || new Date().toISOString(),
          };
        default:
          return { status: 'idle' };
      }
    },
    []
  );

  // Fetch task status
  const fetchTaskStatus = useCallback(
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

        const taskStatus = await unifiedAnalysisApi.getTaskStatus(jobId);
        const newState = taskStatusToState(taskStatus);

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
      } catch (err: any) {
        // If job not found (404), treat as completed
        if (err?.response?.status === 404) {
          const completedState: AnalysisState = {
            status: 'completed',
            jobId,
            result: null,
            completedAt: new Date().toISOString(),
          };
          setState(completedState);
          onStateChange?.(completedState);
          setIsPolling(false);
          setIsLoading(false);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          onComplete?.(completedState);
          return;
        }

        const errorMessage =
          err?.response?.data?.detail ||
          err?.message ||
          'Failed to fetch task status';
        setError(errorMessage);
        setIsLoading(false);
        // Don't stop polling on transient errors - let it retry
      } finally {
        setIsLoading(false);
      }
    },
    [taskStatusToState, onComplete, onError, onStateChange]
  );

  // Poll function that respects visibility
  const poll = useCallback(() => {
    const jobId = currentJobIdRef.current;
    if (!jobId || !isVisibleRef.current) return;
    fetchTaskStatus(jobId);
  }, [fetchTaskStatus]);

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
      fetchTaskStatus(jobId);

      // Set up interval for continued polling (only when visible)
      intervalRef.current = setInterval(() => {
        if (currentJobIdRef.current === jobId && isVisibleRef.current) {
          poll();
        }
      }, pollInterval);
    },
    [fetchTaskStatus, pollInterval, poll]
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
      await fetchTaskStatus(jobId);
    }
  }, [fetchTaskStatus]);

  // Visibility API: pause polling when tab hidden, resume on focus
  useEffect(() => {
    const handleVisibilityChange = () => {
      isVisibleRef.current = !document.hidden;

      if (!document.hidden && currentJobIdRef.current && isPolling) {
        // Tab became visible - fetch immediately
        fetchTaskStatus(currentJobIdRef.current);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isPolling, fetchTaskStatus]);

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
