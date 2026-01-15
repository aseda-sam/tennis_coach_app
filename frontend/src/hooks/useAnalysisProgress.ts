import { useCallback, useEffect, useRef, useState } from 'react';
import unifiedAnalysisApi, { TaskStatus } from '../services/unifiedAnalysisApi';
import { AnalysisData } from '../services/api';

export interface AnalysisProgress {
  jobId: string;
  videoId: number;
  analysisType:
    | 'pose_only'
    | 'ball_only'
    | 'video_annotation_only'
    | 'pose_with_annotation';
  status: TaskStatus['status'];
  progress: number;
  error?: string;
  result?: AnalysisData | null;
  startedAt?: string;
  completedAt?: string;
  estimatedDuration?: number;
  elapsedTime?: number;
}

export interface UseAnalysisProgressOptions {
  pollInterval?: number;
  autoStart?: boolean;
  onComplete?: (progress: AnalysisProgress) => void;
  onError?: (error: string) => void;
  onProgress?: (progress: AnalysisProgress) => void;
}

export interface UseAnalysisProgressReturn {
  progress: AnalysisProgress | null;
  isLoading: boolean;
  error: string | null;
  startPolling: (jobId: string) => void;
  stopPolling: () => void;
  isPolling: boolean;
}

export function useAnalysisProgress(
  options: UseAnalysisProgressOptions = {}
): UseAnalysisProgressReturn {
  const { pollInterval = 12000, onComplete, onError, onProgress } = options;

  const [progress, setProgress] = useState<AnalysisProgress | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentJobIdRef = useRef<string | null>(null);
  const isVisibleRef = useRef(true);

  const convertTaskStatusToProgress = useCallback(
    (taskStatus: TaskStatus): AnalysisProgress => {
      // Calculate elapsed time
      const startedAt = taskStatus.started_at
        ? new Date(taskStatus.started_at).getTime()
        : null;
      const now = Date.now();
      const elapsed = startedAt ? now - startedAt : 0;

      // Calculate time-based progress
      let progress = 0;
      if (taskStatus.status === 'completed') {
        progress = 100;
      } else if (
        taskStatus.status === 'failed' ||
        taskStatus.status === 'cancelled'
      ) {
        progress = taskStatus.progress || 0;
      } else if (taskStatus.estimated_duration && startedAt) {
        const estimated = taskStatus.estimated_duration * 1000; // convert to ms
        progress =
          estimated > 0
            ? Math.min(95, Math.round((elapsed / estimated) * 100))
            : 0;
      }

      return {
        jobId: taskStatus.job_id,
        videoId: taskStatus.video_id,
        analysisType: taskStatus.analysis_type,
        status: taskStatus.status,
        progress,
        error: taskStatus.error || undefined,
        result: taskStatus.result,
        startedAt: taskStatus.started_at || undefined,
        completedAt: taskStatus.completed_at || undefined,
        estimatedDuration: taskStatus.estimated_duration,
        elapsedTime: elapsed,
      };
    },
    []
  );

  const pollTaskStatus = useCallback(
    async (jobId: string) => {
      try {
        setIsLoading(true);
        setError(null);

        const taskStatus = await unifiedAnalysisApi.getTaskStatus(jobId);
        const progressData = convertTaskStatusToProgress(taskStatus);

        setProgress(progressData);
        onProgress?.(progressData);

        // Check if task is complete
        if (taskStatus.status === 'completed') {
          setIsPolling(false);
          setIsLoading(false);
          // Clear interval to stop polling
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          onComplete?.(progressData);
          return;
        }

        // Check if task failed
        if (
          taskStatus.status === 'failed' ||
          taskStatus.status === 'cancelled'
        ) {
          setIsPolling(false);
          setIsLoading(false);
          // Clear interval to stop polling
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          const errorMessage = taskStatus.error || `Job ${taskStatus.status}`;
          setError(errorMessage);
          onError?.(errorMessage);
          return;
        }
      } catch (err: unknown) {
        const axiosError = err as { message?: string };
        const errorMessage = axiosError?.message || 'Failed to get job status';
        setError(errorMessage);
        setIsLoading(false);
        // Keep polling on transient errors
        onError?.(errorMessage);
      }
    },
    [convertTaskStatusToProgress, onComplete, onError, onProgress]
  );

  const startPolling = useCallback(
    (jobId: string) => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }

      currentJobIdRef.current = jobId;
      setIsPolling(true);
      setIsLoading(true);
      setError(null);

      // Poll immediately
      pollTaskStatus(jobId);

      // Set up interval for continued polling (only when visible)
      intervalRef.current = setInterval(() => {
        if (
          currentJobIdRef.current === jobId &&
          isVisibleRef.current
        ) {
          pollTaskStatus(jobId);
        }
      }, pollInterval);
    },
    [pollTaskStatus, pollInterval]
  );

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setIsPolling(false);
    setIsLoading(false);
    currentJobIdRef.current = null;
  }, []);

  // Visibility API: pause polling when tab hidden, resume on focus
  useEffect(() => {
    const handleVisibilityChange = () => {
      isVisibleRef.current = !document.hidden;

      if (!document.hidden && currentJobIdRef.current && isPolling) {
        pollTaskStatus(currentJobIdRef.current);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isPolling, pollTaskStatus]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    progress,
    isLoading,
    error,
    startPolling,
    stopPolling,
    isPolling,
  };
}

export default useAnalysisProgress;
