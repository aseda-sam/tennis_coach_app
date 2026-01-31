import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect } from 'react';
import {
  AcceptProposalRequest,
  ClearProposalsResponse,
  DetectionStatusResponse,
  EditProposalRequest,
  ProposeResponse,
  serveProposalApi,
  ServeWindowProposal,
} from '../services/serveProposalApi';

interface UseServeProposalsOptions {
  videoId?: number;
  autoRefresh?: boolean;
  onProposalsLoaded?: (proposals: ServeWindowProposal[]) => void;
  onError?: (error: string) => void;
}

interface UseServeProposalsResult {
  proposals: ServeWindowProposal[];
  loading: boolean;
  error: string | null;
  detectionStatus: DetectionStatusResponse | null;
  refreshProposals: () => Promise<void>;
  refreshStatus: () => Promise<void>;
  runDetection: (force?: boolean) => Promise<ProposeResponse>;
  clearProposals: () => Promise<ClearProposalsResponse>;
  acceptProposal: (
    proposalId: number,
    request?: AcceptProposalRequest
  ) => Promise<void>;
  rejectProposal: (proposalId: number) => Promise<void>;
  editProposal: (
    proposalId: number,
    request: EditProposalRequest
  ) => Promise<void>;
}

export const useServeProposals = ({
  videoId,
  autoRefresh = true,
  onProposalsLoaded,
  onError,
}: UseServeProposalsOptions = {}): UseServeProposalsResult => {
  const queryClient = useQueryClient();

  // Build query keys
  const proposalsQueryKey = ['serve-proposals', videoId];
  const statusQueryKey = ['serve-detection-status', videoId];

  // Fetch proposals using React Query
  const proposalsQuery = useQuery<ServeWindowProposal[]>({
    queryKey: proposalsQueryKey,
    queryFn: async () => {
      if (!videoId) return [];
      return await serveProposalApi.list(videoId);
    },
    enabled: autoRefresh && !!videoId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Fetch detection status using React Query
  const statusQuery = useQuery<DetectionStatusResponse>({
    queryKey: statusQueryKey,
    queryFn: async () => {
      if (!videoId) throw new Error('Video ID required');
      return await serveProposalApi.getStatus(videoId);
    },
    enabled: autoRefresh && !!videoId,
    staleTime: 30 * 1000, // 30 seconds
  });

  // Call onProposalsLoaded callback when proposals are loaded
  useEffect(() => {
    if (proposalsQuery.data && onProposalsLoaded) {
      onProposalsLoaded(proposalsQuery.data);
    }
  }, [proposalsQuery.data, onProposalsLoaded]);

  // Call onError callback when there's an error
  useEffect(() => {
    if (proposalsQuery.error && onError) {
      const axiosError = proposalsQuery.error as {
        response?: { data?: { detail?: string } };
        message?: string;
      };
      const errorMessage =
        axiosError?.response?.data?.detail ||
        axiosError?.message ||
        'Failed to load proposals';
      onError(errorMessage);
    }
  }, [proposalsQuery.error, onError]);

  // Run detection mutation
  const runDetectionMutation = useMutation({
    mutationFn: (force: boolean = false) => {
      if (!videoId) throw new Error('Video ID required');
      return serveProposalApi.propose(videoId, force);
    },
    onSuccess: () => {
      // Invalidate and refetch proposals and status
      queryClient.invalidateQueries({ queryKey: ['serve-proposals'] });
      queryClient.invalidateQueries({ queryKey: ['serve-detection-status'] });
      // Also invalidate serve attempts since accepting creates one
      queryClient.invalidateQueries({ queryKey: ['serve-attempts'] });
    },
  });

  // Clear proposals mutation
  const clearProposalsMutation = useMutation({
    mutationFn: () => {
      if (!videoId) throw new Error('Video ID required');
      return serveProposalApi.clearProposals(videoId);
    },
    onSuccess: () => {
      // Invalidate and refetch proposals and status
      queryClient.invalidateQueries({ queryKey: ['serve-proposals'] });
      queryClient.invalidateQueries({ queryKey: ['serve-detection-status'] });
    },
  });

  // Accept proposal mutation
  const acceptMutation = useMutation({
    mutationFn: ({
      proposalId,
      request,
    }: {
      proposalId: number;
      request?: AcceptProposalRequest;
    }) => serveProposalApi.accept(proposalId, request),
    onSuccess: () => {
      // Invalidate proposals and serve attempts
      queryClient.invalidateQueries({ queryKey: ['serve-proposals'] });
      queryClient.invalidateQueries({ queryKey: ['serve-attempts'] });
      queryClient.invalidateQueries({ queryKey: ['serve-detection-status'] });
    },
  });

  // Reject proposal mutation
  const rejectMutation = useMutation({
    mutationFn: (proposalId: number) => serveProposalApi.reject(proposalId),
    onSuccess: () => {
      // Invalidate proposals
      queryClient.invalidateQueries({ queryKey: ['serve-proposals'] });
      queryClient.invalidateQueries({ queryKey: ['serve-detection-status'] });
    },
  });

  // Edit proposal mutation
  const editMutation = useMutation({
    mutationFn: ({
      proposalId,
      request,
    }: {
      proposalId: number;
      request: EditProposalRequest;
    }) => serveProposalApi.edit(proposalId, request),
    onSuccess: () => {
      // Invalidate proposals and serve attempts
      queryClient.invalidateQueries({ queryKey: ['serve-proposals'] });
      queryClient.invalidateQueries({ queryKey: ['serve-attempts'] });
      queryClient.invalidateQueries({ queryKey: ['serve-detection-status'] });
    },
  });

  const refreshProposals = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ['serve-proposals'] });
  }, [queryClient]);

  const refreshStatus = useCallback(async () => {
    await queryClient.invalidateQueries({
      queryKey: ['serve-detection-status'],
    });
  }, [queryClient]);

  const runDetection = useCallback(
    async (force: boolean = false): Promise<ProposeResponse> => {
      try {
        return await runDetectionMutation.mutateAsync(force);
      } catch (err: unknown) {
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to run detection';
        throw new Error(errorMessage);
      }
    },
    [runDetectionMutation]
  );

  const clearProposals =
    useCallback(async (): Promise<ClearProposalsResponse> => {
      try {
        return await clearProposalsMutation.mutateAsync();
      } catch (err: unknown) {
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to clear proposals';
        throw new Error(errorMessage);
      }
    }, [clearProposalsMutation]);

  const acceptProposal = useCallback(
    async (
      proposalId: number,
      request?: AcceptProposalRequest
    ): Promise<void> => {
      try {
        await acceptMutation.mutateAsync({ proposalId, request });
      } catch (err: unknown) {
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to accept proposal';
        throw new Error(errorMessage);
      }
    },
    [acceptMutation]
  );

  const rejectProposal = useCallback(
    async (proposalId: number): Promise<void> => {
      try {
        await rejectMutation.mutateAsync(proposalId);
      } catch (err: unknown) {
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to reject proposal';
        throw new Error(errorMessage);
      }
    },
    [rejectMutation]
  );

  const editProposal = useCallback(
    async (proposalId: number, request: EditProposalRequest): Promise<void> => {
      try {
        await editMutation.mutateAsync({ proposalId, request });
      } catch (err: unknown) {
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        const errorMessage =
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to edit proposal';
        throw new Error(errorMessage);
      }
    },
    [editMutation]
  );

  // Extract loading state
  const loading = proposalsQuery.isLoading;

  // Extract error state
  const error = proposalsQuery.error
    ? (() => {
        const err = proposalsQuery.error;
        const axiosError = err as {
          response?: { data?: { detail?: string } };
          message?: string;
        };
        return (
          axiosError?.response?.data?.detail ||
          axiosError?.message ||
          'Failed to load proposals'
        );
      })()
    : null;

  return {
    proposals: proposalsQuery.data || [],
    loading,
    error,
    detectionStatus: statusQuery.data || null,
    refreshProposals,
    refreshStatus,
    runDetection,
    clearProposals,
    acceptProposal,
    rejectProposal,
    editProposal,
  };
};
