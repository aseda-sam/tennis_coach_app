import { useCallback, useEffect, useRef, useState } from 'react';
import { AnalysisData } from '../services/api';
import unifiedAnalysisApi, { VideoJob } from '../services/unifiedAnalysisApi';

export interface AnalysisProgress {
  jobId: string;
  videoId: number;
  analysisType:
    | 'pose_only'
    | 'video_annotation_only'
    | 'pose_with_annotation'
    | 'contact_metrics';
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  error?: string;
  result?: AnalysisData | null;
  startedAt?: string;
  completedAt?: string;
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

  const convertJobToProgress = useCallback((job: VideoJob): AnalysisProgress => {
    const startedAt = job.started_at ? new Date(job.started_at).getTime() : null;
    const now = Date.now();
    const elapsed = startedAt ? now - startedAt : 0;

    // Progress is now indeterminate - always return 0 for processing states
    // Only show 100% for completed, 0% for failed
    let progress = 0;
    if (job.status === 'completed') {
      progress = 100;
    } else if (job.status === 'failed') {
      progress = 0;
    }
    // For 'queued' and 'processing', progress remains 0 (indeterminate)

    return {
      jobId: job.id,
      videoId: job.video_id,
      analysisType: 'pose_only',
      status: job.status,
      progress,
      error: job.error || undefined,
      result: null,
      startedAt: job.started_at || undefined,
      completedAt: job.finished_at || undefined,
      elapsedTime: elapsed,
    };
  }, []);

  const pollJobStatus = useCallback(
    async (jobId: string) => {
      try {
        setIsLoading(true);
        setError(null);

        const job = await unifiedAnalysisApi.getVideoJob(jobId);
        if (!job) {
          const errorMessage = 'Job not found';
          const progressData: AnalysisProgress = {
            jobId,
            videoId: 0,
            analysisType: 'pose_only',
            status: 'failed',
            progress: 0,
            error: errorMessage,
            result: null,
            completedAt: new Date().toISOString(),
            elapsedTime: 0,
          };
          setProgress(progressData);
          setError(errorMessage);
          onError?.(errorMessage);
          setIsPolling(false);
          setIsLoading(false);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          return;
        }

        const progressData = convertJobToProgress(job);

        setProgress(progressData);
        onProgress?.(progressData);

        // Check if task is complete
        if (job.status === 'completed') {
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
        if (job.status === 'failed') {
          setIsPolling(false);
          setIsLoading(false);
          // Clear interval to stop polling
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          const errorMessage = job.error || 'Job failed';
          setError(errorMessage);
          onError?.(errorMessage);
          return;
        }
      } catch (err: unknown) {
        // Error detail is already normalized to string by axios interceptor
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to get job status';
        setError(errorMessage);
        setIsLoading(false);
        // Keep polling on transient errors
        onError?.(errorMessage);
      }
    },
    [convertJobToProgress, onComplete, onError, onProgress]
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
      pollJobStatus(jobId);

      // Set up interval for continued polling (only when visible)
      intervalRef.current = setInterval(() => {
        if (currentJobIdRef.current === jobId && isVisibleRef.current) {
          pollJobStatus(jobId);
        }
      }, pollInterval);
    },
    [pollJobStatus, pollInterval]
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
        pollJobStatus(currentJobIdRef.current);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isPolling, pollJobStatus]);

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
