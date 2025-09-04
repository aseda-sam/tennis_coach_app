import { useCallback, useEffect, useRef, useState } from 'react';
import unifiedAnalysisApi, { TaskStatus } from '../services/unifiedAnalysisApi';

export interface AnalysisProgress {
  taskId: number;
  videoId: number;
  analysisType:
    | 'pose_only'
    | 'ball_only'
    | 'video_annotation_only'
    | 'pose_with_annotation';
  status: TaskStatus['status'];
  progress: number;
  currentStage?: string;
  stageProgress?: number;
  stageMessage?: string;
  estimatedTimeRemaining?: number;
  framesProcessed?: number;
  totalFrames?: number;
  error?: string;
  result?: any;
  startedAt: string;
  completedAt?: string;
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
  startPolling: (taskId: number) => void;
  stopPolling: () => void;
  isPolling: boolean;
}

export function useAnalysisProgress(
  options: UseAnalysisProgressOptions = {}
): UseAnalysisProgressReturn {
  const { pollInterval = 2000, onComplete, onError, onProgress } = options;

  const [progress, setProgress] = useState<AnalysisProgress | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const currentTaskIdRef = useRef<number | null>(null);

  const convertTaskStatusToProgress = useCallback(
    (taskStatus: TaskStatus): AnalysisProgress => {
      return {
        taskId: taskStatus.task_id,
        videoId: taskStatus.video_id,
        analysisType: taskStatus.analysis_type,
        status: taskStatus.status,
        progress: taskStatus.progress,
        currentStage: taskStatus.current_stage,
        stageProgress: taskStatus.stage_progress,
        stageMessage: taskStatus.stage_message,
        estimatedTimeRemaining: taskStatus.estimated_time_remaining,
        framesProcessed: taskStatus.frames_processed,
        totalFrames: taskStatus.total_frames,
        error: taskStatus.error,
        result: taskStatus.result,
        startedAt: taskStatus.started_at,
        completedAt: taskStatus.completed_at,
      };
    },
    []
  );

  const pollTaskStatus = useCallback(
    async (taskId: number) => {
      try {
        setIsLoading(true);
        setError(null);

        const taskStatus = await unifiedAnalysisApi.getTaskStatus(taskId);
        const progressData = convertTaskStatusToProgress(taskStatus);

        setProgress(progressData);
        onProgress?.(progressData);

        // Check if task is complete
        if (taskStatus.status === 'completed') {
          setIsPolling(false);
          setIsLoading(false);
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
          const errorMessage = taskStatus.error || `Task ${taskStatus.status}`;
          setError(errorMessage);
          onError?.(errorMessage);
          return;
        }
      } catch (err: any) {
        const errorMessage = err.message || 'Failed to get task status';
        setError(errorMessage);
        setIsPolling(false);
        setIsLoading(false);
        onError?.(errorMessage);
      }
    },
    [convertTaskStatusToProgress, onComplete, onError, onProgress]
  );

  const startPolling = useCallback(
    (taskId: number) => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }

      currentTaskIdRef.current = taskId;
      setIsPolling(true);
      setIsLoading(true);
      setError(null);

      // Poll immediately
      pollTaskStatus(taskId);

      // Set up interval for continued polling
      intervalRef.current = setInterval(() => {
        if (currentTaskIdRef.current === taskId) {
          pollTaskStatus(taskId);
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
    currentTaskIdRef.current = null;
  }, []);

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
