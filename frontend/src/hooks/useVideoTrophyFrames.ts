import { useMemo } from 'react';
import { useQueries } from '@tanstack/react-query';
import { biomechanicsApi } from '../services/biomechanicsApi';
import { ServeBiomechanicsReport } from '../types/biomechanics';
import { ServeWindow } from '../types/serveWindow';

export interface TrophyFrameData {
  serveWindowId: number;
  serveIndex: number;
  confidence: number;
  method: string;
}

const STALE_TIME = 5 * 60 * 1000;

/**
 * Fetch biomechanics reports for all serve windows and extract trophy KTP metadata.
 * Frames are fetched per-cell via useServeWindowFrame (not here).
 */
export function useVideoTrophyFrames(
  serveWindows: ServeWindow[],
  enabled: boolean
): { trophyData: TrophyFrameData[]; isLoading: boolean } {
  const reportQueries = useQueries({
    queries: serveWindows.map((sw) => ({
      queryKey: ['biomechanics-report', sw.id],
      queryFn: () => biomechanicsApi.getReport(sw.id),
      enabled: enabled && sw.id > 0,
      staleTime: STALE_TIME,
      retry: 1,
    })),
  });

  const allReportsLoaded =
    enabled &&
    reportQueries.length > 0 &&
    reportQueries.every((q) => !q.isLoading);

  const trophyData = useMemo(() => {
    if (!allReportsLoaded) return [];

    const reports = reportQueries
      .map((q) => q.data as ServeBiomechanicsReport | undefined)
      .filter((r): r is ServeBiomechanicsReport => !!r);

    const result: TrophyFrameData[] = [];

    reports.forEach((report) => {
      const swIndex = serveWindows.findIndex(
        (sw) => sw.id === report.serve_window_id
      );
      if (swIndex === -1) return;

      const trophyKtp = report.detection_meta?.ktps?.['trophy_position'];
      const trophyMoment = report.moments?.find(
        (m) => m.moment === 'trophy_position'
      );

      // Need at least a frame in KTP data for backend extraction
      if (trophyKtp?.frame == null) return;

      result.push({
        serveWindowId: report.serve_window_id,
        serveIndex: swIndex,
        confidence: trophyMoment?.confidence ?? 0,
        method: trophyKtp?.method ?? 'unknown',
      });
    });

    return result;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allReportsLoaded]);

  const isLoading = enabled && reportQueries.some((q) => q.isLoading);

  return { trophyData, isLoading };
}
