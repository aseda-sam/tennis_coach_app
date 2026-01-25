import { useCallback, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  serveAttemptApi,
  ServeAttempt,
  ServeAttemptCreate,
  ServeAttemptUpdate,
  ServeAttemptFilters,
} from '../services/serveAttemptApi';

interface UseServeAttemptsOptions {
  videoId?: number;
  filters?: ServeAttemptFilters;
  autoRefresh?: boolean;
  onServeAttemptsLoaded?: (serveAttempts: ServeAttempt[]) => void;
  onError?: (error: string) => void;
}

interface UseServeAttemptsResult {
  serveAttempts: ServeAttempt[];
  loading: boolean;
  error: string | null;
  refreshServeAttempts: () => Promise<void>;
  createServeAttempt: (serveAttempt: ServeAttemptCreate) => Promise<ServeAttempt>;
  updateServeAttempt: (
    serveAttemptId: number,
    updates: ServeAttemptUpdate
  ) => Promise<ServeAttempt>;
  deleteServeAttempt: (serveAttemptId: number) => Promise<void>;
}

export const useServeAttempts = ({
  videoId,
  filters,
  autoRefresh = true,
  onServeAttemptsLoaded,
  onError,
}: UseServeAttemptsOptions = {}): UseServeAttemptsResult => {
  const queryClient = useQueryClient();

  // Build query key with filters
  const queryKey = ['serve-attempts', filters || {}];

  // Fetch serve attempts using React Query
  const serveAttemptsQuery = useQuery<ServeAttempt[]>({
    queryKey,
    queryFn: async () => {
      return await serveAttemptApi.list(filters);
    },
    enabled: autoRefresh,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Call onServeAttemptsLoaded callback when serve attempts are loaded
  useEffect(() => {
    if (serveAttemptsQuery.data && onServeAttemptsLoaded) {
      onServeAttemptsLoaded(serveAttemptsQuery.data);
    }
  }, [serveAttemptsQuery.data, onServeAttemptsLoaded]);

  // Call onError callback when there's an error
  useEffect(() => {
    if (serveAttemptsQuery.error && onError) {
      const axiosError = serveAttemptsQuery.error as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      const errorMessage =
        axiosError?.response?.data?.detail ||
        axiosError?.message ||
        'Failed to load serve attempts';
      onError(errorMessage);
    }
  }, [serveAttemptsQuery.error, onError]);

  // Create serve attempt mutation
  const createMutation = useMutation({
    mutationFn: (serveAttempt: ServeAttemptCreate) =>
      serveAttemptApi.create(serveAttempt),
    onSuccess: () => {
      // Invalidate and refetch serve attempts
      queryClient.invalidateQueries({ queryKey: ['serve-attempts'] });
    },
  });

  // Update serve attempt mutation
  const updateMutation = useMutation({
    mutationFn: ({
      serveAttemptId,
      updates,
    }: {
      serveAttemptId: number;
      updates: ServeAttemptUpdate;
    }) => serveAttemptApi.update(serveAttemptId, updates),
    onSuccess: () => {
      // Invalidate and refetch serve attempts
      queryClient.invalidateQueries({ queryKey: ['serve-attempts'] });
    },
  });

  // Delete serve attempt mutation
  const deleteMutation = useMutation({
    mutationFn: (serveAttemptId: number) =>
      serveAttemptApi.delete(serveAttemptId),
    onSuccess: () => {
      // Invalidate and refetch serve attempts
      queryClient.invalidateQueries({ queryKey: ['serve-attempts'] });
    },
  });

  const refreshServeAttempts = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ['serve-attempts'] });
  }, [queryClient]);

  const createServeAttempt = useCallback(
    async (serveAttempt: ServeAttemptCreate): Promise<ServeAttempt> => {
      try {
        return await createMutation.mutateAsync(serveAttempt);
      } catch (err: unknown) {
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to create serve attempt';
        throw new Error(errorMessage);
      }
    },
    [createMutation]
  );

  const updateServeAttempt = useCallback(
    async (
      serveAttemptId: number,
      updates: ServeAttemptUpdate
    ): Promise<ServeAttempt> => {
      try {
        return await updateMutation.mutateAsync({ serveAttemptId, updates });
      } catch (err: unknown) {
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to update serve attempt';
        throw new Error(errorMessage);
      }
    },
    [updateMutation]
  );

  const deleteServeAttempt = useCallback(
    async (serveAttemptId: number): Promise<void> => {
      try {
        await deleteMutation.mutateAsync(serveAttemptId);
      } catch (err: unknown) {
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to delete serve attempt';
        throw new Error(errorMessage);
      }
    },
    [deleteMutation]
  );

  // Extract loading state
  const loading = serveAttemptsQuery.isLoading;

  // Extract error state
  const error = serveAttemptsQuery.error
    ? (() => {
        const err = serveAttemptsQuery.error;
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        return (
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to load serve attempts'
        );
      })()
    : null;

  return {
    serveAttempts: serveAttemptsQuery.data || [],
    loading,
    error,
    refreshServeAttempts,
    createServeAttempt,
    updateServeAttempt,
    deleteServeAttempt,
  };
};
