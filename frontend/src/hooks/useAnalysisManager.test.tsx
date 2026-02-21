import { act, renderHook } from '@testing-library/react';
import unifiedAnalysisApi from '../services/unifiedAnalysisApi';
import type { VideoJob } from '../types/analysis';

// Mock dependencies
jest.mock('../services/unifiedAnalysisApi', () => ({
  __esModule: true,
  default: {
    startAnalysis: jest.fn(),
    getVideoJobs: jest.fn(),
    getVideoJob: jest.fn(),
    cancelTask: jest.fn(),
  },
  unifiedAnalysisApi: {
    startAnalysis: jest.fn(),
    getVideoJobs: jest.fn(),
    getVideoJob: jest.fn(),
    cancelTask: jest.fn(),
  },
}));

// Must declare mock fns before jest.mock due to hoisting
const mockStartPolling = jest.fn();
const mockStopPolling = jest.fn();

jest.mock('./useAnalysisProgress', () => {
  return {
    __esModule: true,
    useAnalysisProgress: () => ({
      progress: null,
      isLoading: false,
      error: null,
      startPolling: mockStartPolling,
      stopPolling: mockStopPolling,
      isPolling: false,
    }),
    default: () => ({
      progress: null,
      isLoading: false,
      error: null,
      startPolling: mockStartPolling,
      stopPolling: mockStopPolling,
      isPolling: false,
    }),
  };
});

// Import after mocks are set up
// eslint-disable-next-line import/first
import { useAnalysisManager } from './useAnalysisManager';

const mockApi = unifiedAnalysisApi as jest.Mocked<typeof unifiedAnalysisApi>;

describe('useAnalysisManager', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApi.getVideoJobs.mockResolvedValue([]);
  });

  it('initializes with idle state', () => {
    const { result } = renderHook(() => useAnalysisManager({ videoId: 1 }));

    expect(result.current.analysisState).toEqual({
      videoId: 1,
      jobId: null,
      status: 'idle',
      error: null,
    });
    expect(result.current.isLoading).toBe(false);
  });

  it('checks for active jobs on mount', async () => {
    mockApi.getVideoJobs.mockResolvedValue([]);

    renderHook(() => useAnalysisManager({ videoId: 5 }));

    // Give the useEffect time to run
    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(mockApi.getVideoJobs).toHaveBeenCalledWith('queued,processing');
  });

  it('resumes polling for active job on mount', async () => {
    const activeJob: VideoJob = {
      id: 'job-123',
      video_id: 5,
      job_type: 'pose_only',
      status: 'processing',
      created_at: '2025-01-01T00:00:00Z',
      started_at: '2025-01-01T00:00:01Z',
    };
    mockApi.getVideoJobs.mockResolvedValue([activeJob]);

    const { result } = renderHook(() => useAnalysisManager({ videoId: 5 }));

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(result.current.analysisState.status).toBe('processing');
    expect(result.current.analysisState.jobId).toBe('job-123');
    expect(mockStartPolling).toHaveBeenCalledWith('job-123');
  });

  it('ignores active jobs for other videos', async () => {
    const otherVideoJob: VideoJob = {
      id: 'job-456',
      video_id: 99,
      job_type: 'pose_only',
      status: 'processing',
      created_at: '2025-01-01T00:00:00Z',
    };
    mockApi.getVideoJobs.mockResolvedValue([otherVideoJob]);

    const { result } = renderHook(() => useAnalysisManager({ videoId: 5 }));

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(result.current.analysisState.status).toBe('idle');
    expect(mockStartPolling).not.toHaveBeenCalled();
  });

  it('sets error state when active job check fails', async () => {
    mockApi.getVideoJobs.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => useAnalysisManager({ videoId: 5 }));

    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });

    expect(result.current.analysisState.error).toBeTruthy();
  });

  describe('startAnalysis', () => {
    it('starts analysis and begins polling', async () => {
      mockApi.startAnalysis.mockResolvedValue({
        job_id: 'new-job-1',
        video_id: 5,
        analysis_type: 'pose_only',
        status: 'queued',
        message: 'Analysis started',
      });

      const { result } = renderHook(() => useAnalysisManager({ videoId: 5 }));

      await act(async () => {
        await new Promise((r) => setTimeout(r, 0));
      });

      await act(async () => {
        await result.current.startAnalysis({
          analysis_type: 'pose_only',
        });
      });

      expect(mockApi.startAnalysis).toHaveBeenCalledWith(5, {
        analysis_type: 'pose_only',
      });
      expect(result.current.analysisState.status).toBe('processing');
      expect(result.current.analysisState.jobId).toBe('new-job-1');
      expect(mockStartPolling).toHaveBeenCalledWith('new-job-1');
    });

    it('handles startAnalysis failure', async () => {
      mockApi.startAnalysis.mockRejectedValue(new Error('Start failed'));

      const onAnalysisError = jest.fn();
      const { result } = renderHook(() =>
        useAnalysisManager({ videoId: 5, onAnalysisError })
      );

      await act(async () => {
        await new Promise((r) => setTimeout(r, 0));
      });

      await act(async () => {
        await result.current.startAnalysis({
          analysis_type: 'pose_only',
        });
      });

      expect(result.current.analysisState.status).toBe('failed');
      expect(result.current.analysisState.error).toBeTruthy();
      expect(result.current.analysisState.jobId).toBeNull();
      expect(onAnalysisError).toHaveBeenCalled();
    });

    it('handles timeout error with specific message', async () => {
      const timeoutError = new Error('timeout');
      (timeoutError as unknown as { code: string }).code = 'ECONNABORTED';
      mockApi.startAnalysis.mockRejectedValue(timeoutError);

      const { result } = renderHook(() => useAnalysisManager({ videoId: 5 }));

      await act(async () => {
        await new Promise((r) => setTimeout(r, 0));
      });

      await act(async () => {
        await result.current.startAnalysis({
          analysis_type: 'pose_only',
        });
      });

      expect(result.current.analysisState.error).toContain('timed out');
    });
  });

  describe('cancelAnalysis', () => {
    it('cancels an active analysis', async () => {
      mockApi.startAnalysis.mockResolvedValue({
        job_id: 'cancel-job',
        video_id: 5,
        analysis_type: 'pose_only',
        status: 'queued',
        message: 'Started',
      });
      mockApi.cancelTask.mockResolvedValue({
        message: 'Cancelled',
        job_id: 'cancel-job',
      });

      const { result } = renderHook(() => useAnalysisManager({ videoId: 5 }));

      await act(async () => {
        await new Promise((r) => setTimeout(r, 0));
      });

      // Start analysis first
      await act(async () => {
        await result.current.startAnalysis({
          analysis_type: 'pose_only',
        });
      });

      // Then cancel
      await act(async () => {
        await result.current.cancelAnalysis();
      });

      expect(mockApi.cancelTask).toHaveBeenCalledWith('cancel-job');
      expect(mockStopPolling).toHaveBeenCalled();
      expect(result.current.analysisState.status).toBe('cancelled');
      expect(result.current.analysisState.jobId).toBeNull();
    });

    it('does nothing when no jobId', async () => {
      const { result } = renderHook(() => useAnalysisManager({ videoId: 5 }));

      await act(async () => {
        await new Promise((r) => setTimeout(r, 0));
      });

      await act(async () => {
        await result.current.cancelAnalysis();
      });

      expect(mockApi.cancelTask).not.toHaveBeenCalled();
    });

    it('sets error when cancel fails', async () => {
      mockApi.startAnalysis.mockResolvedValue({
        job_id: 'fail-cancel',
        video_id: 5,
        analysis_type: 'pose_only',
        status: 'queued',
        message: 'Started',
      });
      mockApi.cancelTask.mockRejectedValue(new Error('Cancel failed'));

      const { result } = renderHook(() => useAnalysisManager({ videoId: 5 }));

      await act(async () => {
        await new Promise((r) => setTimeout(r, 0));
      });

      await act(async () => {
        await result.current.startAnalysis({
          analysis_type: 'pose_only',
        });
      });

      await act(async () => {
        await result.current.cancelAnalysis();
      });

      expect(result.current.analysisState.error).toBeTruthy();
    });
  });

  describe('refreshAnalysis', () => {
    it('resets state to idle', async () => {
      mockApi.startAnalysis.mockResolvedValue({
        job_id: 'refresh-job',
        video_id: 5,
        analysis_type: 'pose_only',
        status: 'queued',
        message: 'Started',
      });

      const { result } = renderHook(() => useAnalysisManager({ videoId: 5 }));

      await act(async () => {
        await new Promise((r) => setTimeout(r, 0));
      });

      await act(async () => {
        await result.current.startAnalysis({
          analysis_type: 'pose_only',
        });
      });

      expect(result.current.analysisState.status).toBe('processing');

      await act(async () => {
        await result.current.refreshAnalysis();
      });

      expect(result.current.analysisState.status).toBe('idle');
      expect(result.current.analysisState.jobId).toBeNull();
      expect(result.current.analysisState.error).toBeNull();
    });
  });
});
