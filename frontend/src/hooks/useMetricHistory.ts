import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { biomechanicsApi } from '../services/biomechanicsApi';

/**
 * Fetches player biomechanics history and extracts per-metric value arrays.
 * Only enabled when playerId is defined and not in demo mode.
 */
export function useMetricHistory(
  playerId: number | null | undefined,
  isDemo: boolean
) {
  const { data: reports } = useQuery({
    queryKey: ['player-history', playerId],
    queryFn: () => biomechanicsApi.getPlayerHistory(playerId!, 100),
    enabled: !!playerId && !isDemo,
    staleTime: 5 * 60 * 1000,
  });

  const historyMap = useMemo(() => {
    const map: Record<string, number[]> = {};
    if (!reports) return map;
    for (const report of reports) {
      for (const metric of report.metrics) {
        if (metric.value != null) {
          if (!map[metric.metric_name]) {
            map[metric.metric_name] = [];
          }
          map[metric.metric_name].push(metric.value);
        }
      }
    }
    return map;
  }, [reports]);

  return historyMap;
}
