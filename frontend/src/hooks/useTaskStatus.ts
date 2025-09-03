import { useCallback, useEffect, useRef, useState } from 'react';
import { analysisApi, TaskStatus } from '../services/api';

interface UseTaskStatusOptions {
  taskId: number | null;
  pollInterval?: number; // milliseconds
  autoStop?: boolean; // stop polling when task completes
  onComplete?: (taskStatus: TaskStatus) => void;
  onError?: (error: string) => void;
}

interface UseTaskStatusResult {
  taskStatus: TaskStatus | null;
  loading: boolean;
  error: string | null;
  isPolling: boolean;
  startPolling: () => void;
  stopPolling: () => void;
  refetch: () => Promise<void>;
}

export const useTaskStatus = ({
  taskId,
  pollInterval = 2000, // 2 seconds default
  autoStop = true,
  onComplete,
  onError,
}: UseTaskStatusOptions): UseTaskStatusResult => {
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const isPollingRef = useRef(false);

  // Function to fetch task status
  const fetchTaskStatus = useCallback(async () => {
    if (!taskId) return;

    try {
      setLoading(true);
      setError(null);
      
      // Create new abort controller for this request
      abortControllerRef.current = new AbortController();
      
      const status = await analysisApi.getTaskStatus(taskId);
      setTaskStatus(status);

      // Check if task is completed and we should stop polling
      if (autoStop && (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled')) {
        setIsPolling(false);
        isPollingRef.current = false;
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        
        // Call completion callback
        if (status.status === 'completed' && onComplete) {
          onComplete(status);
        } else if ((status.status === 'failed' || status.status === 'cancelled') && onError) {
          onError(status.error || `Task ${status.status}`);
        }
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to fetch task status';
      setError(errorMessage);
      
      if (onError) {
        onError(errorMessage);
      }
      
      // Stop polling on error
      setIsPolling(false);
      isPollingRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } finally {
      setLoading(false);
    }
  }, [taskId, autoStop, onComplete, onError]);

  // Function to start polling
  const startPolling = useCallback(() => {
    if (!taskId || isPollingRef.current) return;

    setIsPolling(true);
    isPollingRef.current = true;
    
    // Fetch immediately
    fetchTaskStatus();
    
    // Set up interval for polling
    intervalRef.current = setInterval(() => {
      fetchTaskStatus();
    }, pollInterval);
  }, [taskId, fetchTaskStatus, pollInterval]);

  // Function to stop polling
  const stopPolling = useCallback(() => {
    setIsPolling(false);
    isPollingRef.current = false;
    
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

  // Function to manually refetch
  const refetch = useCallback(async () => {
    await fetchTaskStatus();
  }, [fetchTaskStatus]);

  // Effect to handle taskId changes
  useEffect(() => {
    if (taskId) {
      // Start polling automatically when taskId is provided
      startPolling();
    } else {
      // Stop polling when taskId is null
      stopPolling();
      setTaskStatus(null);
      setError(null);
    }

    // Cleanup function
    return () => {
      stopPolling();
    };
  }, [taskId, startPolling, stopPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    taskStatus,
    loading,
    error,
    isPolling,
    startPolling,
    stopPolling,
    refetch,
  };
};
