import { useQuery } from '@tanstack/react-query';
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
