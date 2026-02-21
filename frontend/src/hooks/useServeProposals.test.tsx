import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { serveProposalApi } from '../services/serveProposalApi';
import type { ServeWindowProposal } from '../types/serveProposal';
import { useServeProposals } from './useServeProposals';

jest.mock('../services/serveProposalApi', () => ({
  serveProposalApi: {
    list: jest.fn(),
    getStatus: jest.fn(),
    propose: jest.fn(),
    clearProposals: jest.fn(),
    accept: jest.fn(),
    reject: jest.fn(),
    edit: jest.fn(),
    acceptAll: jest.fn(),
    rejectByConfidence: jest.fn(),
  },
}));

const mockApi = serveProposalApi as jest.Mocked<typeof serveProposalApi>;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

const mockProposals: ServeWindowProposal[] = [
  {
    id: 1,
    video_id: 10,
    start_timestamp: 1.0,
    end_timestamp: 3.5,
    model_version: 'v1',
    confidence: 0.9,
    status: 'pending',
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 2,
    video_id: 10,
    start_timestamp: 5.0,
    end_timestamp: 7.0,
    model_version: 'v1',
    confidence: 0.4,
    status: 'pending',
    created_at: '2025-01-01T00:00:00Z',
  },
];

describe('useServeProposals', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns empty proposals when videoId is not provided', () => {
    const { result } = renderHook(() => useServeProposals(), {
      wrapper: createWrapper(),
    });

    expect(result.current.proposals).toEqual([]);
    expect(result.current.loading).toBe(false);
  });

  it('fetches proposals when videoId is provided', async () => {
    mockApi.list.mockResolvedValue(mockProposals);
    mockApi.getStatus.mockResolvedValue({
      video_id: 10,
      pending_proposals: 2,
      reviewed_proposals: 0,
      serve_windows: 0,
      can_run_detection: true,
    });

    const { result } = renderHook(() => useServeProposals({ videoId: 10 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.proposals).toHaveLength(2);
    });

    expect(mockApi.list).toHaveBeenCalledWith(10);
  });

  it('does not fetch when autoRefresh is false', () => {
    const { result } = renderHook(
      () => useServeProposals({ videoId: 10, autoRefresh: false }),
      { wrapper: createWrapper() }
    );

    expect(result.current.proposals).toEqual([]);
    expect(mockApi.list).not.toHaveBeenCalled();
  });

  it('counts low confidence proposals', async () => {
    mockApi.list.mockResolvedValue(mockProposals);
    mockApi.getStatus.mockResolvedValue({
      video_id: 10,
      pending_proposals: 2,
      reviewed_proposals: 0,
      serve_windows: 0,
      can_run_detection: true,
    });

    const { result } = renderHook(
      () => useServeProposals({ videoId: 10, lowConfidenceThreshold: 0.6 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.proposals).toHaveLength(2);
    });

    // Proposal with confidence 0.4 is below 0.6 threshold
    expect(result.current.lowConfidenceCount).toBe(1);
  });

  it('calls onProposalsLoaded callback when proposals arrive', async () => {
    mockApi.list.mockResolvedValue(mockProposals);
    mockApi.getStatus.mockResolvedValue({
      video_id: 10,
      pending_proposals: 2,
      reviewed_proposals: 0,
      serve_windows: 0,
      can_run_detection: true,
    });

    const onProposalsLoaded = jest.fn();
    renderHook(() => useServeProposals({ videoId: 10, onProposalsLoaded }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(onProposalsLoaded).toHaveBeenCalledWith(mockProposals);
    });
  });

  it('calls onError callback on fetch failure', async () => {
    mockApi.list.mockRejectedValue(new Error('Network error'));
    mockApi.getStatus.mockResolvedValue({
      video_id: 10,
      pending_proposals: 0,
      reviewed_proposals: 0,
      serve_windows: 0,
      can_run_detection: true,
    });

    const onError = jest.fn();
    renderHook(() => useServeProposals({ videoId: 10, onError }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(onError).toHaveBeenCalled();
    });
  });

  it('exposes error state on fetch failure', async () => {
    mockApi.list.mockRejectedValue(new Error('Server error'));
    mockApi.getStatus.mockResolvedValue({
      video_id: 10,
      pending_proposals: 0,
      reviewed_proposals: 0,
      serve_windows: 0,
      can_run_detection: true,
    });

    const { result } = renderHook(() => useServeProposals({ videoId: 10 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.error).not.toBeNull();
    });
  });

  describe('mutations', () => {
    it('acceptProposal calls API and throws on error', async () => {
      mockApi.list.mockResolvedValue([]);
      mockApi.getStatus.mockResolvedValue({
        video_id: 10,
        pending_proposals: 0,
        reviewed_proposals: 0,
        serve_windows: 0,
        can_run_detection: true,
      });
      mockApi.accept.mockResolvedValue(undefined);

      const { result } = renderHook(() => useServeProposals({ videoId: 10 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await act(async () => {
        await result.current.acceptProposal(1);
      });

      expect(mockApi.accept).toHaveBeenCalledWith(1, undefined);
    });

    it('rejectProposal calls API', async () => {
      mockApi.list.mockResolvedValue([]);
      mockApi.getStatus.mockResolvedValue({
        video_id: 10,
        pending_proposals: 0,
        reviewed_proposals: 0,
        serve_windows: 0,
        can_run_detection: true,
      });
      mockApi.reject.mockResolvedValue(undefined);

      const { result } = renderHook(() => useServeProposals({ videoId: 10 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      await act(async () => {
        await result.current.rejectProposal(2);
      });

      expect(mockApi.reject).toHaveBeenCalledWith(2);
    });

    it('runDetection calls propose API', async () => {
      mockApi.list.mockResolvedValue([]);
      mockApi.getStatus.mockResolvedValue({
        video_id: 10,
        pending_proposals: 0,
        reviewed_proposals: 0,
        serve_windows: 0,
        can_run_detection: true,
      });
      mockApi.propose.mockResolvedValue({
        video_id: 10,
        proposals: mockProposals,
        count: 2,
      });

      const { result } = renderHook(() => useServeProposals({ videoId: 10 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      let response;
      await act(async () => {
        response = await result.current.runDetection(true);
      });

      expect(mockApi.propose).toHaveBeenCalledWith(10, true);
      expect(response).toEqual({
        video_id: 10,
        proposals: mockProposals,
        count: 2,
      });
    });

    it('acceptAllProposals calls bulk API', async () => {
      mockApi.list.mockResolvedValue(mockProposals);
      mockApi.getStatus.mockResolvedValue({
        video_id: 10,
        pending_proposals: 2,
        reviewed_proposals: 0,
        serve_windows: 0,
        can_run_detection: true,
      });
      mockApi.acceptAll.mockResolvedValue({
        video_id: 10,
        accepted_count: 2,
        serve_window_ids: [100, 101],
      });

      const { result } = renderHook(() => useServeProposals({ videoId: 10 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.proposals).toHaveLength(2);
      });

      let response;
      await act(async () => {
        response = await result.current.acceptAllProposals();
      });

      expect(mockApi.acceptAll).toHaveBeenCalledWith(10);
      expect(response).toEqual({ accepted: 2, failed: 0 });
    });

    it('rejectLowConfidence calls threshold API', async () => {
      mockApi.list.mockResolvedValue(mockProposals);
      mockApi.getStatus.mockResolvedValue({
        video_id: 10,
        pending_proposals: 2,
        reviewed_proposals: 0,
        serve_windows: 0,
        can_run_detection: true,
      });
      mockApi.rejectByConfidence.mockResolvedValue({
        video_id: 10,
        rejected_count: 1,
        threshold: 0.6,
      });

      const { result } = renderHook(() => useServeProposals({ videoId: 10 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.proposals).toHaveLength(2);
      });

      let response;
      await act(async () => {
        response = await result.current.rejectLowConfidence(0.6);
      });

      expect(mockApi.rejectByConfidence).toHaveBeenCalledWith(10, 0.6);
      expect(response).toEqual({ rejected: 1, failed: 0 });
    });

    it('acceptAllProposals returns zeros when no videoId', async () => {
      const { result } = renderHook(() => useServeProposals(), {
        wrapper: createWrapper(),
      });

      let response;
      await act(async () => {
        response = await result.current.acceptAllProposals();
      });

      expect(response).toEqual({ accepted: 0, failed: 0 });
      expect(mockApi.acceptAll).not.toHaveBeenCalled();
    });
  });
});
