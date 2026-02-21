import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect } from 'react';
import { serveWindowApi } from '../services/serveWindowApi';
import {
  ServeWindow,
  ServeWindowCreate,
  ServeWindowFilters,
  ServeWindowUpdate,
} from '../types/serveWindow';
import { getApiErrorMessage } from '../utils/apiError';

interface UseServeWindowsOptions {
  videoId?: number;
  filters?: ServeWindowFilters;
  autoRefresh?: boolean;
  onServeWindowsLoaded?: (serveWindows: ServeWindow[]) => void;
  onError?: (error: string) => void;
}

interface UseServeWindowsResult {
  serveWindows: ServeWindow[];
  loading: boolean;
  error: string | null;
  refreshServeWindows: () => Promise<void>;
  createServeWindow: (serveWindow: ServeWindowCreate) => Promise<ServeWindow>;
  updateServeWindow: (
    serveWindowId: number,
    updates: ServeWindowUpdate
  ) => Promise<ServeWindow>;
  deleteServeWindow: (serveWindowId: number) => Promise<void>;
}

export const useServeWindows = ({
  videoId,
  filters,
  autoRefresh = true,
  onServeWindowsLoaded,
  onError,
}: UseServeWindowsOptions = {}): UseServeWindowsResult => {
  const queryClient = useQueryClient();

  // Build query key with filters
  const queryKey = ['serve-windows', filters || {}];

  // Fetch serve windows using React Query
  const serveWindowsQuery = useQuery<ServeWindow[]>({
    queryKey,
    queryFn: async () => {
      return await serveWindowApi.list(filters);
    },
    enabled: autoRefresh,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Call onServeWindowsLoaded callback when serve windows are loaded
  useEffect(() => {
    if (serveWindowsQuery.data && onServeWindowsLoaded) {
      onServeWindowsLoaded(serveWindowsQuery.data);
    }
  }, [serveWindowsQuery.data, onServeWindowsLoaded]);

  // Call onError callback when there's an error
  useEffect(() => {
    if (serveWindowsQuery.error && onError) {
      const errorMessage = getApiErrorMessage(
        serveWindowsQuery.error,
        'Failed to load serve windows'
      );
      onError(errorMessage);
    }
  }, [serveWindowsQuery.error, onError]);

  // Create serve window mutation
  const createMutation = useMutation({
    mutationFn: (serveWindow: ServeWindowCreate) =>
      serveWindowApi.create(serveWindow),
    onSuccess: () => {
      // Invalidate and refetch serve windows
      queryClient.invalidateQueries({ queryKey: ['serve-windows'] });
    },
  });

  // Update serve window mutation
  const updateMutation = useMutation({
    mutationFn: ({
      serveWindowId,
      updates,
    }: {
      serveWindowId: number;
      updates: ServeWindowUpdate;
    }) => serveWindowApi.update(serveWindowId, updates),
    onSuccess: () => {
      // Invalidate and refetch serve windows
      queryClient.invalidateQueries({ queryKey: ['serve-windows'] });
    },
  });

  // Delete serve window mutation
  const deleteMutation = useMutation({
    mutationFn: (serveWindowId: number) => serveWindowApi.delete(serveWindowId),
    onSuccess: () => {
      // Invalidate and refetch serve windows
      queryClient.invalidateQueries({ queryKey: ['serve-windows'] });
    },
  });

  const refreshServeWindows = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ['serve-windows'] });
  }, [queryClient]);

  const createServeWindow = useCallback(
    async (serveWindow: ServeWindowCreate): Promise<ServeWindow> => {
      try {
        return await createMutation.mutateAsync(serveWindow);
      } catch (err: unknown) {
        const errorMessage = getApiErrorMessage(
          err,
          'Failed to create serve window'
        );
        throw new Error(errorMessage);
      }
    },
    [createMutation]
  );

  const updateServeWindow = useCallback(
    async (
      serveWindowId: number,
      updates: ServeWindowUpdate
    ): Promise<ServeWindow> => {
      try {
        return await updateMutation.mutateAsync({ serveWindowId, updates });
      } catch (err: unknown) {
        const errorMessage = getApiErrorMessage(
          err,
          'Failed to update serve window'
        );
        throw new Error(errorMessage);
      }
    },
    [updateMutation]
  );

  const deleteServeWindow = useCallback(
    async (serveWindowId: number): Promise<void> => {
      try {
        await deleteMutation.mutateAsync(serveWindowId);
      } catch (err: unknown) {
        const errorMessage = getApiErrorMessage(
          err,
          'Failed to delete serve window'
        );
        throw new Error(errorMessage);
      }
    },
    [deleteMutation]
  );

  // Extract loading state
  const loading = serveWindowsQuery.isLoading;

  // Extract error state
  const error = serveWindowsQuery.error
    ? getApiErrorMessage(
        serveWindowsQuery.error,
        'Failed to load serve windows'
      )
    : null;

  return {
    serveWindows: serveWindowsQuery.data || [],
    loading,
    error,
    refreshServeWindows,
    createServeWindow,
    updateServeWindow,
    deleteServeWindow,
  };
};
