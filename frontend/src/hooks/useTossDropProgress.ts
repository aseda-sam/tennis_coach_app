import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { biomechanicsApi } from '../services/biomechanicsApi';

export interface TossDropDataPoint {
  serveWindowId: number;
  videoId: number | null;
  videoFilename: string | null;
  /** ISO timestamp of when the video was recorded (preferred for labels) */
  videoRecordedAt: string | null;
  /** ISO timestamp string from the report's created_at (fallback) */
  createdAt: string;
  value: number | null;
}

export interface TossDropSession {
  videoId: number | null;
  videoFilename: string | null;
  /** Date label derived from the earliest report in this session */
  dateLabel: string;
  points: TossDropDataPoint[];
}

/**
 * Fetches player biomechanics history and returns toss_drop data points
 * grouped by recording session (video_id), sorted chronologically.
 *
 * Unlike useMetricHistory, this retains temporal/video context so it
 * can be used for cross-session progress charts.
 */
export function useTossDropProgress(
  playerId: number | null | undefined,
  isDemo: boolean
) {
  const { data: reports, isLoading } = useQuery({
    queryKey: ['player-history', playerId],
    queryFn: () => biomechanicsApi.getPlayerHistory(playerId!, 100),
    enabled: !!playerId && !isDemo,
    staleTime: 5 * 60 * 1000,
  });

  const sessions = useMemo((): TossDropSession[] => {
    if (!reports) return [];

    // Build a flat list of data points, one per report
    const points: TossDropDataPoint[] = reports
      .map((report) => {
        const metric = report.metrics.find(
          (m) => m.metric_name === 'toss_drop'
        );
        return {
          serveWindowId: report.serve_window_id,
          videoId: report.video_id ?? null,
          videoFilename: report.video_filename ?? null,
          videoRecordedAt: report.video_recorded_at ?? null,
          createdAt: report.created_at,
          value: metric?.value ?? null,
        };
      })
      // Sort chronologically by recording date (prefer videoRecordedAt, fall back to createdAt)
      .sort((a, b) => {
        const aDate = a.videoRecordedAt ?? a.createdAt;
        const bDate = b.videoRecordedAt ?? b.createdAt;
        return new Date(aDate).getTime() - new Date(bDate).getTime();
      });

    // Group by video_id (null video_ids each get their own group)
    const sessionMap = new Map<string, TossDropDataPoint[]>();
    for (const pt of points) {
      const key =
        pt.videoId != null ? String(pt.videoId) : `sw-${pt.serveWindowId}`;
      if (!sessionMap.has(key)) sessionMap.set(key, []);
      sessionMap.get(key)!.push(pt);
    }

    return Array.from(sessionMap.entries()).map(([, pts]) => {
      const earliest = pts[0];
      // Prefer recording date over analysis run date for labels
      const labelSource = earliest.videoRecordedAt ?? earliest.createdAt;
      const date = new Date(labelSource);
      const dateLabel = date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      });
      return {
        videoId: earliest.videoId,
        videoFilename: earliest.videoFilename,
        dateLabel,
        points: pts,
      };
    });
  }, [reports]);

  const allValues = useMemo(
    () =>
      sessions
        .flatMap((s) => s.points.map((p) => p.value))
        .filter((v): v is number => v != null),
    [sessions]
  );

  const mean = useMemo(
    () =>
      allValues.length > 0
        ? allValues.reduce((a, b) => a + b, 0) / allValues.length
        : null,
    [allValues]
  );

  return { sessions, mean, totalCount: allValues.length, isLoading };
}
