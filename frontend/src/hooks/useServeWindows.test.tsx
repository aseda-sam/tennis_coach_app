import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor, act } from '@testing-library/react';
import React from 'react';
import { serveWindowApi } from '../services/serveWindowApi';
import {
  ServeWindow,
  ServeWindowCreate,
  ServeWindowUpdate,
} from '../types/serveWindow';
import { useServeWindows } from './useServeWindows';

// ---------------------------------------------------------------------------
// Mock the entire API module
// ---------------------------------------------------------------------------
jest.mock('../services/serveWindowApi');

const mockedApi = jest.mocked(serveWindowApi);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

/** Factory for a realistic ServeWindow object. */
function makeServeWindow(overrides: Partial<ServeWindow> = {}): ServeWindow {
  return {
    id: 1,
    video_id: 10,
    player_id: 100,
    start_timestamp: 1.0,
    end_timestamp: 3.5,
    contact_timestamp: 2.2,
    source: 'model',
    status: 'confirmed',
    confidence: 0.95,
    model_version: 'v1',
    court_side: 'deuce',
    serve_number: 1,
    serve_subtype: 'flat',
    in_out: 'in',
    created_at: '2025-01-01T00:00:00Z',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useServeWindows', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  // -----------------------------------------------------------------------
  // Fetching
  // -----------------------------------------------------------------------

  it('returns serve windows from the API', async () => {
    const windows = [makeServeWindow({ id: 1 }), makeServeWindow({ id: 2 })];
    mockedApi.list.mockResolvedValue(windows);

    const queryClient = createQueryClient();
    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    // Initially loading
    expect(result.current.loading).toBe(true);
    expect(result.current.serveWindows).toEqual([]);

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.serveWindows).toEqual(windows);
    expect(result.current.error).toBeNull();
    expect(mockedApi.list).toHaveBeenCalledTimes(1);
    expect(mockedApi.list).toHaveBeenCalledWith(undefined);
  });

  it('passes filters to the API list call', async () => {
    mockedApi.list.mockResolvedValue([]);

    const filters = { video_id: 42, court_side: 'ad' as const };
    const queryClient = createQueryClient();
    const { result } = renderHook(() => useServeWindows({ filters }), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(mockedApi.list).toHaveBeenCalledWith(filters);
  });

  // -----------------------------------------------------------------------
  // enabled = false (autoRefresh)
  // -----------------------------------------------------------------------

  it('does not fetch when autoRefresh is false', async () => {
    mockedApi.list.mockResolvedValue([]);

    const queryClient = createQueryClient();
    const { result } = renderHook(
      () => useServeWindows({ autoRefresh: false }),
      { wrapper: createWrapper(queryClient) }
    );

    // Should not be loading and should not have called the API
    // When enabled=false, React Query skips the query entirely.
    // isLoading will be false and data will be undefined (hook returns []).
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(mockedApi.list).not.toHaveBeenCalled();
    expect(result.current.serveWindows).toEqual([]);
  });

  // -----------------------------------------------------------------------
  // Loading & error states
  // -----------------------------------------------------------------------

  it('exposes loading state while the query is in flight', async () => {
    // Never resolve -- keep the query in flight
    mockedApi.list.mockReturnValue(new Promise(() => {}));

    const queryClient = createQueryClient();
    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current.loading).toBe(true);
    expect(result.current.serveWindows).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it('exposes error state when the API call fails', async () => {
    mockedApi.list.mockRejectedValue(new Error('Network error'));

    const queryClient = createQueryClient();
    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.error).not.toBeNull());

    expect(result.current.error).toBe('Network error');
    expect(result.current.serveWindows).toEqual([]);
    expect(result.current.loading).toBe(false);
  });

  it('uses the fallback error message when error has no message', async () => {
    mockedApi.list.mockRejectedValue({});

    const queryClient = createQueryClient();
    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.error).not.toBeNull());

    expect(result.current.error).toBe('Failed to load serve windows');
  });

  it('uses detail from an API error response', async () => {
    mockedApi.list.mockRejectedValue({
      response: { data: { detail: 'Unauthorized' } },
    });

    const queryClient = createQueryClient();
    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.error).not.toBeNull());

    expect(result.current.error).toBe('Unauthorized');
  });

  // -----------------------------------------------------------------------
  // Callbacks
  // -----------------------------------------------------------------------

  it('calls onServeWindowsLoaded when data arrives', async () => {
    const windows = [makeServeWindow()];
    mockedApi.list.mockResolvedValue(windows);
    const onLoaded = jest.fn();

    const queryClient = createQueryClient();
    renderHook(() => useServeWindows({ onServeWindowsLoaded: onLoaded }), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(onLoaded).toHaveBeenCalledWith(windows));
  });

  it('calls onError when the query fails', async () => {
    mockedApi.list.mockRejectedValue(new Error('boom'));
    const onError = jest.fn();

    const queryClient = createQueryClient();
    renderHook(() => useServeWindows({ onError }), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(onError).toHaveBeenCalledWith('boom'));
  });

  // -----------------------------------------------------------------------
  // Create mutation
  // -----------------------------------------------------------------------

  it('createServeWindow calls API and invalidates the cache', async () => {
    const existing = [makeServeWindow({ id: 1 })];
    const created = makeServeWindow({ id: 2 });
    mockedApi.list.mockResolvedValue(existing);
    mockedApi.create.mockResolvedValue(created);

    const queryClient = createQueryClient();
    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    const payload: ServeWindowCreate = {
      video_id: 10,
      start_timestamp: 1.0,
      end_timestamp: 3.5,
    };

    let returnedWindow: ServeWindow | undefined;
    await act(async () => {
      returnedWindow = await result.current.createServeWindow(payload);
    });

    expect(mockedApi.create).toHaveBeenCalledWith(payload);
    expect(returnedWindow).toEqual(created);
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ['serve-windows'] })
    );
  });

  it('createServeWindow throws a readable error on failure', async () => {
    mockedApi.list.mockResolvedValue([]);
    mockedApi.create.mockRejectedValue(new Error('Server error'));

    const queryClient = createQueryClient();
    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    const payload: ServeWindowCreate = {
      video_id: 10,
      start_timestamp: 1.0,
      end_timestamp: 3.5,
    };

    await expect(
      act(() => result.current.createServeWindow(payload))
    ).rejects.toThrow('Server error');
  });

  // -----------------------------------------------------------------------
  // Update mutation
  // -----------------------------------------------------------------------

  it('updateServeWindow calls API and invalidates the cache', async () => {
    const existing = [makeServeWindow({ id: 1 })];
    const updated = makeServeWindow({ id: 1, court_side: 'ad' });
    mockedApi.list.mockResolvedValue(existing);
    mockedApi.update.mockResolvedValue(updated);

    const queryClient = createQueryClient();
    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    const updates: ServeWindowUpdate = { court_side: 'ad' };

    let returnedWindow: ServeWindow | undefined;
    await act(async () => {
      returnedWindow = await result.current.updateServeWindow(1, updates);
    });

    expect(mockedApi.update).toHaveBeenCalledWith(1, updates);
    expect(returnedWindow).toEqual(updated);
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ['serve-windows'] })
    );
  });

  it('updateServeWindow throws a readable error on failure', async () => {
    mockedApi.list.mockResolvedValue([]);
    mockedApi.update.mockRejectedValue({
      response: { data: { detail: 'Not found' } },
    });

    const queryClient = createQueryClient();
    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    await expect(
      act(() => result.current.updateServeWindow(999, { court_side: 'ad' }))
    ).rejects.toThrow('Not found');
  });

  // -----------------------------------------------------------------------
  // Delete mutation
  // -----------------------------------------------------------------------

  it('deleteServeWindow calls API and invalidates the cache', async () => {
    const existing = [makeServeWindow({ id: 1 })];
    mockedApi.list.mockResolvedValue(existing);
    mockedApi.delete.mockResolvedValue(undefined);

    const queryClient = createQueryClient();
    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.deleteServeWindow(1);
    });

    expect(mockedApi.delete).toHaveBeenCalledWith(1);
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ['serve-windows'] })
    );
  });

  it('deleteServeWindow throws a readable error on failure', async () => {
    mockedApi.list.mockResolvedValue([]);
    mockedApi.delete.mockRejectedValue(new Error('Forbidden'));

    const queryClient = createQueryClient();
    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    await expect(
      act(() => result.current.deleteServeWindow(1))
    ).rejects.toThrow('Forbidden');
  });

  // -----------------------------------------------------------------------
  // refreshServeWindows
  // -----------------------------------------------------------------------

  it('refreshServeWindows invalidates the cache', async () => {
    mockedApi.list.mockResolvedValue([]);

    const queryClient = createQueryClient();
    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');

    const { result } = renderHook(() => useServeWindows(), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.refreshServeWindows();
    });

    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: ['serve-windows'] })
    );
  });
});
