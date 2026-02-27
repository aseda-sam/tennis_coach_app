import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { serveProposalApi } from '../services/serveProposalApi';
import {
  DetectionStatusResponse,
  ProposeResponse,
} from '../types/serveProposal';
import { getApiErrorMessage } from '../utils/apiError';

interface UseServeProposalsOptions {
  videoId?: number;
  autoRefresh?: boolean;
  isDemo?: boolean;
}

interface UseServeProposalsResult {
  detectionStatus: DetectionStatusResponse | null;
  runDetection: (force?: boolean) => Promise<ProposeResponse>;
  refreshStatus: () => Promise<void>;
}

export const useServeProposals = ({
  videoId,
  autoRefresh = true,
  isDemo = false,
}: UseServeProposalsOptions = {}): UseServeProposalsResult => {
  const queryClient = useQueryClient();

  const statusQueryKey = ['serve-detection-status', videoId];

  // Fetch detection status using React Query
  const statusQuery = useQuery<DetectionStatusResponse>({
    queryKey: statusQueryKey,
    queryFn: async () => {
      if (!videoId) throw new Error('Video ID required');
      return await serveProposalApi.getStatus(videoId);
    },
    enabled: autoRefresh && !!videoId && !isDemo,
    staleTime: 30 * 1000, // 30 seconds
  });

  // Run detection mutation
  const runDetectionMutation = useMutation({
    mutationFn: (force: boolean = false) => {
      if (!videoId) throw new Error('Video ID required');
      return serveProposalApi.propose(videoId, force);
    },
    onSuccess: () => {
      // Invalidate and refetch status
      queryClient.invalidateQueries({ queryKey: ['serve-detection-status'] });
      // Also invalidate serve windows since detection creates them
      queryClient.invalidateQueries({ queryKey: ['serve-windows'] });
    },
  });

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
        const errorMessage = getApiErrorMessage(err, 'Failed to run detection');
        throw new Error(errorMessage);
      }
    },
    [runDetectionMutation]
  );

  return {
    detectionStatus: statusQuery.data || null,
    runDetection,
    refreshStatus,
  };
};
