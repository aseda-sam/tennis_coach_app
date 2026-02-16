import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { biomechanicsApi } from '../services/biomechanicsApi';
import { ServeBiomechanicsReport } from '../types/biomechanics';

const STALE_TIME = 5 * 60 * 1000; // 5 minutes

export function useServeBiomechanicsReport(serveWindowId: number | null) {
  return useQuery<ServeBiomechanicsReport>({
    queryKey: ['biomechanics-report', serveWindowId],
    queryFn: () => biomechanicsApi.getReport(serveWindowId!),
    enabled: serveWindowId !== null && serveWindowId > 0,
    staleTime: STALE_TIME,
    retry: 1,
  });
}

export function useRecomputeServeBiomechanics() {
  const queryClient = useQueryClient();

  return useMutation<ServeBiomechanicsReport, Error, number>({
    mutationFn: (serveWindowId: number) =>
      biomechanicsApi.computeReport(serveWindowId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: ['biomechanics-report', data.serve_window_id],
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
