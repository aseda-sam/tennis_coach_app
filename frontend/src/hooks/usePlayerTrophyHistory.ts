import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { biomechanicsApi } from '../services/biomechanicsApi';

export interface PlayerTrophyEntry {
  serveWindowId: number;
  videoFilename: string;
  confidence: number;
  method: string;
}

const STALE_TIME = 5 * 60 * 1000;

/**
 * Fetch player biomechanics history and extract trophy KTP entries.
 */
export function usePlayerTrophyHistory(playerId: number | null): {
  entries: PlayerTrophyEntry[];
  isLoading: boolean;
} {
  const { data: reports, isLoading } = useQuery({
    queryKey: ['player-biomechanics-history', playerId],
    queryFn: () => biomechanicsApi.getPlayerHistory(playerId!, 50),
    enabled: playerId != null,
    staleTime: STALE_TIME,
  });

  const entries = useMemo(() => {
    if (!reports) return [];

    const result: PlayerTrophyEntry[] = [];

    for (const report of reports) {
      const trophyKtp = report.detection_meta?.ktps?.['trophy_position'];
      if (!trophyKtp || trophyKtp.frame == null) continue;

      const trophyMoment = report.moments?.find(
        (m) => m.moment === 'trophy_position'
      );

      result.push({
        serveWindowId: report.serve_window_id,
        videoFilename: report.video_filename ?? 'Unknown',
        confidence: trophyMoment?.confidence ?? 0,
        method: trophyKtp.method ?? 'unknown',
      });
    }

    return result;
  }, [reports]);

  return { entries, isLoading };
}
