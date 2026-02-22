import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import React from 'react';
import { serveProposalApi } from '../services/serveProposalApi';
import { useServeProposals } from './useServeProposals';

jest.mock('../services/serveProposalApi', () => ({
  serveProposalApi: {
    getStatus: jest.fn(),
    propose: jest.fn(),
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

describe('useServeProposals', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('runDetection calls propose API', async () => {
    mockApi.getStatus.mockResolvedValue({
      video_id: 10,
      pending_proposals: 0,
      reviewed_proposals: 0,
      serve_windows: 0,
      can_run_detection: true,
    });
    mockApi.propose.mockResolvedValue({
      video_id: 10,
      proposals: [],
      count: 2,
    });

    const { result } = renderHook(() => useServeProposals({ videoId: 10 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.detectionStatus).not.toBeNull();
    });

    let response;
    await act(async () => {
      response = await result.current.runDetection(true);
    });

    expect(mockApi.propose).toHaveBeenCalledWith(10, true);
    expect(response).toEqual({
      video_id: 10,
      proposals: [],
      count: 2,
    });
  });
});
