import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { biomechanicsApi } from '../services/biomechanicsApi';
import { ServeBiomechanicsReport } from '../types/biomechanics';

const STALE_TIME = 5 * 60 * 1000; // 5 minutes

export function useServeBiomechanicsReport(serveAttemptId: number | null) {
  return useQuery<ServeBiomechanicsReport>({
    queryKey: ['biomechanics-report', serveAttemptId],
    queryFn: () => biomechanicsApi.getReport(serveAttemptId!),
    enabled: serveAttemptId !== null && serveAttemptId > 0,
    staleTime: STALE_TIME,
    retry: 1,
  });
}

export function useRecomputeServeBiomechanics() {
  const queryClient = useQueryClient();

  return useMutation<ServeBiomechanicsReport, Error, number>({
    mutationFn: (serveAttemptId: number) =>
      biomechanicsApi.computeReport(serveAttemptId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: ['biomechanics-report', data.serve_attempt_id],
      });
    },
  });
}

export function usePlayerBiomechanicsHistory(
  playerId: number | null,
  limit: number = 20
) {
  return useQuery<ServeBiomechanicsReport[]>({
    queryKey: ['biomechanics-history', playerId, limit],
    queryFn: () => biomechanicsApi.getPlayerHistory(playerId!, limit),
    enabled: playerId !== null && playerId > 0,
    staleTime: STALE_TIME,
  });
}
