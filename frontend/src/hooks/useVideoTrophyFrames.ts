import { useEffect, useState } from 'react';
import { useQueries } from '@tanstack/react-query';
import { biomechanicsApi } from '../services/biomechanicsApi';
import { ServeBiomechanicsReport } from '../types/biomechanics';
import { ServeWindow } from '../types/serveWindow';
import {
  CapturedFrame,
  captureFramesAtTimestamps,
} from '../utils/captureFrames';

export interface TrophyFrame extends CapturedFrame {
  serveIndex: number;
  confidence: number;
  method: string;
}

const STALE_TIME = 5 * 60 * 1000;

export function useVideoTrophyFrames(
  serveWindows: ServeWindow[],
  videoUrl: string,
  enabled: boolean
): { frames: TrophyFrame[]; isLoading: boolean } {
  const [frames, setFrames] = useState<TrophyFrame[]>([]);
  const [capturing, setCapturing] = useState(false);

  // Fetch biomechanics reports for all serve windows in parallel
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

  // Extract trophy timestamps and capture frames once all reports are loaded
  useEffect(() => {
    if (!allReportsLoaded || capturing) return;

    const reports = reportQueries
      .map((q) => q.data as ServeBiomechanicsReport | undefined)
      .filter((r): r is ServeBiomechanicsReport => !!r);

    // Build targets: trophy moment from each report
    const targets: {
      timestamp: number;
      label: string;
      serveIndex: number;
      confidence: number;
      method: string;
    }[] = [];

    reports.forEach((report) => {
      const swIndex = serveWindows.findIndex(
        (sw) => sw.id === report.serve_window_id
      );
      if (swIndex === -1) return;

      // Find trophy KTP from detection_meta (has method info)
      const trophyKtp = report.detection_meta?.ktps?.['trophy'];
      // Also check moments for the timestamp
      const trophyMoment = report.moments?.find(
        (m) => m.moment === 'trophy_position'
      );

      const timestamp = trophyKtp?.timestamp ?? trophyMoment?.timestamp;
      if (timestamp == null) return;

      targets.push({
        timestamp,
        label: `Serve ${swIndex + 1}`,
        serveIndex: swIndex,
        confidence: trophyMoment?.confidence ?? 0,
        method: trophyKtp?.method ?? 'unknown',
      });
    });

    if (targets.length === 0) {
      setFrames([]);
      return;
    }

    let cancelled = false;
    setCapturing(true);

    captureFramesAtTimestamps(
      videoUrl,
      targets.map((t) => ({ timestamp: t.timestamp, label: t.label }))
    )
      .then((captured) => {
        if (cancelled) return;
        const trophyFrames: TrophyFrame[] = captured.map((frame, i) => ({
          ...frame,
          serveIndex: targets[i].serveIndex,
          confidence: targets[i].confidence,
          method: targets[i].method,
        }));
        setFrames(trophyFrames);
      })
      .finally(() => {
        if (!cancelled) setCapturing(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allReportsLoaded, videoUrl]);

  const isLoading =
    enabled && (reportQueries.some((q) => q.isLoading) || capturing);

  return { frames, isLoading };
}
