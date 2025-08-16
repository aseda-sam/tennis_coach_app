import { useCallback, useEffect, useState } from 'react';
import { analysisApi, AnalysisData, AnalysisStartResponse, TaskStatus } from '../services/api';
import { useTaskStatus } from './useTaskStatus';

interface AnalysisState {
  videoId: number;
  analysis: AnalysisData | null;
  taskId: number | null;
  status: 'idle' | 'starting' | 'processing' | 'finalizing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  currentStage?: string;
  stageProgress?: number;
  stageMessage?: string;
  error: string | null;
}

interface UseAnalysisManagerOptions {
  videoId: number;
  autoRefresh?: boolean;
  onAnalysisComplete?: (analysis: AnalysisData) => void;
  onAnalysisError?: (error: string) => void;
}

interface UseAnalysisManagerResult {
  analysisState: AnalysisState;
  startAnalysis: (analysisRequest: {
    analysis_type: string;
    confidence_threshold?: number;
    include_pose_detection?: boolean;
  }) => Promise<void>;
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
    analysis: null,
    taskId: null,
    status: 'idle',
    progress: 0,
    error: null,
  });
  const [isLoading, setIsLoading] = useState(false);

  // Task status polling hook
           const {
           taskStatus,
           loading: taskLoading,
         } = useTaskStatus({
    taskId: analysisState.taskId,
    pollInterval: 2000,
    autoStop: true,
    onComplete: (completedTask: TaskStatus) => {
      // Task completed, refresh analysis data
      refreshAnalysis();
    },
    onError: (error: string) => {
      setAnalysisState(prev => ({
        ...prev,
        status: 'failed',
        error,
        progress: 0,
      }));
      if (onAnalysisError) {
        onAnalysisError(error);
      }
    },
  });

  // Function to load existing analysis
  const loadAnalysis = useCallback(async () => {
    try {
      setIsLoading(true);
      const analysis = await analysisApi.getAnalysisByVideo(videoId);
      setAnalysisState(prev => ({
        ...prev,
        analysis,
        status: 'completed',
        progress: 100,
        error: null,
      }));
    } catch (err: any) {
      // Analysis not found or other error - this is normal for videos without analysis
      setAnalysisState(prev => ({
        ...prev,
        analysis: null,
        status: 'idle',
        progress: 0,
        error: null,
      }));
    } finally {
      setIsLoading(false);
    }
  }, [videoId]);

  // Update analysis state when task status changes
  useEffect(() => {
    if (taskStatus && analysisState.taskId) {
      setAnalysisState(prev => ({
        ...prev,
        progress: taskStatus.progress,
        currentStage: taskStatus.current_stage || undefined,
        stageProgress: taskStatus.stage_progress || undefined,
        stageMessage: taskStatus.stage_message || undefined,
      }));
    }
  }, [taskStatus, analysisState.taskId]);

  // Function to refresh analysis data
  const refreshAnalysis = useCallback(async () => {
    await loadAnalysis();
  }, [loadAnalysis]);

  // Function to start analysis
  const startAnalysis = useCallback(async (analysisRequest: {
    analysis_type: string;
    confidence_threshold?: number;
    include_pose_detection?: boolean;
  }) => {
    try {
      setAnalysisState(prev => ({
        ...prev,
        status: 'starting',
        progress: 0,
        error: null,
      }));

      const response: AnalysisStartResponse = await analysisApi.startAnalysis(videoId, analysisRequest);
      
      if (response.status === 'completed' && response.analysis_id) {
        // Analysis completed immediately (synchronous mode)
        setAnalysisState(prev => ({
          ...prev,
          status: 'completed',
          progress: 100,
          taskId: null,
        }));
        
        // Load the completed analysis
        await refreshAnalysis();
        
        if (onAnalysisComplete && analysisState.analysis) {
          onAnalysisComplete(analysisState.analysis);
        }
      } else if (response.status === 'processing' && response.task_id) {
        // Analysis started in background
        setAnalysisState(prev => ({
          ...prev,
          status: 'processing',
          progress: 0,
          taskId: response.task_id,
        }));
      } else {
        throw new Error(response.message || 'Failed to start analysis');
      }
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to start analysis';
      setAnalysisState(prev => ({
        ...prev,
        status: 'failed',
        error: errorMessage,
        progress: 0,
      }));
      
      if (onAnalysisError) {
        onAnalysisError(errorMessage);
      }
    }
  }, [videoId, refreshAnalysis, onAnalysisComplete, onAnalysisError, analysisState.analysis]);

  // Function to cancel analysis
  const cancelAnalysis = useCallback(async () => {
    if (!analysisState.taskId) return;

    try {
      await analysisApi.cancelTask(analysisState.taskId);
      setAnalysisState(prev => ({
        ...prev,
        status: 'cancelled',
        progress: 0,
        taskId: null,
      }));
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to cancel analysis';
      setAnalysisState(prev => ({
        ...prev,
        error: errorMessage,
      }));
    }
  }, [analysisState.taskId]);

  // Update analysis state based on task status
  useEffect(() => {
    if (taskStatus) {
      setAnalysisState(prev => ({
        ...prev,
        status: taskStatus.status as AnalysisState['status'],
        progress: taskStatus.progress,
        error: taskStatus.error,
      }));
    }
  }, [taskStatus]);

  // Load analysis on mount and when videoId changes
  useEffect(() => {
    if (autoRefresh) {
      loadAnalysis();
    }
  }, [videoId, autoRefresh, loadAnalysis]);

  return {
    analysisState,
    startAnalysis,
    refreshAnalysis,
    cancelAnalysis,
    isLoading: isLoading || taskLoading,
  };
};
